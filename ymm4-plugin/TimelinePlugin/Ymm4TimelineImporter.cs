using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Threading.Tasks;
using NLMSlidePlugin.Core;
using YukkuriMovieMaker.Project;
using YukkuriMovieMaker.Project.Items;

namespace NLMSlidePlugin.TimelinePlugin
{
    /// <summary>
    /// YMM4タイムライン連携ユーティリティ
    /// CSVから読み込んだデータをYMM4タイムラインに追加
    /// </summary>
    public class Ymm4TimelineImporter
    {
        private readonly CsvImportSettings _settings;

        public Ymm4TimelineImporter(CsvImportSettings? settings = null)
        {
            _settings = settings ?? new CsvImportSettings();
        }

        /// <summary>
        /// CSVファイルからタイムラインに一括インポート
        /// </summary>
        /// <param name="csvPath">CSVファイルパス</param>
        /// <param name="audioDir">音声ファイルディレクトリ（省略時はCSVと同ディレクトリ）</param>
        /// <param name="timeline">YMM4タイムライン（省略時はシミュレーションモード）</param>
        /// <param name="addSubtitles">字幕アイテムを追加するか</param>
        public ImportResult ImportFromCsv(string csvPath, string? audioDir = null, Timeline? timeline = null, bool addSubtitles = true)
        {
            var result = new ImportResult();

            try
            {
                var reader = new CsvTimelineReader(csvPath, audioDir);
                var items = reader.ReadTimeline();

                if (items.Count == 0)
                {
                    result.Message = "CSVに有効なデータが見つかりませんでした";
                    return result;
                }

                int audioFound = 0;
                foreach (var item in items)
                {
                    if (!string.IsNullOrEmpty(item.AudioFilePath) && File.Exists(item.AudioFilePath))
                    {
                        audioFound++;
                    }
                }

                // SP-052: overlay_plan.json の読み込み
                var overlayPlan = OverlayImporter.LoadPlanFromCsvDir(csvPath);

                result.TotalItems = items.Count;
                result.AudioFilesFound = audioFound;
                result.Items = items;

                if (timeline != null)
                {
                    var execResult = AddToTimeline(items, timeline, addSubtitles, overlayPlan: overlayPlan);
                    result.Success = true;
                    var overlayMsg = execResult.OverlayItems > 0 ? $", オーバーレイ: {execResult.OverlayItems}件" : "";
                    result.Message = $"{execResult.ImportedRows}件をタイムラインに追加しました（音声: {execResult.AudioItems}件, 字幕: {execResult.TextItems}件, 画像: {execResult.ImageItems}件{overlayMsg}）";
                }
                else
                {
                    result.Success = true;
                    var overlayMsg = overlayPlan != null ? $", オーバーレイ: {overlayPlan.Overlays.Count}件" : "";
                    result.Message = $"{items.Count}件のデータを読み込みました（音声: {audioFound}件{overlayMsg}）";
                }

                _settings.LastCsvPath = csvPath;
                _settings.AudioDirectory = audioDir ?? Path.GetDirectoryName(csvPath);
            }
            catch (Exception ex)
            {
                result.Success = false;
                result.Message = $"インポートエラー: {ex.Message}";
            }

            return result;
        }

        /// <summary>
        /// タイムラインアイテムをYMM4に追加
        /// useVoiceItem=true の場合、AudioItem+TextItem の代わりに VoiceItem を使用する。
        /// VoiceItem は YMM4 がレンダー時に音声合成を行うネイティブ方式。
        /// </summary>
        public AddToTimelineResult AddToTimeline(List<CsvTimelineItem> items, Timeline timeline, bool addSubtitles = true, bool useVoiceItem = false, OverlayImporter.OverlayPlan? overlayPlan = null)
        {
            int fps = Math.Max(1, timeline.VideoInfo.FPS);
            int baseLayer = GetImportBaseLayer(timeline);

            // SP-030: Reset speaker color assignments for this import session
            CsvImportDialog.ResetSpeakerColors();

            int importedRows = 0;
            int audioItemsCount = 0;
            int textItemsCount = 0;
            int imageItemsCount = 0;
            int voiceItemsCount = 0;
            int overlayItemsCount = 0;
            int skippedRows = 0;

            var allTimelineItems = new List<IItem>();

            // SP-052: セグメントごとの開始フレームを記録 (overlay配置用)
            var segmentStartFrames = new Dictionary<int, int>();

            int segmentIndex = 0;
            foreach (var csvItem in items)
            {
                int startFrame = Math.Max(0, (int)Math.Round(csvItem.StartTime * fps));
                int lengthFrames = Math.Max(1, (int)Math.Round((csvItem.Duration ?? 3.0) * fps));

                // SP-052: 開始フレームを記録
                segmentStartFrames[segmentIndex] = startFrame;
                segmentIndex++;

                // SP-028: Use actual WAV duration when available
                if (!string.IsNullOrWhiteSpace(csvItem.AudioFilePath) && File.Exists(csvItem.AudioFilePath))
                {
                    double? wavDuration = CsvImportDialog.GetWavDurationSeconds(csvItem.AudioFilePath);
                    if (wavDuration.HasValue && wavDuration.Value > 0)
                    {
                        lengthFrames = Math.Max(1, (int)Math.Round(wavDuration.Value * fps));
                    }
                }

                bool hasItemInRow = false;

                if (useVoiceItem)
                {
                    // VoiceItem モード: テキストがある行に VoiceItem を作成
                    // YMM4 がレンダー時に音声合成+字幕表示を担当
                    if (!string.IsNullOrWhiteSpace(csvItem.Text))
                    {
                        var voiceItem = new VoiceItem
                        {
                            Serif = csvItem.Text,
                            CharacterName = csvItem.Speaker ?? string.Empty,
                            Frame = startFrame,
                            Layer = baseLayer,
                            Length = lengthFrames
                        };
                        allTimelineItems.Add(voiceItem);
                        voiceItemsCount++;
                        hasItemInRow = true;
                    }

                    // ImageItem: VoiceItemモードではbaseLayer+1
                    // SP-033: Values in-place方式でZoomアニメーション適用
                    if (!string.IsNullOrWhiteSpace(csvItem.ImageFilePath) && File.Exists(csvItem.ImageFilePath))
                    {
                        var image = new ImageItem(csvItem.ImageFilePath)
                        {
                            Frame = startFrame,
                            Layer = baseLayer + 1,
                            Length = lengthFrames,
                            PlaybackRate = 100.0
                        };
                        double fitZoom = CsvImportDialog.CalculateFitZoom(csvItem.ImageFilePath, timeline.VideoInfo.Width, timeline.VideoInfo.Height);
                        CsvImportDialog.ApplyAnimationDirect(image, csvItem.AnimationType ?? "ken_burns", fitZoom, timeline.VideoInfo.Width, timeline.VideoInfo.Height);
                        allTimelineItems.Add(image);
                        imageItemsCount++;
                        hasItemInRow = true;
                    }
                }
                else
                {
                    // AudioItem + TextItem モード (従来方式)
                    if (!string.IsNullOrWhiteSpace(csvItem.AudioFilePath) && File.Exists(csvItem.AudioFilePath))
                    {
                        var audio = new AudioItem(csvItem.AudioFilePath)
                        {
                            Frame = startFrame,
                            Layer = baseLayer,
                            Length = lengthFrames,
                            PlaybackRate = 1.0
                        };
                        allTimelineItems.Add(audio);
                        audioItemsCount++;
                        hasItemInRow = true;
                    }

                    // SP-033: Values in-place方式でZoomアニメーション適用
                    if (!string.IsNullOrWhiteSpace(csvItem.ImageFilePath) && File.Exists(csvItem.ImageFilePath))
                    {
                        var image = new ImageItem(csvItem.ImageFilePath)
                        {
                            Frame = startFrame,
                            Layer = baseLayer + 1,
                            Length = lengthFrames,
                            PlaybackRate = 100.0
                        };
                        double fitZoom = CsvImportDialog.CalculateFitZoom(csvItem.ImageFilePath, timeline.VideoInfo.Width, timeline.VideoInfo.Height);
                        CsvImportDialog.ApplyAnimationDirect(image, csvItem.AnimationType ?? "ken_burns", fitZoom, timeline.VideoInfo.Width, timeline.VideoInfo.Height);
                        allTimelineItems.Add(image);
                        imageItemsCount++;
                        hasItemInRow = true;
                    }

                    if (addSubtitles && !string.IsNullOrWhiteSpace(csvItem.Text))
                    {
                        var text = new TextItem
                        {
                            Frame = startFrame,
                            Layer = baseLayer + 10,
                            Length = lengthFrames,
                            PlaybackRate = 100.0,
                            Text = csvItem.Text
                        };
                        CsvImportDialog.ApplySubtitleStyle(text, timeline.VideoInfo.Width, timeline.VideoInfo.Height, csvItem.Speaker);
                        allTimelineItems.Add(text);
                        textItemsCount++;
                        hasItemInRow = true;
                    }
                }

                if (hasItemInRow)
                    importedRows++;
                else
                    skippedRows++;
            }

            // SP-052: オーバーレイ TextItem の配置
            if (overlayPlan != null && overlayPlan.Overlays.Count > 0)
            {
                // style_template から overlay 設定を取得
                var styleTemplate = StyleTemplateLoader.Load(csvFilePath: null, log: null);
                var overlayTextItems = OverlayImporter.ConvertToTextItems(
                    overlayPlan, segmentStartFrames, fps,
                    timeline.VideoInfo.Width, timeline.VideoInfo.Height,
                    styleTemplate?.Overlay, baseLayer + 17);

                foreach (var overlayParam in overlayTextItems)
                {
                    var textItem = new TextItem
                    {
                        Frame = overlayParam.Frame,
                        Layer = overlayParam.Layer,
                        Length = overlayParam.Length,
                        PlaybackRate = 100.0,
                        Text = overlayParam.Text
                    };
                    // フォントサイズ・色・太字等はYMM4 API経由で設定
                    // (TextItem のプロパティ互換性は YMM4 バージョンに依存)
                    allTimelineItems.Add(textItem);
                    overlayItemsCount++;
                }
            }

            if (allTimelineItems.Count > 0)
            {
                // ImmutableList対応: Items.Add()は新リストを返す。
                // Setterがある場合はPropertyInfo.SetValueで更新する。
                var itemsProp = timeline.GetType().GetProperty("Items");
                bool hasSetter = itemsProp?.SetMethod != null;

                foreach (var item in allTimelineItems)
                {
                    if (hasSetter)
                        itemsProp!.SetValue(timeline, timeline.Items.Add(item));
                    else
                        timeline.Items.Add(item);
                }
                timeline.RefreshTimelineLengthAndMaxLayer();
            }

            return new AddToTimelineResult(importedRows, audioItemsCount, textItemsCount, imageItemsCount, voiceItemsCount, overlayItemsCount, skippedRows, timeline.Items.Count);
        }

        /// <summary>
        /// 非同期版 AddToTimeline（UIスレッドからの呼び出し用）
        /// </summary>
        public Task<AddToTimelineResult> AddToTimelineAsync(List<CsvTimelineItem> items, Timeline timeline, bool addSubtitles = true, bool useVoiceItem = false, OverlayImporter.OverlayPlan? overlayPlan = null)
        {
            return Task.FromResult(AddToTimeline(items, timeline, addSubtitles, useVoiceItem, overlayPlan));
        }

        private static int GetImportBaseLayer(Timeline timeline)
        {
            int maxLayer = 0;
            foreach (var item in timeline.Items)
            {
                if (item.Layer > maxLayer)
                    maxLayer = item.Layer;
            }
            return maxLayer + 1;
        }
    }

    /// <summary>
    /// タイムライン追加結果
    /// </summary>
    public record AddToTimelineResult(
        int ImportedRows,
        int AudioItems,
        int TextItems,
        int ImageItems,
        int VoiceItems,
        int OverlayItems,
        int SkippedRows,
        int TotalTimelineItems);

    /// <summary>
    /// インポート結果
    /// </summary>
    public class ImportResult
    {
        public bool Success { get; set; }
        public string Message { get; set; } = string.Empty;
        public int TotalItems { get; set; }
        public int AudioFilesFound { get; set; }
        public List<CsvTimelineItem>? Items { get; set; }
    }
}

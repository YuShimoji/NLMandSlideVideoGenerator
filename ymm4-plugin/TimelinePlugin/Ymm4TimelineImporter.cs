using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using NLMSlidePlugin.Core;
using NLMSlidePlugin.VoicePlugin;
using YukkuriMovieMaker.Plugin.Voice;
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
        private readonly CsvVoiceResolver _voiceResolver;

        public Ymm4TimelineImporter(CsvImportSettings? settings = null, VoiceSpeakerMapping? voiceMapping = null)
        {
            _settings = settings ?? new CsvImportSettings();
            _voiceResolver = new CsvVoiceResolver(voiceMapping);
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

                result.TotalItems = items.Count;
                result.AudioFilesFound = audioFound;
                result.Items = items;

                if (timeline != null)
                {
                    var execResult = AddToTimeline(items, timeline, addSubtitles);
                    result.Success = true;
                    result.Message = $"{execResult.ImportedRows}件をタイムラインに追加しました（音声: {execResult.AudioItems}件, 字幕: {execResult.TextItems}件）";
                }
                else
                {
                    result.Success = true;
                    result.Message = $"{items.Count}件のデータを読み込みました（音声: {audioFound}件）";
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
        /// タイムラインアイテムをYMM4に追加（同期版: 既存WAVのみ）
        /// </summary>
        public AddToTimelineResult AddToTimeline(List<CsvTimelineItem> items, Timeline timeline, bool addSubtitles = true)
        {
            int fps = Math.Max(1, timeline.VideoInfo.FPS);
            int baseLayer = GetImportBaseLayer(timeline);

            int importedRows = 0;
            int audioItemsCount = 0;
            int textItemsCount = 0;
            int skippedRows = 0;

            var allTimelineItems = new List<IItem>();

            foreach (var csvItem in items)
            {
                int startFrame = Math.Max(0, (int)Math.Round(csvItem.StartTime * fps));
                int lengthFrames = Math.Max(1, (int)Math.Round((csvItem.Duration ?? 3.0) * fps));

                bool hasItemInRow = false;

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

                if (addSubtitles && !string.IsNullOrWhiteSpace(csvItem.Text))
                {
                    var text = new TextItem
                    {
                        Frame = startFrame,
                        Layer = baseLayer + 1,
                        Length = lengthFrames,
                        PlaybackRate = 1.0,
                        Text = csvItem.Text
                    };
                    allTimelineItems.Add(text);
                    textItemsCount++;
                    hasItemInRow = true;
                }

                if (hasItemInRow)
                    importedRows++;
                else
                    skippedRows++;
            }

            if (allTimelineItems.Count > 0)
            {
                foreach (var item in allTimelineItems)
                {
                    timeline.Items.Add(item);
                }
                timeline.RefreshTimelineLengthAndMaxLayer();
            }

            return new AddToTimelineResult(importedRows, audioItemsCount, textItemsCount, skippedRows, timeline.Items.Count);
        }

        /// <summary>
        /// 非同期版: ボイス生成 + タイムライン追加
        /// WAVが無いCSV行に対してYMM4のIVoiceSpeakerで音声を自動生成する。
        /// </summary>
        public async Task<AddToTimelineResult> AddToTimelineWithVoiceAsync(
            List<CsvTimelineItem> items,
            Timeline timeline,
            IEnumerable<IVoiceSpeaker> availableSpeakers,
            string voiceOutputDir,
            bool addSubtitles = true,
            IProgress<VoiceGenerationProgress>? progress = null,
            CancellationToken cancellationToken = default)
        {
            // Phase 1: WAVが無い行にボイスを生成
            await _voiceResolver.GenerateVoicesForTimelineAsync(
                items, availableSpeakers, voiceOutputDir, progress, cancellationToken);

            // Phase 2: タイムラインに追加（全アイテムにWAVが揃った状態）
            return AddToTimeline(items, timeline, addSubtitles);
        }

        /// <summary>
        /// 非同期版 AddToTimeline（UIスレッドからの呼び出し用、後方互換）
        /// </summary>
        public Task<AddToTimelineResult> AddToTimelineAsync(List<CsvTimelineItem> items, Timeline timeline, bool addSubtitles = true)
        {
            return Task.FromResult(AddToTimeline(items, timeline, addSubtitles));
        }

        /// <summary>
        /// 話者名に基づいてボイスキャラクターを解決（後方互換）
        /// 新規コードではVoiceSpeakerMappingを直接使用すること。
        /// </summary>
        public string? ResolveVoiceCharacter(string speakerName)
        {
            var mapping = VoiceSpeakerMapping.CreateDefault();
            var resolved = mapping.Resolve(speakerName);
            return resolved.Id;
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

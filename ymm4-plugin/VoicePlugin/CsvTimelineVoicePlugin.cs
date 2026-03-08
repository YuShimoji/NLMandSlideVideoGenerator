using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using NLMSlidePlugin.Core;
using YukkuriMovieMaker.Plugin.Voice;

namespace NLMSlidePlugin.VoicePlugin
{
    /// <summary>
    /// CSVタイムラインのボイス解決・生成（消費者側パターン）
    ///
    /// YMM4の既存IVoicePluginが提供するIVoiceSpeakerを消費し、
    /// CSVのSpeaker列に対応するボイスで音声を生成する。
    /// 自身はIVoicePluginを実装しない。
    /// </summary>
    public class CsvVoiceResolver
    {
        private readonly VoiceSpeakerMapping _mapping;

        public CsvVoiceResolver(VoiceSpeakerMapping? mapping = null)
        {
            _mapping = mapping ?? VoiceSpeakerMapping.CreateDefault();
        }

        /// <summary>
        /// YMM4に登録済みのIVoiceSpeakerからCSV speaker名に一致するものを検索する。
        /// </summary>
        /// <param name="speakerName">CSVのSpeaker列の値</param>
        /// <param name="availableSpeakers">YMM4の全IVoicePlugin.Voicesから集めたスピーカー一覧</param>
        /// <returns>一致するIVoiceSpeaker、見つからない場合はnull</returns>
        public IVoiceSpeaker? FindSpeaker(string speakerName, IEnumerable<IVoiceSpeaker> availableSpeakers)
        {
            var speakerId = _mapping.Resolve(speakerName);

            // まずAPI/IDで完全一致を試みる
            var match = availableSpeakers.FirstOrDefault(s => s.IsMatch(speakerId.Api, speakerId.Id));
            if (match != null)
                return match;

            // フォールバック: SpeakerNameで部分一致
            match = availableSpeakers.FirstOrDefault(s =>
                s.SpeakerName.Equals(speakerName, StringComparison.OrdinalIgnoreCase));
            if (match != null)
                return match;

            // 最終フォールバック: デフォルトスピーカーのAPI/IDで検索
            var defaultId = VoiceSpeakerMapping.DefaultSpeaker;
            return availableSpeakers.FirstOrDefault(s => s.IsMatch(defaultId.Api, defaultId.Id));
        }

        /// <summary>
        /// CSVアイテムに対して音声を生成する。
        /// 既にAudioFilePathが設定されている場合はスキップ。
        /// </summary>
        /// <param name="item">CSVタイムラインアイテム</param>
        /// <param name="speaker">解決済みのIVoiceSpeaker</param>
        /// <param name="outputDir">WAV出力ディレクトリ</param>
        /// <param name="cancellationToken">キャンセルトークン</param>
        /// <returns>生成されたWAVファイルパス、スキップ時はnull</returns>
        public async Task<string?> GenerateVoiceForItemAsync(
            CsvTimelineItem item,
            IVoiceSpeaker speaker,
            string outputDir,
            CancellationToken cancellationToken = default)
        {
            // 既にWAVがある場合はスキップ
            if (!string.IsNullOrEmpty(item.AudioFilePath) && File.Exists(item.AudioFilePath))
                return null;

            if (string.IsNullOrWhiteSpace(item.Text))
                return null;

            Directory.CreateDirectory(outputDir);

            var filePath = Path.Combine(outputDir, $"voice_{item.LineNumber:D3}.wav");

            // IVoiceSpeaker.CreateVoiceAsync でWAVを生成
            var parameter = speaker.CreateVoiceParameter();
            await speaker.CreateVoiceAsync(item.Text, null!, parameter, filePath);

            if (File.Exists(filePath))
            {
                item.AudioFilePath = filePath;
                item.Duration = WavDurationReader.GetDuration(filePath);
                return filePath;
            }

            return null;
        }

        /// <summary>
        /// CSVタイムライン全体に対してバッチで音声を生成する。
        /// </summary>
        public async Task<VoiceGenerationResult> GenerateVoicesForTimelineAsync(
            List<CsvTimelineItem> items,
            IEnumerable<IVoiceSpeaker> availableSpeakers,
            string outputDir,
            IProgress<VoiceGenerationProgress>? progress = null,
            CancellationToken cancellationToken = default)
        {
            var result = new VoiceGenerationResult();
            var speakersList = availableSpeakers.ToList();

            for (int i = 0; i < items.Count; i++)
            {
                cancellationToken.ThrowIfCancellationRequested();

                var item = items[i];

                // 既にWAVがある場合はスキップ
                if (!string.IsNullOrEmpty(item.AudioFilePath) && File.Exists(item.AudioFilePath))
                {
                    result.SkippedCount++;
                    continue;
                }

                var speaker = FindSpeaker(item.Speaker, speakersList);
                if (speaker == null)
                {
                    result.FailedCount++;
                    result.Errors.Add($"Line {item.LineNumber}: スピーカー '{item.Speaker}' に対応するボイスが見つかりません");
                    continue;
                }

                try
                {
                    var path = await GenerateVoiceForItemAsync(item, speaker, outputDir, cancellationToken);
                    if (path != null)
                        result.GeneratedCount++;
                    else
                        result.SkippedCount++;
                }
                catch (Exception ex)
                {
                    result.FailedCount++;
                    result.Errors.Add($"Line {item.LineNumber}: {ex.Message}");
                }

                progress?.Report(new VoiceGenerationProgress
                {
                    Current = i + 1,
                    Total = items.Count,
                    GeneratedCount = result.GeneratedCount,
                    SkippedCount = result.SkippedCount,
                    FailedCount = result.FailedCount
                });
            }

            return result;
        }
    }

    /// <summary>
    /// ボイス生成結果
    /// </summary>
    public class VoiceGenerationResult
    {
        public int GeneratedCount { get; set; }
        public int SkippedCount { get; set; }
        public int FailedCount { get; set; }
        public List<string> Errors { get; } = new();
        public int TotalProcessed => GeneratedCount + SkippedCount + FailedCount;
    }

    /// <summary>
    /// ボイス生成進捗
    /// </summary>
    public class VoiceGenerationProgress
    {
        public int Current { get; init; }
        public int Total { get; init; }
        public int GeneratedCount { get; init; }
        public int SkippedCount { get; init; }
        public int FailedCount { get; init; }
        public double PercentComplete => Total > 0 ? (Current * 100.0 / Total) : 0;
    }
}

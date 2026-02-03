using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using NLMSlidePlugin.Core;

namespace NLMSlidePlugin.TimelinePlugin
{
    /// <summary>
    /// YMM4タイムライン連携ユーティリティ
    /// CSVから読み込んだデータをYMM4タイムラインに追加
    /// </summary>
    public class Ymm4TimelineImporter
    {
        private readonly CsvImportSettings _settings;

        public Ymm4TimelineImporter(CsvImportSettings settings)
        {
            _settings = settings ?? new CsvImportSettings();
        }

        /// <summary>
        /// CSVファイルからタイムラインに一括インポート
        /// </summary>
        public async Task<ImportResult> ImportFromCsvAsync(string csvPath, string? audioDir = null)
        {
            var result = new ImportResult();

            try
            {
                // CSV読み込み
                var reader = new CsvTimelineReader(csvPath, audioDir);
                var items = reader.ReadTimeline();

                if (items.Count == 0)
                {
                    result.Message = "CSVに有効なデータが見つかりませんでした";
                    return result;
                }

                // 音声ファイルの存在確認
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

                // TODO: YMM4 APIを使用してタイムラインにアイテムを追加
                // 現在はシミュレーションモード
                result.Success = true;
                result.Message = $"{items.Count}件のデータを読み込みました（音声: {audioFound}件）";
                result.Items = items;

                // 設定を保存
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
        /// タイムラインアイテムをYMM4に追加（実際のAPI連携部分）
        /// Note: YMM4の内部APIに依存するため、実際の実装はYMM4のバージョンに依存
        /// </summary>
        public async Task<bool> AddToTimelineAsync(List<CsvTimelineItem> items)
        {
            // TODO: YMM4のタイムラインAPIを使用して実装
            // IEditor、ITimeline、ISequence等のインターフェースが必要
            // 現在はプレースホルダー
            
            await Task.Delay(100); // 非同期処理のシミュレーション
            return true;
        }

        /// <summary>
        /// 話者名に基づいてボイスキャラクターを解決
        /// </summary>
        public string? ResolveVoiceCharacter(string speakerName)
        {
            // 話者名 → YMM4ボイスのマッピング
            // デフォルトマッピング
            var mapping = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase)
            {
                { "ずんだもん", "Zundamon" },
                { "四国めたん", "ShikokuMetan" },
                { "ナレーター", "Yukari" },
                { "Speaker1", "Yukari" },
                { "Speaker2", "Zundamon" },
                { "まりさ", "Marisa" },
                { "れいむ", "Reimu" }
            };

            if (mapping.TryGetValue(speakerName, out var voice))
            {
                return voice;
            }

            // デフォルト
            return "Yukari";
        }
    }

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

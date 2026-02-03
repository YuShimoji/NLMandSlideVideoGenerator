using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;

namespace NLMSlidePlugin.Core
{
    /// <summary>
    /// CSVタイムラインの行データを表すモデル
    /// </summary>
    public class CsvTimelineItem
    {
        /// <summary>
        /// 行番号（1-based、WAVファイル紐付け用）</summary>
        public int LineNumber { get; set; }
        
        /// <summary>
        /// 話者名
        /// </summary>
        public string Speaker { get; set; } = string.Empty;
        
        /// <summary>
        /// テロップテキスト
        /// </summary>
        public string Text { get; set; } = string.Empty;
        
        /// <summary>
        /// 対応する音声ファイル名（001.wav形式）
        /// </summary>
        public string? AudioFileName => $"{LineNumber:D3}.wav";
        
        /// <summary>
        /// 音声ファイルのフルパス
        /// </summary>
        public string? AudioFilePath { get; set; }
        
        /// <summary>
        /// 音声の長さ（秒）
        /// </summary>
        public double? Duration { get; set; }
        
        /// <summary>
        /// タイムライン上の開始時刻（秒）
        /// </summary>
        public double StartTime { get; set; }
        
        /// <summary>
        /// タイムライン上の終了時刻（秒）
        /// </summary>
        public double EndTime => StartTime + (Duration ?? 0);

        public override string ToString()
        {
            return $"[{LineNumber:D3}] {Speaker}: {Text?.Substring(0, Math.Min(30, Text?.Length ?? 0))}...";
        }
    }

    /// <summary>
    /// CSVタイムラインリーダー
    /// UTF-8エンコーディング、カンマ区切り、ヘッダーなし
    /// </summary>
    public class CsvTimelineReader
    {
        private readonly string _csvFilePath;
        private readonly string? _audioDirectoryPath;

        public CsvTimelineReader(string csvFilePath, string? audioDirectoryPath = null)
        {
            _csvFilePath = csvFilePath ?? throw new ArgumentNullException(nameof(csvFilePath));
            _audioDirectoryPath = audioDirectoryPath ?? Path.GetDirectoryName(csvFilePath);
        }

        /// <summary>
        /// CSVファイルを読み込み、タイムラインアイテムのリストを返す
        /// </summary>
        public List<CsvTimelineItem> ReadTimeline()
        {
            var items = new List<CsvTimelineItem>();
            
            if (!File.Exists(_csvFilePath))
            {
                throw new FileNotFoundException($"CSVファイルが見つかりません: {_csvFilePath}");
            }

            var lines = File.ReadAllLines(_csvFilePath, Encoding.UTF8);
            int lineNumber = 1;

            foreach (var line in lines)
            {
                // 空行をスキップ
                if (string.IsNullOrWhiteSpace(line))
                    continue;

                var item = ParseLine(line, lineNumber);
                if (item != null)
                {
                    // 音声ファイルの存在確認
                    if (!string.IsNullOrEmpty(_audioDirectoryPath))
                    {
                        var audioPath = Path.Combine(_audioDirectoryPath, item.AudioFileName!);
                        if (File.Exists(audioPath))
                        {
                            item.AudioFilePath = audioPath;
                            // TODO: 音声ファイルの長さを取得（NAudio等が必要）
                            item.Duration = 3.0; // 仮の値
                        }
                    }
                    
                    items.Add(item);
                }
                
                lineNumber++;
            }

            // タイムライン時刻を計算
            CalculateTimeline(items);
            
            return items;
        }

        /// <summary>
        /// 1行をパースしてCsvTimelineItemを作成
        /// </summary>
        private CsvTimelineItem? ParseLine(string line, int lineNumber)
        {
            // CSVパース（簡易実装：カンマ区切り、ダブルクォート対応）
            var parts = ParseCsvLine(line);
            
            if (parts.Count < 2)
            {
                // 列数が足りない場合はスキップ
                return null;
            }

            return new CsvTimelineItem
            {
                LineNumber = lineNumber,
                Speaker = parts[0].Trim(),
                Text = parts[1].Trim()
            };
        }

        /// <summary>
        /// CSV行をパース（ダブルクォート対応）
        /// </summary>
        private List<string> ParseCsvLine(string line)
        {
            var result = new List<string>();
            var current = new StringBuilder();
            bool inQuotes = false;

            for (int i = 0; i < line.Length; i++)
            {
                char c = line[i];

                if (c == '"')
                {
                    if (inQuotes && i + 1 < line.Length && line[i + 1] == '"')
                    {
                        // エスケープされたダブルクォート
                        current.Append('"');
                        i++;
                    }
                    else
                    {
                        inQuotes = !inQuotes;
                    }
                }
                else if (c == ',' && !inQuotes)
                {
                    result.Add(current.ToString());
                    current.Clear();
                }
                else
                {
                    current.Append(c);
                }
            }

            result.Add(current.ToString());
            return result;
        }

        /// <summary>
        /// タイムライン上の開始・終了時刻を計算
        /// </summary>
        private void CalculateTimeline(List<CsvTimelineItem> items)
        {
            double currentTime = 0;
            
            foreach (var item in items)
            {
                item.StartTime = currentTime;
                
                // 次のアイテムの開始時刻を更新
                if (item.Duration.HasValue)
                {
                    currentTime += item.Duration.Value;
                }
                else
                {
                    // 音声ファイルがない場合はデフォルト3秒
                    currentTime += 3.0;
                }
            }
        }
    }
}

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
        public int LineNumber { get; set; }
        public string Speaker { get; set; } = string.Empty;
        public string Text { get; set; } = string.Empty;
        public string? AudioFileName => $"{LineNumber:D3}.wav";
        public string? AudioFilePath { get; set; }
        public string? ImageFilePath { get; set; }
        public double? Duration { get; set; }
        public double StartTime { get; set; }
        public double EndTime => StartTime + (Duration ?? 0);

        public override string ToString()
        {
            return $"[{LineNumber:D3}] {Speaker}: {Text?.Substring(0, Math.Min(30, Text?.Length ?? 0))}...";
        }
    }

    /// <summary>
    /// CSVタイムラインリーダー
    /// UTF-8エンコーディング（BOM自動検出）、カンマ区切り、ヘッダーなし
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
        /// CSVファイルを読み込み、タイムラインアイテムのリストを返す（後方互換）
        /// </summary>
        public List<CsvTimelineItem> ReadTimeline()
        {
            return ReadTimelineWithErrors().Items;
        }

        /// <summary>
        /// CSVファイルを読み込み、エラー情報付きの結果を返す
        /// </summary>
        public CsvReadResult ReadTimelineWithErrors(
            IProgress<CsvReadProgress>? progress = null,
            CancellationToken cancellationToken = default)
        {
            if (!File.Exists(_csvFilePath))
            {
                throw new FileNotFoundException($"CSVファイルが見つかりません: {_csvFilePath}");
            }

            var encoding = DetectEncoding(_csvFilePath);
            var items = new List<CsvTimelineItem>();
            var errors = new List<CsvReadError>();
            int lineNumber = 0;
            int totalLines = CountLines(_csvFilePath, encoding);

            // 音声ファイルを一括スキャン
            var audioFiles = ScanAudioDirectory(_audioDirectoryPath);

            using var reader = new StreamReader(_csvFilePath, encoding);
            string? line;
            while ((line = reader.ReadLine()) != null)
            {
                cancellationToken.ThrowIfCancellationRequested();
                lineNumber++;

                if (string.IsNullOrWhiteSpace(line))
                    continue;

                var item = ParseLine(line, lineNumber, errors);
                if (item != null)
                {
                    // 音声ファイルの存在確認（HashSet で O(1)）
                    if (audioFiles.Count > 0 && item.AudioFileName != null &&
                        audioFiles.TryGetValue(item.AudioFileName, out var fullAudioPath))
                    {
                        item.AudioFilePath = fullAudioPath;
                        item.Duration = WavDurationReader.GetDuration(fullAudioPath);
                    }
                    else
                    {
                        item.Duration = 3.0;
                    }

                    items.Add(item);
                }

                if (lineNumber % 100 == 0)
                {
                    progress?.Report(new CsvReadProgress
                    {
                        LinesProcessed = lineNumber,
                        TotalLines = totalLines,
                        ItemsCreated = items.Count,
                        ErrorCount = errors.Count
                    });
                }
            }

            // タイムライン時刻を計算
            CalculateTimeline(items);

            // 最終進捗
            progress?.Report(new CsvReadProgress
            {
                LinesProcessed = lineNumber,
                TotalLines = totalLines,
                ItemsCreated = items.Count,
                ErrorCount = errors.Count
            });

            return new CsvReadResult
            {
                Items = items,
                Errors = errors,
                TotalLinesRead = lineNumber,
                DetectedEncoding = encoding
            };
        }

        /// <summary>
        /// BOMスニッフィングによるエンコーディング検出
        /// </summary>
        private static Encoding DetectEncoding(string filePath)
        {
            var bom = new byte[4];
            using (var fs = File.OpenRead(filePath))
            {
                int read = fs.Read(bom, 0, 4);
                if (read < 2)
                    return new UTF8Encoding(false);
            }

            if (bom[0] == 0xEF && bom[1] == 0xBB && bom[2] == 0xBF)
                return new UTF8Encoding(true);
            if (bom[0] == 0xFF && bom[1] == 0xFE)
                return Encoding.Unicode;
            if (bom[0] == 0xFE && bom[1] == 0xFF)
                return Encoding.BigEndianUnicode;

            return new UTF8Encoding(false);
        }

        /// <summary>
        /// 行数カウント（進捗計算用）
        /// </summary>
        private static int CountLines(string filePath, Encoding encoding)
        {
            int count = 0;
            using var reader = new StreamReader(filePath, encoding);
            while (reader.ReadLine() != null) count++;
            return count;
        }

        /// <summary>
        /// 音声ディレクトリのWAVファイルを一括スキャンしてHashSetに格納
        /// </summary>
        private static Dictionary<string, string> ScanAudioDirectory(string? audioDir)
        {
            var result = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);

            if (string.IsNullOrEmpty(audioDir) || !Directory.Exists(audioDir))
                return result;

            foreach (var file in Directory.GetFiles(audioDir, "*.wav"))
            {
                var fileName = Path.GetFileName(file);
                if (fileName != null)
                    result[fileName] = file;
            }

            return result;
        }

        /// <summary>
        /// 1行をパースしてCsvTimelineItemを作成。エラーはリストに追加。
        /// </summary>
        private CsvTimelineItem? ParseLine(string line, int lineNumber, List<CsvReadError> errors)
        {
            var parts = ParseCsvLine(line);

            if (parts.Count < 2)
            {
                errors.Add(new CsvReadError
                {
                    LineNumber = lineNumber,
                    RawLine = line.Length > 100 ? line.Substring(0, 100) + "..." : line,
                    ErrorMessage = $"列数不足（{parts.Count}列、最低2列必要）",
                    Severity = CsvErrorSeverity.Warning
                });
                return null;
            }

            var speaker = parts[0].Trim();
            var text = parts[1].Trim();

            if (string.IsNullOrWhiteSpace(speaker) && string.IsNullOrWhiteSpace(text))
            {
                errors.Add(new CsvReadError
                {
                    LineNumber = lineNumber,
                    RawLine = line.Length > 100 ? line.Substring(0, 100) + "..." : line,
                    ErrorMessage = "話者とテキストが両方空です",
                    Severity = CsvErrorSeverity.Warning
                });
                return null;
            }

            string? imagePath = parts.Count >= 3 ? parts[2].Trim() : null;
            if (!string.IsNullOrEmpty(imagePath) && !File.Exists(imagePath))
            {
                errors.Add(new CsvReadError
                {
                    LineNumber = lineNumber,
                    RawLine = line.Length > 100 ? line.Substring(0, 100) + "..." : line,
                    ErrorMessage = $"画像ファイルが見つかりません: {imagePath}",
                    Severity = CsvErrorSeverity.Warning
                });
                imagePath = null;
            }

            return new CsvTimelineItem
            {
                LineNumber = lineNumber,
                Speaker = speaker,
                Text = text,
                ImageFilePath = string.IsNullOrEmpty(imagePath) ? null : imagePath
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

                if (item.Duration.HasValue)
                {
                    currentTime += item.Duration.Value;
                }
                else
                {
                    currentTime += 3.0;
                }
            }
        }
    }
}

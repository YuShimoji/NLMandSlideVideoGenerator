using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;

namespace NLMSlidePlugin.Core
{
    /// <summary>
    /// CSV読み取り結果（アイテム＋エラー収集）
    /// </summary>
    public class CsvReadResult
    {
        public List<CsvTimelineItem> Items { get; init; } = new();
        public List<CsvReadError> Errors { get; init; } = new();
        public int TotalLinesRead { get; init; }
        public Encoding DetectedEncoding { get; init; } = Encoding.UTF8;

        public bool HasErrors => Errors.Any(e => e.Severity == CsvErrorSeverity.Error);
        public bool HasWarnings => Errors.Any(e => e.Severity == CsvErrorSeverity.Warning);

        /// <summary>
        /// Warning severity のエラーのみを返す（UI表示用）
        /// </summary>
        public List<CsvReadError> Warnings => Errors.Where(e => e.Severity == CsvErrorSeverity.Warning).ToList();

        /// <summary>
        /// Error severity のエラーのみを返す（UI表示用）
        /// </summary>
        public List<CsvReadError> CriticalErrors => Errors.Where(e => e.Severity == CsvErrorSeverity.Error).ToList();

        public int AudioFoundCount => Items.Count(i => !string.IsNullOrEmpty(i.AudioFilePath));
        public int AudioMissingCount => Items.Count(i => string.IsNullOrEmpty(i.AudioFilePath));
    }

    /// <summary>
    /// CSV読み取りエラー
    /// </summary>
    public class CsvReadError
    {
        public int LineNumber { get; init; }
        public string RawLine { get; init; } = string.Empty;
        public string ErrorMessage { get; init; } = string.Empty;
        public CsvErrorSeverity Severity { get; init; }

        public override string ToString() => $"Line {LineNumber}: [{Severity}] {ErrorMessage}";
    }

    public enum CsvErrorSeverity
    {
        Warning,
        Error
    }

    /// <summary>
    /// CSV読み取り進捗
    /// </summary>
    public class CsvReadProgress
    {
        public int LinesProcessed { get; init; }
        public int TotalLines { get; init; }
        public int ItemsCreated { get; init; }
        public int ErrorCount { get; init; }
        public double PercentComplete => TotalLines > 0 ? (LinesProcessed * 100.0 / TotalLines) : 0;
    }
}

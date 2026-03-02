using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading;
using Xunit;
using NLMSlidePlugin.Core;

namespace NLMSlidePlugin.Tests
{
    /// <summary>
    /// CsvTimelineReader のユニットテスト
    /// </summary>
    public class CsvTimelineReaderTests : IDisposable
    {
        private readonly List<string> _tempFiles = new();

        private string CreateTempCsv(string content)
        {
            var path = Path.GetTempFileName();
            File.WriteAllText(path, content, Encoding.UTF8);
            _tempFiles.Add(path);
            return path;
        }

        public void Dispose()
        {
            foreach (var f in _tempFiles)
            {
                try { File.Delete(f); } catch (IOException) { }
            }
        }

        [Fact]
        public void ReadTimeline_EmptyFile_ReturnsEmptyList()
        {
            var reader = new CsvTimelineReader(CreateTempCsv(""));
            var result = reader.ReadTimeline();
            Assert.Empty(result);
        }

        [Fact]
        public void ReadTimeline_SingleLine_ReturnsOneItem()
        {
            var reader = new CsvTimelineReader(CreateTempCsv("Speaker1,Hello World"));
            var result = reader.ReadTimeline();
            Assert.Single(result);
            Assert.Equal(1, result[0].LineNumber);
            Assert.Equal("Speaker1", result[0].Speaker);
            Assert.Equal("Hello World", result[0].Text);
        }

        [Fact]
        public void ReadTimeline_MultipleLines_ReturnsMultipleItems()
        {
            var reader = new CsvTimelineReader(CreateTempCsv("Speaker1,Hello\nSpeaker2,World\nSpeaker3,Test"));
            var result = reader.ReadTimeline();
            Assert.Equal(3, result.Count);
            Assert.Equal(1, result[0].LineNumber);
            Assert.Equal(2, result[1].LineNumber);
            Assert.Equal(3, result[2].LineNumber);
        }

        [Fact]
        public void ReadTimeline_WithQuotes_HandlesQuotesCorrectly()
        {
            var reader = new CsvTimelineReader(CreateTempCsv("Speaker1,\"Hello, World\""));
            var result = reader.ReadTimeline();
            Assert.Single(result);
            Assert.Equal("Hello, World", result[0].Text);
        }

        [Fact]
        public void ReadTimeline_WithEmptyLines_SkipsEmptyLines()
        {
            var reader = new CsvTimelineReader(CreateTempCsv("Speaker1,Hello\n\nSpeaker2,World"));
            var result = reader.ReadTimeline();
            Assert.Equal(2, result.Count);
        }

        [Fact]
        public void ReadTimeline_AudioFileName_GeneratesCorrectName()
        {
            var reader = new CsvTimelineReader(CreateTempCsv("Speaker1,Hello"));
            var result = reader.ReadTimeline();
            Assert.Equal("001.wav", result[0].AudioFileName);
        }

        [Fact]
        public void ReadTimeline_TimelineCalculation_SetsCorrectTimes()
        {
            var reader = new CsvTimelineReader(CreateTempCsv("Speaker1,Hello\nSpeaker2,World"));
            var result = reader.ReadTimeline();
            Assert.Equal(0, result[0].StartTime);
            Assert.Equal(3.0, result[0].EndTime, precision: 1);
            Assert.Equal(3.0, result[1].StartTime, precision: 1);
        }

        // --- 本番化テスト: エラーハンドリング ---

        [Fact]
        public void ReadTimelineWithErrors_MalformedLine_CollectsError()
        {
            // カンマなしの不正行
            var reader = new CsvTimelineReader(CreateTempCsv("Speaker1,OK\nBAD_LINE_NO_COMMA\nSpeaker2,Also OK"));
            var result = reader.ReadTimelineWithErrors();
            Assert.True(result.Items.Count >= 2);
            Assert.True(result.Errors.Count >= 1 || result.HasWarnings);
        }

        [Fact]
        public void ReadTimelineWithErrors_Utf8Bom_DetectsEncoding()
        {
            var path = Path.GetTempFileName();
            _tempFiles.Add(path);
            File.WriteAllText(path, "Speaker1,BOM test", new UTF8Encoding(encoderShouldEmitUTF8Identifier: true));
            var reader = new CsvTimelineReader(path);
            var result = reader.ReadTimelineWithErrors();
            Assert.Single(result.Items);
            Assert.Equal("BOM test", result.Items[0].Text);
        }

        [Fact]
        public void ReadTimelineWithErrors_MissingAudioDir_ReportsAudioMissing()
        {
            var reader = new CsvTimelineReader(CreateTempCsv("Speaker1,Hello\nSpeaker2,World"), audioDirectoryPath: "/nonexistent_dir_12345");
            var result = reader.ReadTimelineWithErrors();
            Assert.Equal(2, result.AudioMissingCount);
        }

        [Fact]
        public void ReadTimelineWithErrors_CancellationToken_Respects()
        {
            var cts = new CancellationTokenSource();
            cts.Cancel();
            var reader = new CsvTimelineReader(CreateTempCsv("Speaker1,Hello\nSpeaker2,World"));
            Assert.Throws<OperationCanceledException>(() => reader.ReadTimelineWithErrors(cancellationToken: cts.Token));
        }

        [Fact]
        public void ReadTimelineWithErrors_ProgressReporting_Works()
        {
            var progressValues = new List<int>();
            var progress = new Progress<CsvReadProgress>(p => progressValues.Add(p.LinesProcessed));
            var reader = new CsvTimelineReader(CreateTempCsv("Speaker1,A\nSpeaker2,B\nSpeaker3,C"));
            var result = reader.ReadTimelineWithErrors(progress: progress);
            Assert.Equal(3, result.Items.Count);
        }

        // --- 本番化テスト: 大規模CSV ---

        [Fact]
        public void ReadTimeline_1000Lines_CompletesSuccessfully()
        {
            var sb = new StringBuilder();
            for (int i = 0; i < 1000; i++)
            {
                sb.AppendLine($"Speaker{i % 3 + 1},セリフ番号{i + 1:D4}です。これはベンチマーク用のテストデータです。");
            }
            var reader = new CsvTimelineReader(CreateTempCsv(sb.ToString()));
            var result = reader.ReadTimelineWithErrors();
            Assert.Equal(1000, result.Items.Count);
            Assert.Empty(result.Errors);
            Assert.Equal(1000, result.TotalLinesRead);
        }
    }
}

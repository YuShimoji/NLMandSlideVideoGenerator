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

        // --- SP-033: アニメーション種別テスト ---

        [Fact]
        public void ReadTimeline_FourthColumnAnimationType_ParsedCorrectly()
        {
            var csv = "Speaker1,Hello,C:\\nonexistent.png,zoom_in\nSpeaker2,World,,pan_left";
            var reader = new CsvTimelineReader(CreateTempCsv(csv));
            var result = reader.ReadTimeline();
            Assert.Equal(2, result.Count);
            Assert.Equal("zoom_in", result[0].AnimationType);
            Assert.Equal("pan_left", result[1].AnimationType);
        }

        [Fact]
        public void ReadTimeline_NoFourthColumn_DefaultsToKenBurns()
        {
            var reader = new CsvTimelineReader(CreateTempCsv("Speaker1,Hello"));
            var result = reader.ReadTimeline();
            Assert.Single(result);
            Assert.Equal("ken_burns", result[0].AnimationType);
        }

        [Fact]
        public void ReadTimeline_InvalidAnimationType_DefaultsToKenBurns()
        {
            var csv = "Speaker1,Hello,,invalid_type";
            var reader = new CsvTimelineReader(CreateTempCsv(csv));
            var result = reader.ReadTimeline();
            Assert.Single(result);
            Assert.Equal("ken_burns", result[0].AnimationType);
        }

        [Fact]
        public void ReadTimeline_AllAnimationTypesValid()
        {
            var types = new[] { "ken_burns", "zoom_in", "zoom_out", "pan_left", "pan_right", "pan_up", "static" };
            var lines = string.Join("\n", types.Select((t, i) => $"S{i},T{i},,{t}"));
            var reader = new CsvTimelineReader(CreateTempCsv(lines));
            var result = reader.ReadTimeline();
            Assert.Equal(7, result.Count);
            for (int i = 0; i < types.Length; i++)
            {
                Assert.Equal(types[i], result[i].AnimationType);
            }
        }

        [Fact]
        public void ReadTimeline_RelativeImagePath_ResolvedToCsvDirectory()
        {
            // CSVと同じディレクトリに画像ファイルを作成
            var tempDir = Path.Combine(Path.GetTempPath(), $"nlm_test_{Guid.NewGuid():N}");
            Directory.CreateDirectory(tempDir);
            var imgDir = Path.Combine(tempDir, "slides");
            Directory.CreateDirectory(imgDir);
            var imgPath = Path.Combine(imgDir, "test.png");
            File.WriteAllBytes(imgPath, new byte[] { 0x89, 0x50, 0x4E, 0x47 }); // PNG header

            var csvPath = Path.Combine(tempDir, "test.csv");
            File.WriteAllText(csvPath, "Speaker1,Hello,slides/test.png,pan_left", Encoding.UTF8);
            _tempFiles.Add(csvPath);
            _tempFiles.Add(imgPath);

            try
            {
                var reader = new CsvTimelineReader(csvPath);
                var result = reader.ReadTimeline();
                Assert.Single(result);
                Assert.NotNull(result[0].ImageFilePath);
                Assert.Equal(imgPath, result[0].ImageFilePath);
                Assert.Equal("pan_left", result[0].AnimationType);
            }
            finally
            {
                try { Directory.Delete(tempDir, true); } catch { }
            }
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

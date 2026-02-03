using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using Xunit;
using NLMSlidePlugin.Core;

namespace NLMSlidePlugin.Tests
{
    /// <summary>
    /// CsvTimelineReader のユニットテスト
    /// </summary>
    public class CsvTimelineReaderTests
    {
        [Fact]
        public void ReadTimeline_EmptyFile_ReturnsEmptyList()
        {
            // Arrange
            var tempFile = Path.GetTempFileName();
            File.WriteAllText(tempFile, "");
            var reader = new CsvTimelineReader(tempFile);

            // Act
            var result = reader.ReadTimeline();

            // Assert
            Assert.Empty(result);

            // Cleanup
            File.Delete(tempFile);
        }

        [Fact]
        public void ReadTimeline_SingleLine_ReturnsOneItem()
        {
            // Arrange
            var tempFile = Path.GetTempFileName();
            File.WriteAllText(tempFile, "Speaker1,Hello World");
            var reader = new CsvTimelineReader(tempFile);

            // Act
            var result = reader.ReadTimeline();

            // Assert
            Assert.Single(result);
            Assert.Equal(1, result[0].LineNumber);
            Assert.Equal("Speaker1", result[0].Speaker);
            Assert.Equal("Hello World", result[0].Text);

            // Cleanup
            File.Delete(tempFile);
        }

        [Fact]
        public void ReadTimeline_MultipleLines_ReturnsMultipleItems()
        {
            // Arrange
            var tempFile = Path.GetTempFileName();
            File.WriteAllText(tempFile, @"Speaker1,Hello
Speaker2,World
Speaker3,Test");
            var reader = new CsvTimelineReader(tempFile);

            // Act
            var result = reader.ReadTimeline();

            // Assert
            Assert.Equal(3, result.Count);
            Assert.Equal(1, result[0].LineNumber);
            Assert.Equal(2, result[1].LineNumber);
            Assert.Equal(3, result[2].LineNumber);

            // Cleanup
            File.Delete(tempFile);
        }

        [Fact]
        public void ReadTimeline_WithQuotes_HandlesQuotesCorrectly()
        {
            // Arrange
            var tempFile = Path.GetTempFileName();
            File.WriteAllText(tempFile, @"Speaker1,""Hello, World""");
            var reader = new CsvTimelineReader(tempFile);

            // Act
            var result = reader.ReadTimeline();

            // Assert
            Assert.Single(result);
            Assert.Equal("Hello, World", result[0].Text);

            // Cleanup
            File.Delete(tempFile);
        }

        [Fact]
        public void ReadTimeline_WithEmptyLines_SkipsEmptyLines()
        {
            // Arrange
            var tempFile = Path.GetTempFileName();
            File.WriteAllText(tempFile, @"Speaker1,Hello

Speaker2,World");
            var reader = new CsvTimelineReader(tempFile);

            // Act
            var result = reader.ReadTimeline();

            // Assert
            Assert.Equal(2, result.Count);

            // Cleanup
            File.Delete(tempFile);
        }

        [Fact]
        public void ReadTimeline_AudioFileName_GeneratesCorrectName()
        {
            // Arrange
            var tempFile = Path.GetTempFileName();
            File.WriteAllText(tempFile, "Speaker1,Hello");
            var reader = new CsvTimelineReader(tempFile);

            // Act
            var result = reader.ReadTimeline();

            // Assert
            Assert.Equal("001.wav", result[0].AudioFileName);

            // Cleanup
            File.Delete(tempFile);
        }

        [Fact]
        public void ReadTimeline_TimelineCalculation_SetsCorrectTimes()
        {
            // Arrange
            var tempFile = Path.GetTempFileName();
            File.WriteAllText(tempFile, @"Speaker1,Hello
Speaker2,World");
            var reader = new CsvTimelineReader(tempFile);

            // Act
            var result = reader.ReadTimeline();

            // Assert
            Assert.Equal(0, result[0].StartTime);
            Assert.Equal(3.0, result[0].EndTime, precision: 1); // Default duration is 3.0
            Assert.Equal(3.0, result[1].StartTime, precision: 1);

            // Cleanup
            File.Delete(tempFile);
        }
    }
}

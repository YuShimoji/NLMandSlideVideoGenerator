using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using Xunit;
using NLMSlidePlugin.Core;

namespace NLMSlidePlugin.Tests
{
    /// <summary>
    /// OverlayImporter のユニットテスト (SP-052)
    /// </summary>
    public class OverlayImporterTests : IDisposable
    {
        private readonly List<string> _tempFiles = new();

        private string CreateTempJson(string content)
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
        public void LoadPlan_ValidJson_ReturnsOverlayPlan()
        {
            var json = @"{
                ""version"": ""1.0"",
                ""overlays"": [
                    {
                        ""type"": ""chapter_title"",
                        ""text"": ""導入"",
                        ""segment_index"": 0,
                        ""duration_sec"": 4.0,
                        ""position"": ""top_center"",
                        ""style"": ""default""
                    }
                ]
            }";
            var path = CreateTempJson(json);
            var plan = OverlayImporter.LoadPlan(path);

            Assert.NotNull(plan);
            Assert.Equal("1.0", plan!.Version);
            Assert.Single(plan.Overlays);
            Assert.Equal("chapter_title", plan.Overlays[0].Type);
            Assert.Equal("導入", plan.Overlays[0].Text);
            Assert.Equal(0, plan.Overlays[0].SegmentIndex);
        }

        [Fact]
        public void LoadPlan_MultipleOverlays_ReturnsAll()
        {
            var json = @"{
                ""version"": ""1.0"",
                ""overlays"": [
                    {
                        ""type"": ""chapter_title"",
                        ""text"": ""第1章"",
                        ""segment_index"": 0,
                        ""duration_sec"": 4.0,
                        ""position"": ""top_center"",
                        ""style"": ""default""
                    },
                    {
                        ""type"": ""key_point"",
                        ""text"": ""重要なポイント"",
                        ""segment_index"": 3,
                        ""duration_sec"": 7.0,
                        ""position"": ""lower_third"",
                        ""style"": ""default""
                    },
                    {
                        ""type"": ""statistic"",
                        ""text"": ""利用者数: 1億人"",
                        ""segment_index"": 5,
                        ""duration_sec"": 4.0,
                        ""position"": ""center_upper"",
                        ""style"": ""emphasis"",
                        ""value"": ""100000000""
                    }
                ]
            }";
            var path = CreateTempJson(json);
            var plan = OverlayImporter.LoadPlan(path);

            Assert.NotNull(plan);
            Assert.Equal(3, plan!.Overlays.Count);
            Assert.Equal("statistic", plan.Overlays[2].Type);
            Assert.Equal("100000000", plan.Overlays[2].Value);
        }

        [Fact]
        public void LoadPlan_FileNotFound_ReturnsNull()
        {
            var plan = OverlayImporter.LoadPlan("/nonexistent/overlay_plan.json");
            Assert.Null(plan);
        }

        [Fact]
        public void LoadPlan_InvalidJson_ReturnsNull()
        {
            var path = CreateTempJson("{ invalid json }}}");
            var plan = OverlayImporter.LoadPlan(path);
            Assert.Null(plan);
        }

        [Fact]
        public void LoadPlan_EmptyOverlays_ReturnsEmptyList()
        {
            var json = @"{ ""version"": ""1.0"", ""overlays"": [] }";
            var path = CreateTempJson(json);
            var plan = OverlayImporter.LoadPlan(path);

            Assert.NotNull(plan);
            Assert.Empty(plan!.Overlays);
        }

        [Fact]
        public void ConvertToTextItems_BasicConversion()
        {
            var plan = new OverlayImporter.OverlayPlan
            {
                Overlays = new List<OverlayImporter.OverlayEntry>
                {
                    new()
                    {
                        Type = "chapter_title",
                        Text = "第1章: AI入門",
                        SegmentIndex = 0,
                        DurationSec = 4.0,
                        Position = "top_center",
                        Style = "default"
                    }
                }
            };

            var segmentFrames = new Dictionary<int, int> { { 0, 0 } };
            var items = OverlayImporter.ConvertToTextItems(plan, segmentFrames, 60, 1920, 1080);

            Assert.Single(items);
            var item = items[0];
            Assert.Equal("第1章: AI入門", item.Text);
            Assert.Equal(64, item.FontSize); // chapter_title default
            Assert.True(item.Bold);
            Assert.Equal(0, item.Frame);
            Assert.Equal(240, item.Length); // 4.0 * 60fps
        }

        [Fact]
        public void ConvertToTextItems_SkipsMissingSegments()
        {
            var plan = new OverlayImporter.OverlayPlan
            {
                Overlays = new List<OverlayImporter.OverlayEntry>
                {
                    new()
                    {
                        Type = "key_point",
                        Text = "テスト",
                        SegmentIndex = 99, // Not in segmentFrames
                        DurationSec = 7.0,
                        Position = "lower_third"
                    }
                }
            };

            var segmentFrames = new Dictionary<int, int> { { 0, 0 }, { 1, 600 } };
            var items = OverlayImporter.ConvertToTextItems(plan, segmentFrames, 60, 1920, 1080);

            Assert.Empty(items);
        }

        [Fact]
        public void ConvertToTextItems_UsesCustomOverlayConfig()
        {
            var plan = new OverlayImporter.OverlayPlan
            {
                Overlays = new List<OverlayImporter.OverlayEntry>
                {
                    new()
                    {
                        Type = "statistic",
                        Text = "1億人突破",
                        SegmentIndex = 0,
                        DurationSec = 4.0,
                        Position = "center_upper",
                        Style = "emphasis"
                    }
                }
            };

            var config = new StyleTemplateLoader.OverlayConfig();
            config.Statistic.FontSize = 96; // custom size

            var segmentFrames = new Dictionary<int, int> { { 0, 0 } };
            var items = OverlayImporter.ConvertToTextItems(plan, segmentFrames, 60, 1920, 1080, config);

            Assert.Single(items);
            Assert.Equal(96, items[0].FontSize);
        }

        [Fact]
        public void ConvertToTextItems_CalculatesYPosition()
        {
            var plan = new OverlayImporter.OverlayPlan
            {
                Overlays = new List<OverlayImporter.OverlayEntry>
                {
                    new()
                    {
                        Type = "key_point",
                        Text = "テスト",
                        SegmentIndex = 0,
                        DurationSec = 7.0,
                        Position = "lower_third"
                    }
                }
            };

            var segmentFrames = new Dictionary<int, int> { { 0, 0 } };
            var items = OverlayImporter.ConvertToTextItems(plan, segmentFrames, 60, 1920, 1080);

            Assert.Single(items);
            // key_point y_offset_ratio = 0.70, 1080 * 0.70 = 756
            Assert.Equal(756, items[0].Y);
        }

        [Fact]
        public void LoadPlanFromCsvDir_FindsOverlayInSameDir()
        {
            // Create temp directory with overlay_plan.json
            var tempDir = Path.Combine(Path.GetTempPath(), "overlay_test_" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(tempDir);
            _tempFiles.Add(tempDir);

            var csvPath = Path.Combine(tempDir, "timeline.csv");
            File.WriteAllText(csvPath, "speaker,text");
            _tempFiles.Add(csvPath);

            var overlayPath = Path.Combine(tempDir, "overlay_plan.json");
            File.WriteAllText(overlayPath, @"{ ""version"": ""1.0"", ""overlays"": [] }");
            _tempFiles.Add(overlayPath);

            var plan = OverlayImporter.LoadPlanFromCsvDir(csvPath);
            Assert.NotNull(plan);
            Assert.Equal("1.0", plan!.Version);

            // Cleanup
            try { Directory.Delete(tempDir, true); } catch { }
        }
    }
}

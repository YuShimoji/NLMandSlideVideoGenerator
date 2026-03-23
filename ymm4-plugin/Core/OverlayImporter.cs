using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;

namespace NLMSlidePlugin.Core
{
    /// <summary>
    /// SP-052: overlay_plan.json を読み込み、YMM4 TextItem 配置データを生成する。
    /// Python の OverlayPlanner が出力した overlay_plan.json を消費し、
    /// Layer 7 に配置するテキストオーバーレイのパラメータを提供する。
    /// </summary>
    public class OverlayImporter
    {
        public const string OverlayPlanFileName = "overlay_plan.json";

        // ---- データモデル ----

        public class OverlayEntry
        {
            public string Type { get; set; } = string.Empty;
            public string Text { get; set; } = string.Empty;
            public int SegmentIndex { get; set; }
            public double DurationSec { get; set; }
            public string Position { get; set; } = "top_center";
            public string Style { get; set; } = "default";
            public string? Value { get; set; }
        }

        public class OverlayPlan
        {
            public string Version { get; set; } = "1.0";
            public List<OverlayEntry> Overlays { get; set; } = new();
        }

        /// <summary>
        /// TextItem に適用するスタイルパラメータ。
        /// YMM4 API の TextItem プロパティにマッピングする。
        /// </summary>
        public class TextItemParams
        {
            public string Text { get; set; } = string.Empty;
            public int FontSize { get; set; } = 40;
            public System.Windows.Media.Color FontColor { get; set; }
            public bool Bold { get; set; }
            public bool Italic { get; set; }
            public string BasePoint { get; set; } = "CenterTop";
            public int X { get; set; }
            public int Y { get; set; }
            public int Layer { get; set; } = 17; // Layer 7 relative offset
            public int Frame { get; set; }
            public int Length { get; set; }
            public double FadeInSec { get; set; } = 0.5;
            public double FadeOutSec { get; set; } = 0.5;
            public int SegmentIndex { get; set; }
        }

        // ---- 読み込み ----

        private static readonly JsonSerializerOptions _jsonOptions = new()
        {
            PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
            ReadCommentHandling = JsonCommentHandling.Skip,
            AllowTrailingCommas = true,
        };

        /// <summary>
        /// overlay_plan.json を読み込む。
        /// </summary>
        public static OverlayPlan? LoadPlan(string path, Action<string>? log = null)
        {
            if (!File.Exists(path))
            {
                log?.Invoke($"OverlayImporter: {path} not found, skipping overlay import");
                return null;
            }

            try
            {
                var json = File.ReadAllText(path);
                var plan = JsonSerializer.Deserialize<OverlayPlan>(json, _jsonOptions);
                log?.Invoke($"OverlayImporter: loaded {plan?.Overlays?.Count ?? 0} overlays from {path}");
                return plan;
            }
            catch (Exception ex)
            {
                log?.Invoke($"OverlayImporter: parse error ({path}): {ex.Message}");
                return null;
            }
        }

        /// <summary>
        /// overlay_plan.json を CSV と同じディレクトリから検索して読み込む。
        /// </summary>
        public static OverlayPlan? LoadPlanFromCsvDir(string csvFilePath, Action<string>? log = null)
        {
            var dir = Path.GetDirectoryName(csvFilePath);
            if (string.IsNullOrEmpty(dir)) return null;

            var path = Path.Combine(dir, OverlayPlanFileName);
            return LoadPlan(path, log);
        }

        // ---- TextItem パラメータ変換 ----

        /// <summary>
        /// OverlayPlan のエントリを TextItemParams に変換する。
        /// セグメントの開始フレーム情報と style_template 設定が必要。
        /// </summary>
        /// <param name="plan">オーバーレイプラン</param>
        /// <param name="segmentStartFrames">各セグメントの開始フレーム (index -> frame)</param>
        /// <param name="fps">FPS</param>
        /// <param name="videoWidth">動画幅 (px)</param>
        /// <param name="videoHeight">動画高 (px)</param>
        /// <param name="overlayConfig">style_template の overlay 設定 (null でデフォルト)</param>
        /// <param name="overlayBaseLayer">オーバーレイの基本レイヤー番号</param>
        public static List<TextItemParams> ConvertToTextItems(
            OverlayPlan plan,
            Dictionary<int, int> segmentStartFrames,
            int fps,
            int videoWidth,
            int videoHeight,
            StyleTemplateLoader.OverlayConfig? overlayConfig = null,
            int overlayBaseLayer = 17)
        {
            var result = new List<TextItemParams>();
            var config = overlayConfig ?? new StyleTemplateLoader.OverlayConfig();

            foreach (var entry in plan.Overlays)
            {
                if (!segmentStartFrames.TryGetValue(entry.SegmentIndex, out int startFrame))
                    continue;

                var typeConfig = GetTypeConfig(config, entry.Type);
                int lengthFrames = Math.Max(1, (int)Math.Round(entry.DurationSec * fps));

                var (x, y, basePoint) = CalculatePosition(
                    typeConfig.Position, typeConfig.YOffsetRatio, videoWidth, videoHeight);

                result.Add(new TextItemParams
                {
                    Text = entry.Text,
                    FontSize = typeConfig.FontSize,
                    FontColor = StyleTemplateLoader.ParseHexColor(typeConfig.FontColor),
                    Bold = typeConfig.Bold,
                    Italic = typeConfig.Italic,
                    BasePoint = basePoint,
                    X = x,
                    Y = y,
                    Layer = overlayBaseLayer,
                    Frame = startFrame,
                    Length = lengthFrames,
                    FadeInSec = typeConfig.FadeInSec,
                    FadeOutSec = typeConfig.FadeOutSec,
                    SegmentIndex = entry.SegmentIndex,
                });
            }

            return result;
        }

        private static StyleTemplateLoader.OverlayTypeConfig GetTypeConfig(
            StyleTemplateLoader.OverlayConfig config, string type)
        {
            return type switch
            {
                "chapter_title" => config.ChapterTitle,
                "key_point" => config.KeyPoint,
                "statistic" => config.Statistic,
                "source_citation" => config.SourceCitation,
                _ => config.KeyPoint, // fallback
            };
        }

        private static (int x, int y, string basePoint) CalculatePosition(
            string position, double yOffsetRatio, int videoWidth, int videoHeight)
        {
            int y = (int)(videoHeight * yOffsetRatio);

            return position switch
            {
                "top_center" => (0, y, "CenterTop"),
                "lower_third" => (0, y, "CenterTop"),
                "center_upper" => (0, y, "CenterTop"),
                "above_subtitle" => (0, y, "CenterTop"),
                _ => (0, y, "CenterTop"),
            };
        }
    }
}

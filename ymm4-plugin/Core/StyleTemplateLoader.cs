using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;

namespace NLMSlidePlugin.Core
{
    /// <summary>
    /// style_template.json を読み込み、スタイル設定値を提供する (SP-031)。
    /// C# プラグインと Python パイプラインで同一 JSON を共有する。
    /// </summary>
    public class StyleTemplateLoader
    {
        /// <summary>テンプレートファイル名。CSVと同じディレクトリ or config/ に配置。</summary>
        public const string TemplateFileName = "style_template.json";

        // ---- データクラス ----

        public class VideoConfig
        {
            public int Width { get; set; } = 1920;
            public int Height { get; set; } = 1080;
            public int Fps { get; set; } = 60;
        }

        public class SubtitleConfig
        {
            public int FontSize { get; set; } = 48;
            public double YPositionRatio { get; set; } = 0.35;
            public string BasePoint { get; set; } = "CenterBottom";
            public double MaxWidthRatio { get; set; } = 0.9;
            public string WordWrap { get; set; } = "Character";
            public bool Bold { get; set; } = true;
            public string Style { get; set; } = "Border";
            public string StyleColor { get; set; } = "#000000";
        }

        public class AnimationConfig
        {
            public double KenBurnsZoomRatio { get; set; } = 1.05;
            public double ZoomInRatio { get; set; } = 1.15;
            public double ZoomOutRatio { get; set; } = 1.15;
            public double PanZoomRatio { get; set; } = 1.12;
            public double PanDistanceRatio { get; set; } = 0.05;
        }

        public class CrossfadeConfig
        {
            public bool Enabled { get; set; } = true;
            public double DurationSeconds { get; set; } = 0.5;
        }

        public class TimingConfig
        {
            public double PaddingSeconds { get; set; } = 0.3;
            public double DefaultDurationSeconds { get; set; } = 3.0;
        }

        public class BgmConfig
        {
            public double VolumePercent { get; set; } = 30.0;
            public double FadeInSeconds { get; set; } = 2.0;
            public double FadeOutSeconds { get; set; } = 2.0;
            public int Layer { get; set; } = 0;
        }

        public class ValidationConfig
        {
            public double MaxTotalDurationSeconds { get; set; } = 3600.0;
            public double WarnGapThresholdSeconds { get; set; } = 1.0;
            public double WarnOverlapThresholdSeconds { get; set; } = -0.1;
        }

        // ---- 集約クラス ----

        public class StyleTemplate
        {
            public string Version { get; set; } = "1.0.0";
            public VideoConfig Video { get; set; } = new();
            public SubtitleConfig Subtitle { get; set; } = new();
            public List<string> SpeakerColors { get; set; } = new()
            {
                "#FFFFFF", "#FFFF64", "#64FFFF", "#64FF96", "#FFB464", "#C896FF"
            };
            public AnimationConfig Animation { get; set; } = new();
            public BgmConfig Bgm { get; set; } = new();
            public CrossfadeConfig Crossfade { get; set; } = new();
            public TimingConfig Timing { get; set; } = new();
            public ValidationConfig Validation { get; set; } = new();
        }

        // ---- 読み込みロジック ----

        private static readonly JsonSerializerOptions _jsonOptions = new()
        {
            PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
            ReadCommentHandling = JsonCommentHandling.Skip,
            AllowTrailingCommas = true,
        };

        /// <summary>
        /// スタイルテンプレートを読み込む。
        /// 検索順: csvDir/style_template.json → configDir/style_template.json → デフォルト値
        /// </summary>
        /// <param name="csvFilePath">CSV ファイルのパス (同一ディレクトリを最初に検索)</param>
        /// <param name="configDir">設定ディレクトリ (Python config/ ディレクトリ相当)</param>
        /// <param name="log">ログ出力アクション</param>
        /// <returns>StyleTemplate インスタンス</returns>
        public static StyleTemplate Load(
            string? csvFilePath = null,
            string? configDir = null,
            Action<string>? log = null)
        {
            var searchPaths = new List<string>();

            // 1. CSV と同じディレクトリ
            if (!string.IsNullOrEmpty(csvFilePath))
            {
                var dir = Path.GetDirectoryName(csvFilePath);
                if (!string.IsNullOrEmpty(dir))
                    searchPaths.Add(Path.Combine(dir, TemplateFileName));
            }

            // 2. 明示的な config ディレクトリ
            if (!string.IsNullOrEmpty(configDir))
            {
                searchPaths.Add(Path.Combine(configDir, TemplateFileName));
            }

            // 3. CSV から上位に config/ を探索
            if (!string.IsNullOrEmpty(csvFilePath))
            {
                var dir = Path.GetDirectoryName(csvFilePath);
                for (int i = 0; i < 5 && !string.IsNullOrEmpty(dir); i++)
                {
                    var candidate = Path.Combine(dir, "config", TemplateFileName);
                    if (!searchPaths.Contains(candidate))
                        searchPaths.Add(candidate);
                    dir = Path.GetDirectoryName(dir);
                }
            }

            foreach (var path in searchPaths)
            {
                if (File.Exists(path))
                {
                    try
                    {
                        var json = File.ReadAllText(path);
                        var template = JsonSerializer.Deserialize<StyleTemplate>(json, _jsonOptions);
                        if (template != null)
                        {
                            log?.Invoke($"StyleTemplate loaded: {path} (v{template.Version})");
                            return template;
                        }
                    }
                    catch (Exception ex)
                    {
                        log?.Invoke($"StyleTemplate parse error ({path}): {ex.Message}");
                    }
                }
            }

            log?.Invoke("StyleTemplate: using defaults (no template file found)");
            return new StyleTemplate();
        }

        /// <summary>
        /// #RRGGBB 文字列を System.Windows.Media.Color に変換する。
        /// </summary>
        public static System.Windows.Media.Color ParseHexColor(string hex)
        {
            if (string.IsNullOrEmpty(hex) || hex.Length != 7 || hex[0] != '#')
                return System.Windows.Media.Color.FromRgb(255, 255, 255);

            try
            {
                byte r = Convert.ToByte(hex.Substring(1, 2), 16);
                byte g = Convert.ToByte(hex.Substring(3, 2), 16);
                byte b = Convert.ToByte(hex.Substring(5, 2), 16);
                return System.Windows.Media.Color.FromRgb(r, g, b);
            }
            catch
            {
                return System.Windows.Media.Color.FromRgb(255, 255, 255);
            }
        }
    }
}

using Microsoft.Win32;
using NLMSlidePlugin.Core;
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.IO;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Reflection;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;
using YukkuriMovieMaker.Project;
using YukkuriMovieMaker.Project.Items;

namespace NLMSlidePlugin.TimelinePlugin
{
    /// <summary>
    /// CSV import dialog for timeline import.
    /// </summary>
    public partial class CsvImportDialog : Window, INotifyPropertyChanged
    {
        private Timeline? timeline;
        private string csvPath = string.Empty;
        private string statusMessage = "Select a CSV file.";
        private bool addSubtitles = true;
        private List<CsvTimelineItem> previewItems = new();
        private static bool _voiceMethodsDumped;
        private double progressValue;
        private string bgmPath = string.Empty;
        private double bgmVolume = 30.0;

        public event PropertyChangedEventHandler? PropertyChanged;

        public CsvImportDialog(Timeline? timeline = null)
        {
            this.timeline = timeline;
            InitializeComponent();
            DataContext = this;
        }

        public string CsvPath
        {
            get => csvPath;
            set
            {
                csvPath = value;
                OnPropertyChanged();
            }
        }

        public string StatusMessage
        {
            get => statusMessage;
            set
            {
                statusMessage = value;
                OnPropertyChanged();
            }
        }

        public bool AddSubtitles
        {
            get => addSubtitles;
            set
            {
                addSubtitles = value;
                OnPropertyChanged();
            }
        }

        public string BgmPath
        {
            get => bgmPath;
            set { bgmPath = value; OnPropertyChanged(); }
        }

        public double BgmVolume
        {
            get => bgmVolume;
            set { bgmVolume = value; OnPropertyChanged(); }
        }

        public List<CsvTimelineItem> PreviewItems
        {
            get => previewItems;
            set
            {
                previewItems = value;
                PreviewDataGrid.ItemsSource = value;
                OnPropertyChanged();
            }
        }

        public double ProgressValue
        {
            get => progressValue;
            set { progressValue = value; OnPropertyChanged(); }
        }

        private string logContent = string.Empty;
        public string LogContent
        {
            get => logContent;
            set { logContent = value; OnPropertyChanged(); }
        }

        public void AppendLog(string message)
        {
            LogContent += $"[{DateTime.Now:HH:mm:ss}] {message}{Environment.NewLine}";
        }

        private void BrowseCsvButton_Click(object sender, RoutedEventArgs e)
        {
            var dialog = new OpenFileDialog
            {
                Filter = "CSV files (*.csv)|*.csv|All files (*.*)|*.*",
                Title = "Select CSV File",
                CheckFileExists = true
            };

            if (dialog.ShowDialog() != true) return;

            CsvPath = dialog.FileName;
            StatusMessage = "CSV selected.";
            AppendLog($"CSV selected: {CsvPath}");
        }

        private void BrowseBgmButton_Click(object sender, RoutedEventArgs e)
        {
            var dialog = new OpenFileDialog
            {
                Filter = "Audio files (*.wav;*.mp3;*.m4a)|*.wav;*.mp3;*.m4a|All files (*.*)|*.*",
                Title = "BGMファイルを選択",
                CheckFileExists = true
            };

            if (dialog.ShowDialog() != true) return;

            BgmPath = dialog.FileName;
            AppendLog($"BGM selected: {BgmPath}");
        }

        private async void PreviewButton_Click(object sender, RoutedEventArgs e)
        {
            if (string.IsNullOrWhiteSpace(CsvPath) || !File.Exists(CsvPath))
            {
                StatusMessage = "Invalid CSV path.";
                return;
            }

            try
            {
                SetBusy(true);
                StatusMessage = "Loading preview...";
                ProgressValue = 0;
                LogContent = string.Empty;
                AppendLog($"Preview start: {CsvPath}");

                var progress = new Progress<CsvReadProgress>(p =>
                {
                    ProgressValue = p.PercentComplete;
                    StatusMessage = $"Reading CSV: {p.LinesProcessed} lines...";
                });

                // Capture UI state before Task.Run to avoid cross-thread access
                string capturedCsvPath = CsvPath;
                var result = await Task.Run(() =>
                {
                    var reader = new CsvTimelineReader(capturedCsvPath);
                    return reader.ReadTimelineWithErrors(progress);
                });

                PreviewItems = result.Items;
                ProgressValue = 100;

                foreach (var warn in result.Warnings) AppendLog($"[WARN] {warn}");
                foreach (var err in result.Errors) AppendLog($"[ERR] {err}");

                StatusMessage = result.Errors.Count > 0
                    ? $"Found {result.Items.Count} items with {result.Errors.Count} errors."
                    : $"Found {result.Items.Count} items.";

                AppendLog($"Preview done: {result.Items.Count} items, {result.Errors.Count} errors, {result.Warnings.Count} warnings.");
            }
            catch (Exception ex)
            {
                StatusMessage = $"Preview failed: {ex.Message}";
                AppendLog($"[FATAL] {ex}");
            }
            finally
            {
                SetBusy(false);
            }
        }

        private void ExportDaihonButton_Click(object sender, RoutedEventArgs e)
        {
            if (PreviewItems.Count == 0)
            {
                StatusMessage = "先にプレビューを実行してください。";
                return;
            }

            try
            {
                var saveDialog = new SaveFileDialog
                {
                    Title = "台本CSVとして保存",
                    Filter = "CSV files (*.csv)|*.csv",
                    DefaultExt = ".csv",
                    FileName = Path.GetFileNameWithoutExtension(CsvPath) + "_daihon.csv"
                };

                if (saveDialog.ShowDialog() != true)
                    return;

                ExportAsDaihonCsv(saveDialog.FileName);

                StatusMessage = $"台本CSV出力完了: {Path.GetFileName(saveDialog.FileName)}";
                AppendLog($"Exported daihon CSV: {saveDialog.FileName}");
                WriteRuntimeLog($"Daihon CSV exported to: {saveDialog.FileName}");

                MessageBox.Show(
                    $"台本CSVを出力しました。{Environment.NewLine}{Environment.NewLine}" +
                    $"{saveDialog.FileName}{Environment.NewLine}{Environment.NewLine}" +
                    $"YMM4のメニュー → 台本 → 台本ファイルを開く で読み込んでください。",
                    "台本CSV出力完了", MessageBoxButton.OK, MessageBoxImage.Information);
            }
            catch (Exception ex)
            {
                StatusMessage = $"台本CSV出力エラー: {ex.Message}";
                AppendLog($"[ERROR] Daihon export: {ex}");
                WriteRuntimeLog($"Daihon export failed: {ex}");
                MessageBox.Show($"台本CSV出力に失敗しました:{Environment.NewLine}{ex.Message}", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private void ExportAsDaihonCsv(string outputPath)
        {
            using var writer = new StreamWriter(outputPath, false, System.Text.Encoding.UTF8);

            foreach (var item in PreviewItems)
            {
                if (string.IsNullOrWhiteSpace(item.Text))
                    continue;

                string speaker = item.Speaker ?? string.Empty;
                string serif = item.Text;

                // CSV escaping: if serif contains comma, quote, or newline, wrap in quotes
                if (serif.Contains(',') || serif.Contains('"') || serif.Contains('\n') || serif.Contains('\r'))
                {
                    serif = "\"" + serif.Replace("\"", "\"\"") + "\"";
                }
                if (speaker.Contains(',') || speaker.Contains('"'))
                {
                    speaker = "\"" + speaker.Replace("\"", "\"\"") + "\"";
                }

                writer.WriteLine($"{speaker},{serif}");
            }

            AppendLog($"Wrote {PreviewItems.Count(i => !string.IsNullOrWhiteSpace(i.Text))} lines to daihon CSV.");
        }

        private bool _voiceImporting;

        private async void VoiceImportButton_Click(object sender, RoutedEventArgs e)
        {
            if (_voiceImporting) return; // 二重実行防止

            if (PreviewItems.Count == 0)
            {
                StatusMessage = "先にプレビューを実行してください。";
                return;
            }

            try
            {
                _voiceImporting = true;
                VoiceImportButton.IsEnabled = false;
                SetBusy(true);
                StatusMessage = "VoiceItem一括インポート中...";
                ProgressValue = 0;
                AppendLog("Starting VoiceItem native import...");
                WriteRuntimeLog($"VoiceItem native import: {PreviewItems.Count} items.");

                await ImportWithVoiceItemNativeAsync();

                try { DialogResult = true; } catch { }
                Close();
            }
            catch (Exception ex)
            {
                StatusMessage = $"Import failed: {ex.Message}";
                AppendLog($"[FATAL] {ex}");
                WriteRuntimeLog($"VoiceItem import failed: {ex}");
                MessageBox.Show($"VoiceItemインポートに失敗しました:{Environment.NewLine}{ex.Message}", "Import Error", MessageBoxButton.OK, MessageBoxImage.Error);
            }
            finally
            {
                _voiceImporting = false;
                VoiceImportButton.IsEnabled = true;
                SetBusy(false);
            }
        }

        private async void ImportButton_Click(object sender, RoutedEventArgs e)
        {
            if (PreviewItems.Count == 0)
            {
                StatusMessage = "先にプレビューを実行してください。";
                return;
            }

            try
            {
                SetBusy(true);
                StatusMessage = "Importing to timeline...";
                ProgressValue = 0;
                AppendLog("Starting timeline import (AudioItem + ImageItem)...");
                WriteRuntimeLog($"Importing {PreviewItems.Count} items.");

                await ImportWithoutVoiceAsync();

                DialogResult = true;
                Close();
            }
            catch (Exception ex)
            {
                StatusMessage = $"Import failed: {ex.Message}";
                AppendLog($"[FATAL] {ex}");
                WriteRuntimeLog($"Import failed: {ex}");
                MessageBox.Show($"Import failed:{Environment.NewLine}{ex.Message}", "Import Error", MessageBoxButton.OK, MessageBoxImage.Error);
            }
            finally
            {
                SetBusy(false);
            }
        }

        /// <summary>
        /// VoiceItem + ImageItem インポート
        /// CharacterSettings からキャラクターを解決し、CreateVoiceItemAsync で
        /// YMM4ネイティブの音声合成パイプラインを通してVoiceItemを作成する。
        /// </summary>
        private async Task ImportWithVoiceItemNativeAsync()
        {
            if (!TryEnsureTimeline(out var activeTimeline, out var resolveError))
            {
                throw new InvalidOperationException($"Timeline not found: {resolveError}");
            }

            // Step 1: CharacterSettings からキャラクター一覧を取得
            var characters = ResolveCharactersFromSettings();
            if (characters.Count == 0)
            {
                throw new InvalidOperationException(
                    "YMM4にキャラクターが設定されていません。\n" +
                    "YMM4のキャラクター設定で、使用するキャラクターを追加してください。");
            }

            AppendLog($"Found {characters.Count} characters in YMM4 settings:");
            foreach (var kv in characters)
            {
                AppendLog($"  - {kv.Key}");
                WriteRuntimeLog($"  Character: '{kv.Key}'");
            }

            WriteRuntimeLog($"ImportWithVoiceItemNative: {characters.Count} characters, {PreviewItems.Count} items");

            var capturedItems = PreviewItems.ToList();
            int fps = Math.Max(1, activeTimeline.VideoInfo.FPS);
            int baseLayer = GetImportBaseLayer(activeTimeline);

            int importedRows = 0;
            int voiceItemsCount = 0;
            int imageItemsCount = 0;
            int crossfadeFrames = Math.Max(1, (int)Math.Round(0.5 * fps)); // 0.5秒クロスフェード
            int skippedRows = 0;

            int nextFrame = 0; // 音声長ベースで次のアイテム開始位置を累積

            for (int i = 0; i < capturedItems.Count; i++)
            {
                var item = capturedItems[i];
                ProgressValue = (int)(i * 100.0 / capturedItems.Count);
                StatusMessage = $"Processing {i + 1}/{capturedItems.Count}: {item.Speaker}...";

                int frame = nextFrame;
                int currentItemLength = Math.Max(1, (int)Math.Round((item.Duration ?? 3.0) * fps)); // デフォルト長
                bool hasItemInRow = false;

                // VoiceItem: テキストがある行にVoiceItemを作成
                if (!string.IsNullOrWhiteSpace(item.Text))
                {
                    string speakerName = item.Speaker ?? string.Empty;
                    object? character = null;

                    // キャラクター名でマッチ（完全一致 → 部分一致 → 読み仮名 → フォールバック）
                    if (!string.IsNullOrEmpty(speakerName))
                    {
                        if (characters.ContainsKey(speakerName))
                        {
                            character = characters[speakerName];
                        }
                        else
                        {
                            // 部分一致: CSVの話者名がキャラクター名に含まれるか、またはその逆
                            var match = characters.FirstOrDefault(kv =>
                                kv.Key.Contains(speakerName, StringComparison.OrdinalIgnoreCase) ||
                                speakerName.Contains(kv.Key, StringComparison.OrdinalIgnoreCase));
                            if (match.Value != null)
                            {
                                character = match.Value;
                                AppendLog($"  Partial match: '{speakerName}' → '{match.Key}'");
                            }
                            else
                            {
                                // 読み仮名マッチング: キャラクターオブジェクトの Kana/Reading プロパティを探す
                                character = TryMatchByReading(speakerName, characters);
                                if (character != null)
                                    AppendLog($"  Reading match: '{speakerName}'");
                            }
                        }
                    }

                    if (character == null && characters.Count > 0)
                    {
                        // フォールバック: 最初のキャラクターを使用
                        character = characters.Values.First();
                        AppendLog($"  Warning: Character '{speakerName}' not found, using '{characters.Keys.First()}'");
                    }

                    if (character != null)
                    {
                        try
                        {
                            var voiceItem = await CreateVoiceItemViaReflectionAsync(character, item.Text, fps);
                            if (voiceItem != null)
                            {
                                voiceItem.Frame = frame;
                                voiceItem.Layer = baseLayer;

                                // VoiceLength から Length を確定
                                if (voiceItem.Length > 0)
                                {
                                    currentItemLength = voiceItem.Length;
                                }
                                else
                                {
                                    voiceItem.Length = currentItemLength;
                                }

                                // UIスレッドでタイムラインに追加
                                var dispatcher = Application.Current?.Dispatcher;
                                if (dispatcher != null)
                                {
                                    dispatcher.Invoke(() =>
                                    {
                                        var itemsProp = activeTimeline.GetType().GetProperty("Items");
                                        bool hasSetter = itemsProp?.SetMethod != null;
                                        if (hasSetter)
                                            itemsProp!.SetValue(activeTimeline, activeTimeline.Items.Add(voiceItem));
                                        else
                                            activeTimeline.Items.Add(voiceItem);
                                    });
                                }

                                voiceItemsCount++;
                                hasItemInRow = true;
                                WriteRuntimeLog($"  VoiceItem: speaker={speakerName}, length={voiceItem.Length}, frame={frame}");
                            }
                        }
                        catch (Exception ex)
                        {
                            AppendLog($"  Error creating VoiceItem for '{speakerName}': {ex.Message}");
                            WriteRuntimeLog($"  VoiceItem ERROR: {ex}");
                        }
                    }
                }

                // ImageItem（クロスフェード付き、交互レイヤー配置）
                if (!string.IsNullOrEmpty(item.ImageFilePath) && File.Exists(item.ImageFilePath))
                {
                    // クロスフェード: 前のスライドと重なるように延長
                    int imageStart = Math.Max(0, frame - crossfadeFrames);
                    int imageEnd = frame + currentItemLength + crossfadeFrames;
                    int length = imageEnd - imageStart;
                    // 交互レイヤー（偶数=+1, 奇数=+2）で重なりを許可
                    int imageLayer = baseLayer + 1 + (imageItemsCount % 2);

                    var imageItem = new ImageItem(item.ImageFilePath)
                    {
                        Frame = imageStart,
                        Layer = imageLayer,
                        Length = length,
                        PlaybackRate = 100.0,
                        FadeIn = crossfadeFrames,
                        FadeOut = crossfadeFrames,
                    };

                    double fitZoom = CalculateFitZoom(item.ImageFilePath, activeTimeline.VideoInfo.Width, activeTimeline.VideoInfo.Height);
                    // SP-033: アニメーション種別対応
                    ApplyAnimationByType(imageItem, item.AnimationType, fitZoom, activeTimeline.VideoInfo.Width, activeTimeline.VideoInfo.Height);

                    var dispatcher = Application.Current?.Dispatcher;
                    if (dispatcher != null)
                    {
                        dispatcher.Invoke(() =>
                        {
                            var itemsProp = activeTimeline.GetType().GetProperty("Items");
                            bool hasSetter = itemsProp?.SetMethod != null;
                            if (hasSetter)
                                itemsProp!.SetValue(activeTimeline, activeTimeline.Items.Add(imageItem));
                            else
                                activeTimeline.Items.Add(imageItem);
                        });
                    }

                    imageItemsCount++;
                    hasItemInRow = true;
                }

                // 次のアイテムの開始位置を音声長+パディングに基づいて設定
                int paddingFrames = Math.Max(0, (int)Math.Round(0.3 * fps));
                nextFrame = frame + currentItemLength + paddingFrames;

                if (hasItemInRow) importedRows++;
                else skippedRows++;
            }

            // BGM配置
            bool bgmAdded = false;
            if (!string.IsNullOrEmpty(BgmPath) && File.Exists(BgmPath) && nextFrame > 0)
            {
                try
                {
                    int bgmLength = nextFrame; // タイムライン全体をカバー
                    int fadeFrames = Math.Min(fps * 2, bgmLength / 4); // 2秒フェード（最大長の1/4）

                    var bgmItem = new AudioItem(BgmPath)
                    {
                        Frame = 0,
                        Layer = 0, // 最下層
                        Length = bgmLength,
                        PlaybackRate = 1.0
                    };

                    // 音量設定 (リフレクションで Volume プロパティを探す)
                    double volumeRatio = BgmVolume / 100.0;
                    ApplyBgmVolume(bgmItem, volumeRatio);
                    ApplyBgmFade(bgmItem, fadeFrames);

                    var dispatcher = Application.Current?.Dispatcher;
                    dispatcher?.Invoke(() =>
                    {
                        var itemsProp = activeTimeline.GetType().GetProperty("Items");
                        bool hasSetter = itemsProp?.SetMethod != null;
                        if (hasSetter)
                            itemsProp!.SetValue(activeTimeline, activeTimeline.Items.Add(bgmItem));
                        else
                            activeTimeline.Items.Add(bgmItem);
                    });

                    bgmAdded = true;
                    AppendLog($"BGM added: {Path.GetFileName(BgmPath)}, volume={BgmVolume:F0}%, length={bgmLength} frames");
                    WriteRuntimeLog($"BGM: path={BgmPath}, volume={volumeRatio:F2}, length={bgmLength}, fadeFrames={fadeFrames}");
                }
                catch (Exception ex)
                {
                    AppendLog($"BGM add failed: {ex.Message}");
                    WriteRuntimeLog($"BGM ERROR: {ex}");
                }
            }

            // RefreshTimelineLengthAndMaxLayer on UI thread
            Application.Current?.Dispatcher?.Invoke(() =>
            {
                activeTimeline.RefreshTimelineLengthAndMaxLayer();
            });

            ProgressValue = 100;
            string bgmStatus = bgmAdded ? ", BGM: 1件" : "";
            StatusMessage = $"Imported {importedRows} items (Voice: {voiceItemsCount}, Image: {imageItemsCount}{bgmStatus}).";
            AppendLog($"Import success: Rows={importedRows}, Voice={voiceItemsCount}, Image={imageItemsCount}, BGM={bgmAdded}, Skipped={skippedRows}");
            WriteRuntimeLog($"ImportWithVoiceItemNative done: voice={voiceItemsCount}, image={imageItemsCount}, bgm={bgmAdded}, skipped={skippedRows}");

            MessageBox.Show(
                $"インポート完了{Environment.NewLine}{Environment.NewLine}" +
                $"VoiceItem: {voiceItemsCount}件, ImageItem: {imageItemsCount}件{bgmStatus}{Environment.NewLine}" +
                $"スキップ: {skippedRows}件",
                "CSV Import Success", MessageBoxButton.OK, MessageBoxImage.Information);
        }

        /// <summary>
        /// CharacterSettings からキャラクター名 → Character オブジェクトの辞書を取得
        /// </summary>
        private Dictionary<string, object> ResolveCharactersFromSettings()
        {
            var result = new Dictionary<string, object>();

            try
            {
                // YukkuriMovieMaker.Settings.CharacterSettings を探す
                Type? settingsType = null;
                foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies())
                {
                    try
                    {
                        settingsType = assembly.GetType("YukkuriMovieMaker.Settings.CharacterSettings");
                        if (settingsType != null) break;
                    }
                    catch { }
                }

                if (settingsType == null)
                {
                    WriteRuntimeLog("CharacterSettings type not found");
                    return result;
                }

                // シングルトン or static プロパティを探す
                object? settingsInstance = null;

                // パターン1: Default / Instance static property
                foreach (var propName in new[] { "Default", "Instance", "Current", "Settings" })
                {
                    var prop = settingsType.GetProperty(propName, BindingFlags.Public | BindingFlags.Static);
                    if (prop != null)
                    {
                        settingsInstance = prop.GetValue(null);
                        if (settingsInstance != null)
                        {
                            WriteRuntimeLog($"CharacterSettings found via {propName}");
                            break;
                        }
                    }
                }

                // パターン2: SettingsBase パターン
                if (settingsInstance == null)
                {
                    // Settings型を探す (ApplicationSettingsBase パターン)
                    var allProps = settingsType.GetProperties(BindingFlags.Public | BindingFlags.Static | BindingFlags.FlattenHierarchy);
                    foreach (var prop in allProps)
                    {
                        if (settingsType.IsAssignableFrom(prop.PropertyType))
                        {
                            settingsInstance = prop.GetValue(null);
                            if (settingsInstance != null)
                            {
                                WriteRuntimeLog($"CharacterSettings found via static prop {prop.Name}");
                                break;
                            }
                        }
                    }
                }

                if (settingsInstance == null)
                {
                    WriteRuntimeLog("CharacterSettings instance not found. Dumping static props:");
                    var allProps = settingsType.GetProperties(BindingFlags.Public | BindingFlags.Static | BindingFlags.FlattenHierarchy);
                    foreach (var p in allProps)
                        WriteRuntimeLog($"  {p.Name}: {p.PropertyType.Name}");
                    return result;
                }

                // Characters プロパティを取得
                var charactersProp = settingsInstance.GetType().GetProperty("Characters",
                    BindingFlags.Public | BindingFlags.Instance);
                if (charactersProp == null)
                {
                    WriteRuntimeLog("Characters property not found on CharacterSettings");
                    return result;
                }

                var characters = charactersProp.GetValue(settingsInstance);
                if (characters is System.Collections.IEnumerable enumerable)
                {
                    foreach (var character in enumerable)
                    {
                        var nameProp = character.GetType().GetProperty("Name");
                        if (nameProp != null)
                        {
                            var name = nameProp.GetValue(character) as string;
                            if (!string.IsNullOrEmpty(name) && !result.ContainsKey(name))
                            {
                                result[name] = character;
                            }
                        }
                    }
                }

                WriteRuntimeLog($"Resolved {result.Count} characters from settings");
            }
            catch (Exception ex)
            {
                WriteRuntimeLog($"ResolveCharactersFromSettings error: {ex}");
            }

            return result;
        }

        /// <summary>
        /// リフレクションで VoiceItem.CreateVoiceItemAsync(Character, string, ...) を呼び出す
        /// </summary>
        private async Task<VoiceItem?> CreateVoiceItemViaReflectionAsync(object character, string serif, int fps = 30)
        {
            // VoiceItem の静的メソッド CreateVoiceItemAsync を探す
            var voiceItemType = typeof(VoiceItem);

            var createMethod = voiceItemType.GetMethod("CreateVoiceItemAsync",
                BindingFlags.Public | BindingFlags.Static);

            if (createMethod == null)
            {
                // インスタンスメソッドの可能性も探す
                createMethod = voiceItemType.GetMethod("CreateVoiceItemAsync",
                    BindingFlags.Public | BindingFlags.Instance);
            }

            if (createMethod != null)
            {
                WriteRuntimeLog($"CreateVoiceItemAsync found: {createMethod.ReturnType.Name}, params={string.Join(", ", createMethod.GetParameters().Select(p => $"{p.ParameterType.Name} {p.Name}"))}");

                var parameters = createMethod.GetParameters();
                var args = new object?[parameters.Length];

                for (int i = 0; i < parameters.Length; i++)
                {
                    var param = parameters[i];
                    if (param.ParameterType.Name.Contains("Character") || param.Name == "character")
                        args[i] = character;
                    else if (param.ParameterType == typeof(string) && (param.Name == "serif" || param.Name == "text"))
                        args[i] = serif;
                    else if (param.ParameterType == typeof(string) && param.Name == "hatsuon")
                        args[i] = string.Empty; // 自動生成させる
                    else if (param.HasDefaultValue)
                        args[i] = param.DefaultValue;
                    else
                        args[i] = null;
                }

                try
                {
                    object? resultObj;
                    if (createMethod.IsStatic)
                        resultObj = createMethod.Invoke(null, args);
                    else
                        resultObj = createMethod.Invoke(Activator.CreateInstance(voiceItemType), args);

                    // Task<VoiceItem> を await
                    if (resultObj is Task task)
                    {
                        await task;
                        // Task<T>.Result を取得
                        var resultProp = task.GetType().GetProperty("Result");
                        var voiceItem = resultProp?.GetValue(task) as VoiceItem;

                        if (voiceItem != null)
                        {
                            // CreateVoiceItemAsync 後に音声合成パイプラインを実行
                            await RunVoiceSynthesisPipelineAsync(voiceItem, fps);

                            // キャラクター固有の字幕・ボイスパラメータを適用
                            TryInvokeSyncMethod(voiceItem, "ResetVoiceParameter");
                            TryInvokeSyncMethod(voiceItem, "ResetJimakuParameter");
                        }

                        return voiceItem;
                    }
                }
                catch (Exception ex)
                {
                    WriteRuntimeLog($"CreateVoiceItemAsync invocation failed: {ex}");
                    // フォールバック: 手動でVoiceItem作成
                    AppendLog($"  Falling back to manual VoiceItem creation: {ex.Message}");
                }
            }
            else
            {
                WriteRuntimeLog("CreateVoiceItemAsync method not found on VoiceItem");
            }

            // フォールバック: 手動でVoiceItem作成してSerifToHatsuonAsyncを呼ぶ
            return await CreateVoiceItemManualAsync(character, serif, fps);
        }

        /// <summary>
        /// VoiceItem に対して音声合成パイプラインを実行
        /// SerifToHatsuonAsync → CreateVoiceCacheAsync → LoadVoiceLength
        /// </summary>
        private async Task RunVoiceSynthesisPipelineAsync(VoiceItem voiceItem, int fps = 30)
        {
            var voiceItemType = typeof(VoiceItem);

            // VoiceItem の全メソッドを一度ダンプ（初回のみ: static flag で制御）
            if (!_voiceMethodsDumped)
            {
                _voiceMethodsDumped = true;
                var allMethods = voiceItemType.GetMethods(BindingFlags.Public | BindingFlags.Instance);
                WriteRuntimeLog($"  VoiceItem has {allMethods.Length} public methods. Voice-related:");
                foreach (var m in allMethods)
                {
                    if (m.Name.Contains("Voice") || m.Name.Contains("Hatsuon") || m.Name.Contains("Serif")
                        || m.Name.Contains("Cache") || m.Name.Contains("Length") || m.Name.Contains("LipSync")
                        || m.Name.Contains("Pronounce") || m.Name.Contains("Create"))
                    {
                        WriteRuntimeLog($"    {m.Name}({string.Join(", ", m.GetParameters().Select(p => p.ParameterType.Name))}) -> {m.ReturnType.Name}");
                    }
                }
            }

            // 1. SerifToHatsuonAsync — テキストから発音データを生成
            await TryInvokeAsyncMethod(voiceItem, "SerifToHatsuonAsync");
            WriteRuntimeLog($"  Hatsuon after: {voiceItem.Hatsuon?.Substring(0, Math.Min(40, voiceItem.Hatsuon?.Length ?? 0))}");

            // 2. 音声キャッシュ生成 — 名前のバリエーションを試す
            bool cacheCreated = false;
            foreach (var methodName in new[] { "CreateVoiceCacheAsync", "CreateVoiceAsync", "UpdateVoiceAsync", "CreateVoiceFileAsync" })
            {
                if (await TryInvokeAsyncMethod(voiceItem, methodName))
                {
                    cacheCreated = true;
                    break;
                }
            }
            if (!cacheCreated)
                WriteRuntimeLog("  WARNING: No voice cache/file creation method succeeded");

            // 3. VoiceLengthプロパティから音声長をフレーム数に変換してLengthに設定
            try
            {
                var voiceLengthProp = voiceItemType.GetProperty("VoiceLength",
                    BindingFlags.Public | BindingFlags.Instance);
                if (voiceLengthProp != null)
                {
                    var voiceLength = voiceLengthProp.GetValue(voiceItem);
                    if (voiceLength is TimeSpan ts && ts.TotalSeconds > 0)
                    {
                        int newLength = Math.Max(1, (int)Math.Round(ts.TotalSeconds * fps));
                        voiceItem.Length = newLength;
                        WriteRuntimeLog($"  VoiceLength={ts.TotalSeconds:F3}s → Length={newLength} frames (fps={fps})");
                    }
                    else
                    {
                        WriteRuntimeLog($"  VoiceLength={voiceLength} (not valid TimeSpan or zero)");
                    }
                }
                else
                {
                    WriteRuntimeLog("  VoiceLength property NOT FOUND");
                }
            }
            catch (Exception ex)
            {
                WriteRuntimeLog($"  VoiceLength access failed: {ex.Message}");
            }

            // 4. リップシンク（オプション）
            await TryInvokeAsyncMethod(voiceItem, "LoadLipSyncAsync");

            // 診断ログ
            WriteRuntimeLog($"  Pipeline complete: Serif={voiceItem.Serif?.Substring(0, Math.Min(20, voiceItem.Serif?.Length ?? 0))}, " +
                           $"CharacterName={voiceItem.CharacterName}, Length={voiceItem.Length}");
        }

        private async Task<bool> TryInvokeAsyncMethod(object target, string methodName)
        {
            var method = target.GetType().GetMethod(methodName,
                BindingFlags.Public | BindingFlags.Instance);
            if (method == null)
            {
                WriteRuntimeLog($"  {methodName}: NOT FOUND");
                return false;
            }

            try
            {
                var parameters = method.GetParameters();
                var args = new object?[parameters.Length];
                for (int i = 0; i < parameters.Length; i++)
                {
                    if (parameters[i].HasDefaultValue)
                        args[i] = parameters[i].DefaultValue;
                    else
                        args[i] = null;
                }

                var result = method.Invoke(target, args.Length > 0 ? args : null);
                if (result is Task task)
                    await task;

                WriteRuntimeLog($"  {methodName}: OK");
                return true;
            }
            catch (Exception ex)
            {
                WriteRuntimeLog($"  {methodName}: FAILED - {ex.InnerException?.Message ?? ex.Message}");
                return false;
            }
        }

        private bool TryInvokeSyncMethod(object target, string methodName)
        {
            var method = target.GetType().GetMethod(methodName,
                BindingFlags.Public | BindingFlags.Instance);
            if (method == null)
            {
                WriteRuntimeLog($"  {methodName}: NOT FOUND");
                return false;
            }

            try
            {
                method.Invoke(target, null);
                WriteRuntimeLog($"  {methodName}: OK");
                return true;
            }
            catch (Exception ex)
            {
                WriteRuntimeLog($"  {methodName}: FAILED - {ex.InnerException?.Message ?? ex.Message}");
                return false;
            }
        }

        /// <summary>
        /// フォールバック: VoiceItemを手動構築し、SerifToHatsuonAsync で発音生成
        /// </summary>
        private async Task<VoiceItem?> CreateVoiceItemManualAsync(object character, string serif, int fps = 30)
        {
            try
            {
                var voiceItem = new VoiceItem();
                voiceItem.Serif = serif;

                // Character プロパティをセット
                var charProp = typeof(VoiceItem).GetProperty("Character");
                if (charProp?.CanWrite == true)
                {
                    charProp.SetValue(voiceItem, character);
                }
                else
                {
                    // backing field にセット
                    var backingField = typeof(VoiceItem).GetField("<Character>k__BackingField",
                        BindingFlags.NonPublic | BindingFlags.Instance);
                    if (backingField != null)
                        backingField.SetValue(voiceItem, character);
                }

                // CharacterName をセット
                var nameProp = character.GetType().GetProperty("Name");
                if (nameProp != null)
                {
                    voiceItem.CharacterName = nameProp.GetValue(character) as string ?? string.Empty;
                }

                // ResetVoiceParameter() — キャラクターのボイス設定をVoiceItemに反映
                var resetVoice = typeof(VoiceItem).GetMethod("ResetVoiceParameter",
                    BindingFlags.Public | BindingFlags.Instance);
                resetVoice?.Invoke(voiceItem, null);

                // ResetJimakuParameter() — 字幕設定を反映
                var resetJimaku = typeof(VoiceItem).GetMethod("ResetJimakuParameter",
                    BindingFlags.Public | BindingFlags.Instance);
                resetJimaku?.Invoke(voiceItem, null);

                // SerifToHatsuonAsync() — 発音生成
                var serifToHatsuon = typeof(VoiceItem).GetMethod("SerifToHatsuonAsync",
                    BindingFlags.Public | BindingFlags.Instance);
                if (serifToHatsuon != null)
                {
                    var task = serifToHatsuon.Invoke(voiceItem, null);
                    if (task is Task t)
                        await t;
                    WriteRuntimeLog($"  SerifToHatsuonAsync completed for: {serif.Substring(0, Math.Min(20, serif.Length))}");
                }

                // CreateVoiceCacheAsync() — 音声キャッシュ生成
                var createCache = typeof(VoiceItem).GetMethod("CreateVoiceCacheAsync",
                    BindingFlags.Public | BindingFlags.Instance);
                if (createCache != null)
                {
                    var task = createCache.Invoke(voiceItem, null);
                    if (task is Task t)
                        await t;
                    WriteRuntimeLog($"  CreateVoiceCacheAsync completed");
                }

                // LoadVoiceLength() — 音声長を設定
                var loadLength = typeof(VoiceItem).GetMethod("LoadVoiceLength",
                    BindingFlags.Public | BindingFlags.Instance);
                loadLength?.Invoke(voiceItem, null);

                return voiceItem;
            }
            catch (Exception ex)
            {
                WriteRuntimeLog($"CreateVoiceItemManual failed: {ex}");
                AppendLog($"  Manual VoiceItem creation failed: {ex.Message}");
                return null;
            }
        }

        private async Task ImportWithoutVoiceAsync()
        {
            var progress = new Progress<int>(v => ProgressValue = v);
            var result = await ImportToTimelineAsync(PreviewItems, AddSubtitles, progress);

            ProgressValue = 100;
            StatusMessage = $"Imported {result.ImportedRows} items.";
            AppendLog($"Import success: Rows={result.ImportedRows}, Audio={result.AudioItems}, Text={result.TextItems}, Image={result.ImageItems}, TotalTimeline={result.TimelineItemsAfterImport}");

            MessageBox.Show(
                $"Import Complete!{Environment.NewLine}{Environment.NewLine}" +
                $"Successfully imported {result.ImportedRows} items (Image: {result.ImageItems}).",
                "CSV Import Success", MessageBoxButton.OK, MessageBoxImage.Information);
        }

        private void SetBusy(bool isBusy)
        {
            if (PreviewButton != null) PreviewButton.IsEnabled = !isBusy;
            if (ImportButton != null) ImportButton.IsEnabled = !isBusy;
            if (BrowseCsvButton != null) BrowseCsvButton.IsEnabled = !isBusy;
        }

        private async Task<ImportExecutionResult> ImportToTimelineAsync(List<CsvTimelineItem> items, bool addSubtitles, IProgress<int> progress)
        {
            // Capture dispatcher reference for null safety
            var dispatcher = Application.Current?.Dispatcher
                ?? throw new InvalidOperationException("Application dispatcher is not available.");
            return await Task.Run(() =>
            {
                return dispatcher.Invoke(() =>
                {
                    if (!TryEnsureTimeline(out var activeTimeline, out var resolveError))
                    {
                        throw new InvalidOperationException($"Timeline not found: {resolveError}");
                    }

                    int fps = Math.Max(1, activeTimeline.VideoInfo.FPS);
                    int baseLayer = GetImportBaseLayer(activeTimeline);
                    int count = 0;
                    int audioCount = 0;
                    int textCount = 0;
                    int imageCount = 0;
                    int itemsBefore = activeTimeline.Items.Count;

                    // SP-031: Pre-import quality validation
                    var validationWarnings = ValidateImportItems(items);
                    foreach (var w in validationWarnings)
                    {
                        WriteRuntimeLog($"[QA] {w}");
                    }

                    // Items is ImmutableList in v4.50+ — must reassign after each Add
                    var itemsProp = activeTimeline.GetType().GetProperty("Items");
                    bool itemsHasSetter = itemsProp?.SetMethod != null;

                    for (int i = 0; i < items.Count; i++)
                    {
                        var item = items[i];
                        int frame = (int)Math.Round(item.StartTime * fps);
                        int length = (int)Math.Round((item.Duration ?? 1.0) * fps);

                        // SP-028: Use actual WAV duration when available
                        if (!string.IsNullOrEmpty(item.AudioFilePath) && File.Exists(item.AudioFilePath))
                        {
                            double? wavDuration = GetWavDurationSeconds(item.AudioFilePath);
                            if (wavDuration.HasValue && wavDuration.Value > 0)
                            {
                                length = Math.Max(1, (int)Math.Round(wavDuration.Value * fps));
                            }
                        }

                        if (!string.IsNullOrEmpty(item.AudioFilePath) && File.Exists(item.AudioFilePath))
                        {
                            var audioItem = new AudioItem(item.AudioFilePath) { Frame = frame, Layer = baseLayer, Length = length };
                            if (itemsHasSetter)
                                itemsProp!.SetValue(activeTimeline, activeTimeline.Items.Add(audioItem));
                            else
                                activeTimeline.Items.Add(audioItem);
                            audioCount++;
                        }

                        if (!string.IsNullOrEmpty(item.ImageFilePath) && File.Exists(item.ImageFilePath))
                        {
                            var imageItem = new ImageItem(item.ImageFilePath) { Frame = frame, Layer = baseLayer + 1, Length = length, PlaybackRate = 100.0 };
                            double fitZoom = CalculateFitZoom(item.ImageFilePath, activeTimeline.VideoInfo.Width, activeTimeline.VideoInfo.Height);
                            // SP-033: アニメーション種別対応
                            ApplyAnimationByType(imageItem, item.AnimationType, fitZoom, activeTimeline.VideoInfo.Width, activeTimeline.VideoInfo.Height);
                            if (itemsHasSetter)
                                itemsProp!.SetValue(activeTimeline, activeTimeline.Items.Add(imageItem));
                            else
                                activeTimeline.Items.Add(imageItem);
                            imageCount++;
                        }

                        if (addSubtitles && !string.IsNullOrEmpty(item.Text))
                        {
                            var textItem = new TextItem { Text = item.Text, Frame = frame, Layer = baseLayer + 2, Length = length };
                            ApplySubtitleStyle(textItem, activeTimeline.VideoInfo.Height);
                            if (itemsHasSetter)
                                itemsProp!.SetValue(activeTimeline, activeTimeline.Items.Add(textItem));
                            else
                                activeTimeline.Items.Add(textItem);
                            textCount++;
                        }

                        count++;
                        progress.Report((int)(i * 100.0 / items.Count));
                    }

                    int itemsAfter = activeTimeline.Items.Count;
                    WriteRuntimeLog($"Import done: added={audioCount + textCount + imageCount}, itemsBefore={itemsBefore}, itemsAfter={itemsAfter}");

                    activeTimeline.RefreshTimelineLengthAndMaxLayer();
                    return new ImportExecutionResult(count, audioCount, textCount, imageCount, 0, 0, activeTimeline.Items.Count);
                });
            });
        }

        private ImportExecutionResult ImportToTimeline(IEnumerable<CsvTimelineItem> items, bool shouldAddSubtitles)
        {
            var dispatcher = Application.Current?.Dispatcher
                ?? throw new InvalidOperationException("Application dispatcher is not available.");
            return dispatcher.Invoke(() =>
            {
                if (!TryEnsureTimeline(out var activeTimeline, out var resolveError))
                {
                    throw new InvalidOperationException($"Timeline context is not available. {resolveError}");
                }

                // SP-031: Pre-import quality validation
                var validationWarnings = ValidateImportItems(items);
                foreach (var w in validationWarnings)
                {
                    WriteRuntimeLog($"[QA] {w}");
                }

                int fps = Math.Max(1, activeTimeline.VideoInfo.FPS);
                int baseLayer = GetImportBaseLayer(activeTimeline);

                int importedRows = 0;
                int audioItemsCount = 0;
                int textItemsCount = 0;
                int imageItemsCount = 0;
                int skippedRows = 0;

                var allTimelineItems = new List<IItem>();

                foreach (var csvItem in items)
                {
                    int startFrame = Math.Max(0, (int)Math.Round(csvItem.StartTime * fps));
                    int lengthFrames = Math.Max(1, (int)Math.Round((csvItem.Duration ?? 3.0) * fps));

                    // SP-028: Use actual WAV duration when available
                    if (!string.IsNullOrWhiteSpace(csvItem.AudioFilePath) && File.Exists(csvItem.AudioFilePath))
                    {
                        double? wavDuration = GetWavDurationSeconds(csvItem.AudioFilePath);
                        if (wavDuration.HasValue && wavDuration.Value > 0)
                        {
                            lengthFrames = Math.Max(1, (int)Math.Round(wavDuration.Value * fps));
                        }
                    }

                    bool hasItemInRow = false;
                    if (!string.IsNullOrWhiteSpace(csvItem.AudioFilePath) && File.Exists(csvItem.AudioFilePath))
                    {
                        var audio = new AudioItem(csvItem.AudioFilePath)
                        {
                            Frame = startFrame,
                            Layer = baseLayer,
                            Length = lengthFrames,
                            PlaybackRate = 1.0
                        };
                        allTimelineItems.Add(audio);
                        audioItemsCount++;
                        hasItemInRow = true;
                    }

                    if (!string.IsNullOrWhiteSpace(csvItem.ImageFilePath) && File.Exists(csvItem.ImageFilePath))
                    {
                        var image = new ImageItem(csvItem.ImageFilePath)
                        {
                            Frame = startFrame,
                            Layer = baseLayer + 1,
                            Length = lengthFrames,
                        };
                        double fitZoom = CalculateFitZoom(csvItem.ImageFilePath, activeTimeline.VideoInfo.Width, activeTimeline.VideoInfo.Height);
                        // SP-033: アニメーション種別対応
                        ApplyAnimationByType(image, csvItem.AnimationType, fitZoom, activeTimeline.VideoInfo.Width, activeTimeline.VideoInfo.Height);
                        allTimelineItems.Add(image);
                        imageItemsCount++;
                        hasItemInRow = true;
                    }

                    if (shouldAddSubtitles && !string.IsNullOrWhiteSpace(csvItem.Text))
                    {
                        var text = new TextItem
                        {
                            Frame = startFrame,
                            Layer = baseLayer + 2,
                            Length = lengthFrames,
                            PlaybackRate = 1.0,
                            Text = csvItem.Text
                        };
                        ApplySubtitleStyle(text, activeTimeline.VideoInfo.Height);
                        allTimelineItems.Add(text);
                        textItemsCount++;
                        hasItemInRow = true;
                    }

                    if (hasItemInRow)
                    {
                        importedRows++;
                    }
                    else
                    {
                        skippedRows++;
                    }
                }

                if (allTimelineItems.Count > 0)
                {
                    // Items is ImmutableList in v4.50+ — must reassign after each Add
                    var itemsProp = activeTimeline.GetType().GetProperty("Items");
                    bool useSetter = itemsProp?.SetMethod != null;

                    foreach (var item in allTimelineItems)
                    {
                        if (useSetter)
                            itemsProp!.SetValue(activeTimeline, activeTimeline.Items.Add(item));
                        else
                            activeTimeline.Items.Add(item);
                    }
                    activeTimeline.RefreshTimelineLengthAndMaxLayer();
                }

                return new ImportExecutionResult(importedRows, audioItemsCount, textItemsCount, imageItemsCount, 0, skippedRows, activeTimeline.Items.Count);
            });
        }

        private bool TryEnsureTimeline(out Timeline activeTimeline, out string detail)
        {
            if (timeline is not null)
            {
                activeTimeline = timeline;
                detail = "source=viewmodel-injection";
                WriteRuntimeLog($"Timeline resolved via injection.");
                return true;
            }

            if (TryResolveTimelineFromMainWindow(out activeTimeline, out detail))
            {
                timeline = activeTimeline;
                WriteRuntimeLog($"Timeline resolved via reflection. detail={detail}");
                return true;
            }

            WriteRuntimeLog($"Timeline resolution failed. detail={detail}");
            activeTimeline = null!;
            return false;
        }

        private static bool TryResolveTimelineFromMainWindow(out Timeline timeline, out string detail)
        {
            timeline = null!;
            detail = string.Empty;

            var mainWindow = Application.Current?.MainWindow;
            if (mainWindow?.DataContext is null)
            {
                detail = "main-window-datacontext-missing";
                return false;
            }

            var mainViewModel = mainWindow.DataContext!;

            // Strategy 1: MainViewModel.Timeline (some versions)
            var directTimeline = GetPropertyValue(mainViewModel, "Timeline") as Timeline;
            if (directTimeline is not null)
            {
                timeline = directTimeline;
                detail = "source=main-viewmodel-direct";
                return true;
            }

            // Strategy 2: MainViewModel.ActiveTimelineViewModel.Timeline (v4.50+)
            var activeTimelineVm = GetPropertyValue(mainViewModel, "ActiveTimelineViewModel");
            if (activeTimelineVm is not null)
            {
                var tlFromActive = GetPropertyValue(activeTimelineVm, "Timeline") as Timeline
                                ?? GetFieldValue(activeTimelineVm, "timeline") as Timeline;
                if (tlFromActive is not null)
                {
                    timeline = tlFromActive;
                    detail = "source=active-timeline-viewmodel";
                    return true;
                }
                WriteRuntimeLog($"ActiveTimelineViewModel found but Timeline is null. Type={activeTimelineVm.GetType().FullName}");
            }

            // Strategy 3: MainViewModel.TimelineAreaViewModel.ViewModel.Value.Timeline (v4.43)
            var timelineAreaViewModel = GetPropertyValue(mainViewModel, "TimelineAreaViewModel");
            if (timelineAreaViewModel is not null)
            {
                var reactiveViewModel = GetPropertyValue(timelineAreaViewModel, "ViewModel");
                var timelineViewModel = reactiveViewModel is not null ? GetPropertyValue(reactiveViewModel, "Value") : null;
                var tlFromArea =
                    timelineViewModel is not null
                        ? GetPropertyValue(timelineViewModel, "Timeline") as Timeline
                          ?? GetFieldValue(timelineViewModel, "timeline") as Timeline
                        : null;
                if (tlFromArea is not null)
                {
                    timeline = tlFromArea;
                    detail = "source=timeline-area-viewmodel-legacy";
                    return true;
                }
            }

            detail = "timeline-not-resolved";
            return false;
        }

        private static object? GetPropertyValue(object instance, string propertyName)
        {
            var property = instance.GetType().GetProperty(
                propertyName,
                BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic);
            return property?.GetValue(instance);
        }

        private static object? GetFieldValue(object instance, string fieldName)
        {
            var field = instance.GetType().GetField(
                fieldName,
                BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic);
            return field?.GetValue(instance);
        }

        private static void WriteRuntimeLog(string message)
        {
            try
            {
                var dir = Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                    "NLMSlidePlugin",
                    "logs");
                Directory.CreateDirectory(dir);
                var path = Path.Combine(dir, "csv_import_runtime.log");
                var line = $"{DateTime.Now:yyyy-MM-dd HH:mm:ss.fff} {message}{Environment.NewLine}";
                File.AppendAllText(path, line);
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[NLMSlidePlugin] WriteRuntimeLog failed: {ex.Message}");
            }
        }

        /// <summary>
        /// キャラクターオブジェクトの読み仮名プロパティや名前正規化でマッチングを試みる
        /// </summary>
        private static object? TryMatchByReading(string speakerName, Dictionary<string, object> characters)
        {
            string speakerNorm = NormalizeCharacterName(speakerName);

            foreach (var kv in characters)
            {
                // YMM4キャラクター名を正規化して比較（"ゆっくり霊夢"→"霊夢"、"ゆっくり魔理沙"→"魔理沙"）
                string charNorm = NormalizeCharacterName(kv.Key);
                if (string.Equals(speakerNorm, charNorm, StringComparison.OrdinalIgnoreCase))
                {
                    WriteRuntimeLog($"  Normalized match: '{speakerName}'→'{speakerNorm}' == '{kv.Key}'→'{charNorm}'");
                    return kv.Value;
                }

                // キャラクターオブジェクトの Kana / NameKana / Reading プロパティを探す
                try
                {
                    foreach (var propName in new[] { "Kana", "NameKana", "Reading", "Yomigana" })
                    {
                        var prop = kv.Value.GetType().GetProperty(propName,
                            BindingFlags.Public | BindingFlags.Instance);
                        if (prop != null)
                        {
                            var reading = prop.GetValue(kv.Value) as string;
                            if (!string.IsNullOrEmpty(reading))
                            {
                                string readingNorm = NormalizeCharacterName(reading);
                                if (reading.Contains(speakerName, StringComparison.OrdinalIgnoreCase) ||
                                    speakerName.Contains(reading, StringComparison.OrdinalIgnoreCase) ||
                                    string.Equals(speakerNorm, readingNorm, StringComparison.OrdinalIgnoreCase))
                                {
                                    WriteRuntimeLog($"  Reading property match: '{speakerName}' via {propName}='{reading}' on '{kv.Key}'");
                                    return kv.Value;
                                }
                            }
                        }
                    }
                }
                catch { }
            }

            return null;
        }

        /// <summary>
        /// キャラクター名を正規化: よくある接頭辞を除去
        /// </summary>
        private static string NormalizeCharacterName(string name)
        {
            // よくある接頭辞を除去
            foreach (var prefix in new[] { "ゆっくり", "softalk_", "voicevox_", "coeiroink_", "VOICEVOX_" })
            {
                if (name.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
                {
                    name = name.Substring(prefix.Length);
                    break;
                }
            }
            return name.Trim();
        }

        /// <summary>
        /// Calculate zoom percentage to fit image to video dimensions (contain mode).
        /// Returns 100.0 if image size cannot be determined.
        /// </summary>
        internal static double CalculateFitZoom(string imagePath, int videoWidth, int videoHeight)
        {
            try
            {
                var uri = new Uri(imagePath, UriKind.Absolute);
                var decoder = System.Windows.Media.Imaging.BitmapDecoder.Create(
                    uri,
                    System.Windows.Media.Imaging.BitmapCreateOptions.DelayCreation,
                    System.Windows.Media.Imaging.BitmapCacheOption.None);
                var frame = decoder.Frames[0];
                int imgW = frame.PixelWidth;
                int imgH = frame.PixelHeight;
                if (imgW <= 0 || imgH <= 0) return 100.0;

                double scaleX = (double)videoWidth / imgW;
                double scaleY = (double)videoHeight / imgH;
                double scale = Math.Min(scaleX, scaleY);
                return scale * 100.0;
            }
            catch (Exception ex)
            {
                WriteRuntimeLog($"CalculateFitZoom failed for {imagePath}: {ex.Message}");
                return 100.0;
            }
        }

        /// <summary>
        /// Apply subtitle styling to a TextItem via Reflection (SP-030).
        /// Sets Y position to bottom area, font size, and text color.
        /// </summary>
        internal static void ApplySubtitleStyle(TextItem textItem, int videoHeight, int fontSize = 48)
        {
            try
            {
                bool ySet = false;
                bool fontSet = false;

                // Position subtitle at bottom area of screen
                // Y is an AnimationValue — use the same pattern as Zoom/Opacity
                var yProp = textItem.GetType().GetProperty("Y");
                if (yProp != null)
                {
                    var yObj = yProp.GetValue(textItem);
                    if (yObj != null)
                    {
                        var valuesProp = yObj.GetType().GetProperty("Values");
                        if (valuesProp != null)
                        {
                            var values = valuesProp.GetValue(yObj);
                            if (values != null)
                            {
                                var indexer = values.GetType().GetProperty("Item");
                                if (indexer != null)
                                {
                                    var firstValue = indexer.GetValue(values, new object[] { 0 });
                                    var valueProp = firstValue?.GetType().GetProperty("Value");
                                    if (valueProp != null && valueProp.CanWrite)
                                    {
                                        double yPos = videoHeight * 0.35;
                                        valueProp.SetValue(firstValue, yPos);
                                        ySet = true;
                                    }
                                }
                            }
                        }
                    }
                }

                // FontSize — try multiple approaches since it may be read-only
                var fontSizeProp = textItem.GetType().GetProperty("FontSize");
                if (fontSizeProp != null)
                {
                    if (fontSizeProp.CanWrite)
                    {
                        // Direct setter available
                        fontSizeProp.SetValue(textItem, fontSize);
                        fontSet = true;
                    }
                    else
                    {
                        // FontSize is read-only — try setting via backing field
                        var backingField = textItem.GetType().GetField("<FontSize>k__BackingField",
                            BindingFlags.NonPublic | BindingFlags.Instance);
                        if (backingField != null)
                        {
                            backingField.SetValue(textItem, fontSize);
                            fontSet = true;
                        }
                        else
                        {
                            // Try common field naming patterns
                            foreach (var fieldName in new[] { "_fontSize", "fontSize", "m_fontSize" })
                            {
                                var field = textItem.GetType().GetField(fieldName,
                                    BindingFlags.NonPublic | BindingFlags.Instance);
                                if (field != null)
                                {
                                    field.SetValue(textItem, fontSize);
                                    fontSet = true;
                                    break;
                                }
                            }
                        }
                    }
                }

                WriteRuntimeLog($"ApplySubtitleStyle: Y={ySet}, fontSize={fontSet} (videoHeight={videoHeight})");
            }
            catch (Exception ex)
            {
                WriteRuntimeLog($"ApplySubtitleStyle failed: {ex.Message}");
            }
        }

        /// <summary>
        /// Apply fade-in effect to an ImageItem via Reflection (SP-030).
        /// Sets Opacity animation from 0% to 100% over fadeFrames.
        /// </summary>
        internal static void ApplyImageFade(ImageItem imageItem, int fadeFrames = 10)
        {
            try
            {
                var opacityProp = imageItem.GetType().GetProperty("Opacity");
                if (opacityProp is null) return;
                var opacityObj = opacityProp.GetValue(imageItem);
                if (opacityObj is null) return;

                // Set AnimationType to "直線" (linear)
                var animTypeProp = opacityObj.GetType().GetProperty("AnimationType");
                if (animTypeProp != null)
                {
                    var enumType = animTypeProp.PropertyType;
                    var enumValues = Enum.GetValues(enumType);
                    foreach (var ev in enumValues)
                    {
                        if (ev.ToString() == "直線")
                        {
                            animTypeProp.SetValue(opacityObj, ev);
                            break;
                        }
                    }
                }

                // Set Values[0] = 0 (start transparent), Values[1] = 100 (end opaque)
                var valuesProp = opacityObj.GetType().GetProperty("Values");
                if (valuesProp is null) return;
                var values = valuesProp.GetValue(opacityObj);
                if (values is null) return;

                var indexer = values.GetType().GetProperty("Item");
                if (indexer is null) return;
                var firstValue = indexer.GetValue(values, new object[] { 0 });
                var valueProp = firstValue?.GetType().GetProperty("Value");
                valueProp?.SetValue(firstValue, 0.0); // start at 0% opacity

                // Add second keyframe at 100%
                var countProp = values.GetType().GetProperty("Count");
                int count = (int)(countProp?.GetValue(values) ?? 0);
                if (count < 2)
                {
                    var firstValueType = firstValue?.GetType();
                    if (firstValueType != null)
                    {
                        var newValue = Activator.CreateInstance(firstValueType);
                        var newValueProp = firstValueType.GetProperty("Value");
                        newValueProp?.SetValue(newValue, 100.0);
                        var addMethod = values.GetType().GetMethod("Add");
                        addMethod?.Invoke(values, new[] { newValue });
                    }
                }
                else
                {
                    var secondValue = indexer.GetValue(values, new object[] { 1 });
                    var secondValueProp = secondValue?.GetType().GetProperty("Value");
                    secondValueProp?.SetValue(secondValue, 100.0);
                }

                WriteRuntimeLog($"ApplyImageFade: 0% → 100% over {fadeFrames} frames");
            }
            catch (Exception ex)
            {
                WriteRuntimeLog($"ApplyImageFade failed: {ex.Message}");
            }
        }

        /// <summary>
        /// ImageItem にクロスフェード（フェードイン+フェードアウト）を適用
        /// Opacity: 0% → 100% → ... → 100% → 0% のエンベロープ
        /// </summary>
        internal static void ApplyImageCrossfade(ImageItem imageItem, int fadeFrames = 15)
        {
            try
            {
                var opacityProp = imageItem.GetType().GetProperty("Opacity");
                if (opacityProp is null) return;
                var opacityObj = opacityProp.GetValue(imageItem);
                if (opacityObj is null) return;

                // AnimationType を "直線" (linear) に設定
                var animTypeProp = opacityObj.GetType().GetProperty("AnimationType");
                if (animTypeProp != null)
                {
                    var enumType = animTypeProp.PropertyType;
                    foreach (var ev in Enum.GetValues(enumType))
                    {
                        if (ev.ToString() == "直線")
                        {
                            animTypeProp.SetValue(opacityObj, ev);
                            break;
                        }
                    }
                }

                // Values コレクションを取得
                var valuesProp = opacityObj.GetType().GetProperty("Values");
                if (valuesProp is null) return;
                var values = valuesProp.GetValue(opacityObj);
                if (values is null) return;

                var indexer = values.GetType().GetProperty("Item");
                if (indexer is null) return;
                var firstValue = indexer.GetValue(values, new object[] { 0 });
                if (firstValue is null) return;
                var firstValueType = firstValue.GetType();
                var valueProp = firstValueType.GetProperty("Value");
                var addMethod = values.GetType().GetMethod("Add");

                // Clear existing values and rebuild: 0% → 100% → 100% → 0%
                var clearMethod = values.GetType().GetMethod("Clear");
                clearMethod?.Invoke(values, null);

                void AddKeyframe(double opacity)
                {
                    var kf = Activator.CreateInstance(firstValueType);
                    valueProp?.SetValue(kf, opacity);
                    addMethod?.Invoke(values, new[] { kf });
                }

                AddKeyframe(0.0);    // フェードイン開始
                AddKeyframe(100.0);  // フェードイン完了
                AddKeyframe(100.0);  // フェードアウト開始
                AddKeyframe(0.0);    // フェードアウト完了

                WriteRuntimeLog($"ApplyImageCrossfade: 0%→100%→100%→0% over {fadeFrames} frames each");
            }
            catch (Exception ex)
            {
                // フォールバック: 通常のフェードインのみ
                WriteRuntimeLog($"ApplyImageCrossfade failed ({ex.Message}), falling back to fade-in");
                ApplyImageFade(imageItem, fadeFrames);
            }
        }

        // ========== SP-033: アニメーションバリアント ==========

        /// <summary>
        /// SP-033: Direct API 方式でアニメーションを適用。
        /// Animation.From / Animation.To で開始値・終了値を設定し、
        /// AnimationType で補間方式を指定する。リフレクション不要。
        /// </summary>
#pragma warning disable CS0618 // Animation.From/To は旧形式だが YMM4 v4.50 で動作する
        internal static void ApplyAnimationByType(ImageItem imageItem, string animationType, double fitZoom, int videoWidth, int videoHeight)
        {
            // AnimationType enum: なし=0, 直線移動=1, 加減速移動=103
            var linear = YukkuriMovieMaker.Commons.AnimationType.直線移動;
            var easeInOut = YukkuriMovieMaker.Commons.AnimationType.加減速移動;

            switch (animationType)
            {
                case "zoom_in":
                    imageItem.Zoom.AnimationType = easeInOut;
                    imageItem.Zoom.From = fitZoom;
                    imageItem.Zoom.To = fitZoom * 1.15;
                    break;
                case "zoom_out":
                    imageItem.Zoom.AnimationType = easeInOut;
                    imageItem.Zoom.From = fitZoom * 1.15;
                    imageItem.Zoom.To = fitZoom;
                    break;
                case "pan_left":
                    imageItem.Zoom.From = fitZoom;
                    imageItem.X.AnimationType = easeInOut;
                    imageItem.X.From = videoWidth * 0.05;
                    imageItem.X.To = 0;
                    break;
                case "pan_right":
                    imageItem.Zoom.From = fitZoom;
                    imageItem.X.AnimationType = easeInOut;
                    imageItem.X.From = -(videoWidth * 0.05);
                    imageItem.X.To = 0;
                    break;
                case "pan_up":
                    imageItem.Zoom.From = fitZoom;
                    imageItem.Y.AnimationType = easeInOut;
                    imageItem.Y.From = videoHeight * 0.05;
                    imageItem.Y.To = 0;
                    break;
                case "static":
                    imageItem.Zoom.From = fitZoom;
                    break;
                case "ken_burns":
                default:
                    imageItem.Zoom.AnimationType = linear;
                    imageItem.Zoom.From = fitZoom;
                    imageItem.Zoom.To = fitZoom * 1.05;
                    break;
            }
            // Opacity: デフォルト100%のまま（ApplyImageFade不要）
            WriteRuntimeLog($"ApplyAnimationByType(Direct): {animationType}, zoom={fitZoom:F1}");
        }
#pragma warning restore CS0618

        /// <summary>
        /// ImageItem の不透明度を 100% に強制設定する。
        /// YMM4 の ImageItem デフォルト不透明度が 0% の場合に対応。
        /// </summary>
        internal static void EnsureOpacity100(ImageItem imageItem)
        {
            try
            {
#pragma warning disable CS0618 // Animation.From is obsolete but functional
                imageItem.Opacity.From = 100.0;
#pragma warning restore CS0618
                WriteRuntimeLog("EnsureOpacity100: set via Direct API");
            }
            catch (Exception ex)
            {
                WriteRuntimeLog($"EnsureOpacity100 failed: {ex.Message}");
            }
        }

        /// <summary>
        /// BGMの音量をリフレクションで設定
        /// </summary>
        private static void ApplyBgmVolume(AudioItem bgmItem, double volumeRatio)
        {
            try
            {
                // AudioItem の Volume プロパティを探す
                var volumeProp = bgmItem.GetType().GetProperty("Volume",
                    BindingFlags.Public | BindingFlags.Instance);
                if (volumeProp?.CanWrite == true)
                {
                    // YMM4の Volume は 0-100 のint/double が一般的
                    var propType = volumeProp.PropertyType;
                    if (propType == typeof(int))
                        volumeProp.SetValue(bgmItem, (int)(volumeRatio * 100));
                    else if (propType == typeof(double))
                        volumeProp.SetValue(bgmItem, volumeRatio * 100.0);
                    else
                        volumeProp.SetValue(bgmItem, Convert.ChangeType(volumeRatio * 100.0, propType));

                    WriteRuntimeLog($"BGM Volume set to {volumeRatio * 100:F0}%");
                    return;
                }

                WriteRuntimeLog("BGM Volume property not found, using default volume");
            }
            catch (Exception ex)
            {
                WriteRuntimeLog($"ApplyBgmVolume failed: {ex.Message}");
            }
        }

        /// <summary>
        /// BGMにフェードイン/フェードアウトを適用
        /// </summary>
        private static void ApplyBgmFade(AudioItem bgmItem, int fadeFrames)
        {
            if (fadeFrames <= 0) return;

            try
            {
                // AudioItem の VideoEffects/AfterVideoEffects で音量エンベロープを制御
                // YMM4 の AudioItem は VideoEffects を持たないため、
                // FadeIn/FadeOut 用のプロパティをリフレクションで探す
                foreach (var propName in new[] { "FadeIn", "FadeInFrame", "FadeInFrames" })
                {
                    var prop = bgmItem.GetType().GetProperty(propName,
                        BindingFlags.Public | BindingFlags.Instance);
                    if (prop?.CanWrite == true)
                    {
                        if (prop.PropertyType == typeof(int))
                            prop.SetValue(bgmItem, fadeFrames);
                        else if (prop.PropertyType == typeof(double))
                            prop.SetValue(bgmItem, (double)fadeFrames);
                        WriteRuntimeLog($"BGM {propName} set to {fadeFrames}");
                        break;
                    }
                }

                foreach (var propName in new[] { "FadeOut", "FadeOutFrame", "FadeOutFrames" })
                {
                    var prop = bgmItem.GetType().GetProperty(propName,
                        BindingFlags.Public | BindingFlags.Instance);
                    if (prop?.CanWrite == true)
                    {
                        if (prop.PropertyType == typeof(int))
                            prop.SetValue(bgmItem, fadeFrames);
                        else if (prop.PropertyType == typeof(double))
                            prop.SetValue(bgmItem, (double)fadeFrames);
                        WriteRuntimeLog($"BGM {propName} set to {fadeFrames}");
                        break;
                    }
                }
            }
            catch (Exception ex)
            {
                WriteRuntimeLog($"ApplyBgmFade failed: {ex.Message}");
            }
        }

        /// <summary>
        /// Get WAV file duration in seconds (SP-028: Post-Voice Timeline Resync).
        /// Returns null if the file cannot be read.
        /// </summary>
        internal static double? GetWavDurationSeconds(string audioFilePath)
        {
            try
            {
                using var fs = new FileStream(audioFilePath, FileMode.Open, FileAccess.Read);
                using var reader = new BinaryReader(fs);
                // RIFF header
                if (new string(reader.ReadChars(4)) != "RIFF") return null;
                reader.ReadInt32(); // file size
                if (new string(reader.ReadChars(4)) != "WAVE") return null;

                int sampleRate = 0;
                int byteRate = 0;
                int dataSize = 0;
                bool foundFmt = false;
                bool foundData = false;

                while (fs.Position < fs.Length - 8)
                {
                    string chunkId = new string(reader.ReadChars(4));
                    int chunkSize = reader.ReadInt32();
                    if (chunkId == "fmt ")
                    {
                        reader.ReadInt16(); // audio format
                        reader.ReadInt16(); // num channels
                        sampleRate = reader.ReadInt32();
                        byteRate = reader.ReadInt32();
                        // skip rest of fmt chunk
                        int remaining = chunkSize - 12;
                        if (remaining > 0) reader.ReadBytes(remaining);
                        foundFmt = true;
                    }
                    else if (chunkId == "data")
                    {
                        dataSize = chunkSize;
                        foundData = true;
                        break;
                    }
                    else
                    {
                        // skip unknown chunk
                        if (chunkSize > 0) reader.ReadBytes(chunkSize);
                    }
                }

                if (foundFmt && foundData && byteRate > 0)
                {
                    return (double)dataSize / byteRate;
                }
                return null;
            }
            catch (Exception ex)
            {
                WriteRuntimeLog($"GetWavDurationSeconds failed for {audioFilePath}: {ex.Message}");
                return null;
            }
        }

        /// <summary>
        /// Pre-import quality validation (SP-031).
        /// Checks CSV items for common issues before importing to timeline.
        /// Returns a list of warning messages (empty = all clear).
        /// </summary>
        internal static List<string> ValidateImportItems(IEnumerable<CsvTimelineItem> items)
        {
            var warnings = new List<string>();
            CsvTimelineItem? prev = null;
            int rowIndex = 0;
            CsvTimelineItem? lastItem = null;

            foreach (var item in items)
            {
                rowIndex++;

                // Check for missing audio files
                if (!string.IsNullOrWhiteSpace(item.AudioFilePath) && !File.Exists(item.AudioFilePath))
                {
                    warnings.Add($"Row {rowIndex}: Audio file not found: {item.AudioFilePath}");
                }

                // Check for missing image files
                if (!string.IsNullOrWhiteSpace(item.ImageFilePath) && !File.Exists(item.ImageFilePath))
                {
                    warnings.Add($"Row {rowIndex}: Image file not found: {item.ImageFilePath}");
                }

                // Check for zero or negative duration
                if (item.Duration.HasValue && item.Duration.Value <= 0)
                {
                    warnings.Add($"Row {rowIndex}: Invalid duration: {item.Duration.Value}");
                }

                // Check for empty text when no audio
                if (string.IsNullOrWhiteSpace(item.Text) && string.IsNullOrWhiteSpace(item.AudioFilePath))
                {
                    warnings.Add($"Row {rowIndex}: No text and no audio — row may be empty");
                }

                // Check for gaps between items (> 1 second gap)
                if (prev != null)
                {
                    double prevEnd = prev.StartTime + (prev.Duration ?? 3.0);
                    double gap = item.StartTime - prevEnd;
                    if (gap > 1.0)
                    {
                        warnings.Add($"Row {rowIndex}: Gap of {gap:F1}s detected after previous item");
                    }
                    if (gap < -0.1)
                    {
                        warnings.Add($"Row {rowIndex}: Overlap of {-gap:F1}s with previous item");
                    }
                }

                prev = item;
                lastItem = item;
            }

            // Total duration check
            if (lastItem != null)
            {
                double totalDuration = lastItem.StartTime + (lastItem.Duration ?? 3.0);
                if (totalDuration > 3600)
                {
                    warnings.Add($"Total duration exceeds 1 hour: {totalDuration / 60:F1} minutes");
                }
            }

            return warnings;
        }

        private static int GetImportBaseLayer(Timeline timeline)
        {
            var selectedLayers = timeline.LayerSelection.GetSelectedLayers().ToArray();
            if (selectedLayers.Length > 0)
            {
                return Math.Max(0, selectedLayers.Min());
            }

            return Math.Max(0, timeline.MaxLayer + 1);
        }

        protected void OnPropertyChanged([CallerMemberName] string propertyName = null!)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
        }

        private readonly record struct ImportExecutionResult(
            int ImportedRows,
            int AudioItems,
            int TextItems,
            int ImageItems,
            int VoiceItems,
            int SkippedRows,
            int TimelineItemsAfterImport);
    }
}

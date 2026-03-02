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
        private string audioDirectory = string.Empty;
        private string statusMessage = "Select a CSV file.";
        private bool addSubtitles = true;
        private List<CsvTimelineItem> previewItems = new();
        private double progressValue;

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

        public string AudioDirectory
        {
            get => audioDirectory;
            set
            {
                audioDirectory = value;
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
            var csvDir = Path.GetDirectoryName(CsvPath) ?? string.Empty;
            var defaultAudioDir = Path.Combine(csvDir, "audio");
            AudioDirectory = Directory.Exists(defaultAudioDir) ? defaultAudioDir : csvDir;
            StatusMessage = "CSV selected.";
            AppendLog($"CSV selected: {CsvPath}");
        }

        private void BrowseAudioButton_Click(object sender, RoutedEventArgs e)
        {
            var dialog = new OpenFileDialog
            {
                Title = "Select Any File in Audio Directory",
                Filter = "All Files (*.*)|*.*",
                FileName = "Select Folder"
            };

            if (dialog.ShowDialog() == true)
            {
                AudioDirectory = Path.GetDirectoryName(dialog.FileName) ?? string.Empty;
                AppendLog($"Audio directory selected: {AudioDirectory}");
            }
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
                string capturedAudioDir = AudioDirectory;
                var result = await Task.Run(() =>
                {
                    var reader = new CsvTimelineReader(capturedCsvPath, capturedAudioDir);
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

        private async void ImportButton_Click(object sender, RoutedEventArgs e)
        {
            if (PreviewItems.Count == 0)
            {
                StatusMessage = "Please run Preview first.";
                return;
            }

            try
            {
                SetBusy(true);
                StatusMessage = "Importing to timeline...";
                ProgressValue = 0;
                AppendLog("Starting timeline import...");
                WriteRuntimeLog($"Importing {PreviewItems.Count} items.");

                var progress = new Progress<int>(v => ProgressValue = v);
                
                var result = await ImportToTimelineAsync(PreviewItems, AddSubtitles, progress);

                ProgressValue = 100;
                StatusMessage = $"Imported {result.ImportedRows} items.";
                AppendLog($"Import success: Rows={result.ImportedRows}, Audio={result.AudioItems}, Text={result.TextItems}, TotalTimeline={result.TimelineItemsAfterImport}");

                MessageBox.Show(
                    $"Import Complete!{Environment.NewLine}{Environment.NewLine}" +
                    $"Successfully imported {result.ImportedRows} items.",
                    "CSV Import Success", MessageBoxButton.OK, MessageBoxImage.Information);

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

        private void SetBusy(bool isBusy)
        {
            if (PreviewButton != null) PreviewButton.IsEnabled = !isBusy;
            if (ImportButton != null) ImportButton.IsEnabled = !isBusy;
            if (BrowseCsvButton != null) BrowseCsvButton.IsEnabled = !isBusy;
            if (BrowseAudioButton != null) BrowseAudioButton.IsEnabled = !isBusy;
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

                    for (int i = 0; i < items.Count; i++)
                    {
                        var item = items[i];
                        int frame = (int)Math.Round(item.StartTime * fps);
                        int length = (int)Math.Round((item.Duration ?? 1.0) * fps);

                        if (!string.IsNullOrEmpty(item.AudioFilePath) && File.Exists(item.AudioFilePath))
                        {
                            activeTimeline.Items.Add(new AudioItem(item.AudioFilePath) { Frame = frame, Layer = baseLayer, Length = length });
                            audioCount++;
                        }

                        if (addSubtitles && !string.IsNullOrEmpty(item.Text))
                        {
                            activeTimeline.Items.Add(new TextItem { Text = item.Text, Frame = frame, Layer = baseLayer + 1, Length = length });
                            textCount++;
                        }

                        count++;
                        progress.Report((int)(i * 100.0 / items.Count));
                    }

                    activeTimeline.RefreshTimelineLengthAndMaxLayer();
                    return new ImportExecutionResult(count, audioCount, textCount, 0, activeTimeline.Items.Count);
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

                int fps = Math.Max(1, activeTimeline.VideoInfo.FPS);
                int baseLayer = GetImportBaseLayer(activeTimeline);

                int importedRows = 0;
                int audioItemsCount = 0;
                int textItemsCount = 0;
                int skippedRows = 0;

                // Add all items in a single batch if possible for better performance
                var allTimelineItems = new List<IItem>();
                var startFrames = new List<int>();
                var layers = new List<int>();

                foreach (var csvItem in items)
                {
                    int startFrame = Math.Max(0, (int)Math.Round(csvItem.StartTime * fps));
                    int lengthFrames = Math.Max(1, (int)Math.Round((csvItem.Duration ?? 3.0) * fps));

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

                    if (shouldAddSubtitles && !string.IsNullOrWhiteSpace(csvItem.Text))
                    {
                        var text = new TextItem
                        {
                            Frame = startFrame,
                            Layer = baseLayer + 1,
                            Length = lengthFrames,
                            PlaybackRate = 1.0,
                            Text = csvItem.Text
                        };
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
                    // TryAddItems(IItem[] items, int frame, int layer, bool isUndoEnabled)
                    // Note: If we use this overload, it might offset ALL items by (frame, layer).
                    // We should probably add them one by one or use a different approach if they have different start frames.
                    // Actually, activeTimeline.Items.Add(item) followed by Refresh might be better if we handle Undo ourselves.
                    // But TryAddItems is safer for YMM4's internal state.
                    
                    foreach (var item in allTimelineItems)
                    {
                        activeTimeline.Items.Add(item);
                    }
                    activeTimeline.RefreshTimelineLengthAndMaxLayer();
                }

                return new ImportExecutionResult(importedRows, audioItemsCount, textItemsCount, skippedRows, activeTimeline.Items.Count);
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
            var timelineAreaViewModel = GetPropertyValue(mainViewModel, "TimelineAreaViewModel");
            if (timelineAreaViewModel is null)
            {
                detail = "timeline-area-viewmodel-missing";
                return false;
            }

            var reactiveViewModel = GetPropertyValue(timelineAreaViewModel, "ViewModel");
            if (reactiveViewModel is null)
            {
                detail = "timeline-area-reactive-viewmodel-missing";
                return false;
            }

            var timelineViewModel = GetPropertyValue(reactiveViewModel, "Value");
            if (timelineViewModel is null)
            {
                detail = "timeline-viewmodel-value-missing";
                return false;
            }

            var timelineCandidate =
                GetPropertyValue(timelineViewModel, "Timeline") as Timeline ??
                GetFieldValue(timelineViewModel, "timeline") as Timeline;

            if (timelineCandidate is null)
            {
                detail = "timeline-field-missing";
                return false;
            }

            timeline = timelineCandidate;
            detail = "source=main-window-reflection";
            return true;
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
            int SkippedRows,
            int TimelineItemsAfterImport);
    }
}

using Microsoft.Win32;
using NLMSlidePlugin.Core;
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.IO;
using System.Linq;
using System.Runtime.CompilerServices;
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
        private readonly Timeline? timeline;
        private string csvPath = string.Empty;
        private string audioDirectory = string.Empty;
        private string statusMessage = "Select a CSV file.";
        private bool addSubtitles = true;
        private List<CsvTimelineItem> previewItems = new();

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

        private void BrowseCsvButton_Click(object sender, RoutedEventArgs e)
        {
            var dialog = new OpenFileDialog
            {
                Filter = "CSV files (*.csv)|*.csv|All files (*.*)|*.*",
                Title = "Select CSV File",
                CheckFileExists = true
            };

            if (dialog.ShowDialog() != true)
            {
                return;
            }

            CsvPath = dialog.FileName;

            var csvDir = Path.GetDirectoryName(CsvPath) ?? string.Empty;
            var defaultAudioDir = Path.Combine(csvDir, "audio");
            AudioDirectory = Directory.Exists(defaultAudioDir) ? defaultAudioDir : csvDir;
            StatusMessage = "CSV selected. Click Preview.";
        }

        private void BrowseAudioButton_Click(object sender, RoutedEventArgs e)
        {
            var dialog = new OpenFileDialog
            {
                Title = "Select Any File in Audio Directory",
                Filter = "All Files (*.*)|*.*",
                CheckFileExists = false,
                FileName = "Select Folder"
            };

            if (dialog.ShowDialog() == true)
            {
                AudioDirectory = Path.GetDirectoryName(dialog.FileName) ?? string.Empty;
            }
        }

        private void PreviewButton_Click(object sender, RoutedEventArgs e)
        {
            if (string.IsNullOrWhiteSpace(CsvPath))
            {
                StatusMessage = "Please select a CSV file.";
                return;
            }

            if (!File.Exists(CsvPath))
            {
                StatusMessage = "CSV file does not exist.";
                return;
            }

            try
            {
                var reader = new CsvTimelineReader(CsvPath, AudioDirectory);
                var items = reader.ReadTimeline();
                PreviewItems = items;

                int audioFound = items.Count(i => !string.IsNullOrEmpty(i.AudioFilePath));
                StatusMessage = $"Preview loaded: {items.Count} rows, audio found: {audioFound}.";
            }
            catch (Exception ex)
            {
                PreviewItems = new List<CsvTimelineItem>();
                StatusMessage = $"Preview failed: {ex.Message}";
            }
        }

        private void ImportButton_Click(object sender, RoutedEventArgs e)
        {
            if (string.IsNullOrWhiteSpace(CsvPath) || !File.Exists(CsvPath))
            {
                StatusMessage = "Please select a valid CSV file.";
                return;
            }

            if (PreviewItems.Count == 0)
            {
                PreviewButton_Click(sender, e);
                if (PreviewItems.Count == 0)
                {
                    StatusMessage = "No rows available to import.";
                    return;
                }
            }

            try
            {
                ImportButton.IsEnabled = false;
                StatusMessage = "Importing...";

                var result = ImportToTimeline(PreviewItems, AddSubtitles);
                if (result.ImportedRows <= 0)
                {
                    throw new InvalidOperationException("No items were added to the timeline.");
                }

                StatusMessage = $"Imported {result.ImportedRows} rows (audio: {result.AudioItems}, text: {result.TextItems}, skipped: {result.SkippedRows}, timeline items: {result.TimelineItemsAfterImport})";

                MessageBox.Show(
                    $"Imported {result.ImportedRows} rows to timeline.\n\n" +
                    $"Audio items: {result.AudioItems}\n" +
                    $"Text items: {result.TextItems}\n" +
                    $"Skipped rows: {result.SkippedRows}\n" +
                    $"Timeline total items: {result.TimelineItemsAfterImport}",
                    "CSV Import Result",
                    MessageBoxButton.OK,
                    MessageBoxImage.Information);

                DialogResult = true;
                Close();
            }
            catch (Exception ex)
            {
                StatusMessage = $"Import failed: {ex.Message}";
                MessageBox.Show(
                    $"Import failed:\n{ex.Message}",
                    "CSV Import Error",
                    MessageBoxButton.OK,
                    MessageBoxImage.Error);
            }
            finally
            {
                ImportButton.IsEnabled = true;
            }
        }

        private ImportExecutionResult ImportToTimeline(IEnumerable<CsvTimelineItem> items, bool shouldAddSubtitles)
        {
            if (timeline is null)
            {
                throw new InvalidOperationException("Timeline context is not available.");
            }

            int fps = Math.Max(1, timeline.VideoInfo.FPS);
            int baseLayer = GetImportBaseLayer(timeline);

            int importedRows = 0;
            int audioItems = 0;
            int textItems = 0;
            int skippedRows = 0;

            foreach (var csvItem in items)
            {
                int startFrame = Math.Max(0, (int)Math.Round(csvItem.StartTime * fps));
                int lengthFrames = Math.Max(1, (int)Math.Round((csvItem.Duration ?? 3.0) * fps));

                var timelineItems = new List<IItem>();
                bool hasAudio = false;
                bool hasText = false;

                if (!string.IsNullOrWhiteSpace(csvItem.AudioFilePath) && File.Exists(csvItem.AudioFilePath))
                {
                    var audio = new AudioItem(csvItem.AudioFilePath)
                    {
                        Frame = 0,
                        Layer = 0,
                        Length = lengthFrames,
                        PlaybackRate = 1.0
                    };
                    timelineItems.Add(audio);
                    hasAudio = true;
                }

                if (shouldAddSubtitles && !string.IsNullOrWhiteSpace(csvItem.Text))
                {
                    var text = new TextItem
                    {
                        Frame = 0,
                        Layer = 1,
                        Length = lengthFrames,
                        PlaybackRate = 1.0,
                        Text = csvItem.Text
                    };
                    timelineItems.Add(text);
                    hasText = true;
                }

                if (timelineItems.Count == 0)
                {
                    skippedRows++;
                    continue;
                }

                int beforeCount = timeline.Items.Count;
                bool added = timeline.TryAddItems(timelineItems.ToArray(), startFrame, baseLayer, true);
                int afterCount = timeline.Items.Count;
                if (!added || afterCount <= beforeCount)
                {
                    skippedRows++;
                    continue;
                }

                importedRows++;
                if (hasAudio)
                {
                    audioItems++;
                }

                if (hasText)
                {
                    textItems++;
                }
            }

            timeline.RefreshTimelineLengthAndMaxLayer();
            return new ImportExecutionResult(importedRows, audioItems, textItems, skippedRows, timeline.Items.Count);
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

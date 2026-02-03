using Microsoft.Win32;
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.IO;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Threading.Tasks;
using System.Windows;
using NLMSlidePlugin.Core;

namespace NLMSlidePlugin.TimelinePlugin
{
    /// <summary>
    /// CSVインポートダイアログのコードビハインド
    /// </summary>
    public partial class CsvImportDialog : Window, INotifyPropertyChanged
    {
        private string _csvPath = string.Empty;
        private string _audioDirectory = string.Empty;
        private string _statusMessage = "CSVファイルを選択してください";
        private bool _addSubtitles = true;
        private List<CsvTimelineItem> _previewItems = new();

        public event PropertyChangedEventHandler? PropertyChanged;

        public CsvImportDialog()
        {
            InitializeComponent();
            DataContext = this;
        }

        #region Properties

        public string CsvPath
        {
            get => _csvPath;
            set { _csvPath = value; OnPropertyChanged(); }
        }

        public string AudioDirectory
        {
            get => _audioDirectory;
            set { _audioDirectory = value; OnPropertyChanged(); }
        }

        public string StatusMessage
        {
            get => _statusMessage;
            set { _statusMessage = value; OnPropertyChanged(); }
        }

        public bool AddSubtitles
        {
            get => _addSubtitles;
            set { _addSubtitles = value; OnPropertyChanged(); }
        }

        public List<CsvTimelineItem> PreviewItems
        {
            get => _previewItems;
            set
            {
                _previewItems = value;
                PreviewDataGrid.ItemsSource = value;
                OnPropertyChanged();
            }
        }

        #endregion

        #region Event Handlers

        private void BrowseCsvButton_Click(object sender, RoutedEventArgs e)
        {
            var dialog = new OpenFileDialog
            {
                Filter = "CSVファイル (*.csv)|*.csv|すべてのファイル (*.*)|*.*",
                Title = "タイムラインCSVを選択",
                CheckFileExists = true
            };

            if (dialog.ShowDialog() == true)
            {
                CsvPath = dialog.FileName;
                
                // 音声ディレクトリを自動設定（CSVと同じフォルダ/audio）
                var csvDir = Path.GetDirectoryName(CsvPath);
                var defaultAudioDir = Path.Combine(csvDir, "audio");
                if (Directory.Exists(defaultAudioDir))
                {
                    AudioDirectory = defaultAudioDir;
                }
                else
                {
                    AudioDirectory = csvDir;
                }

                StatusMessage = "プレビューボタンをクリックして内容を確認してください";
            }
        }

        private void BrowseAudioButton_Click(object sender, RoutedEventArgs e)
        {
            // FolderBrowserDialogの代わりにOpenFileDialogを使用
            var dialog = new OpenFileDialog
            {
                Title = "音声ファイルを含むフォルダを選択（ファイルは無視されます）",
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
            if (string.IsNullOrEmpty(CsvPath))
            {
                StatusMessage = "CSVファイルを選択してください";
                return;
            }

            if (!File.Exists(CsvPath))
            {
                StatusMessage = "指定されたCSVファイルが見つかりません";
                return;
            }

            try
            {
                var reader = new CsvTimelineReader(CsvPath, AudioDirectory);
                var items = reader.ReadTimeline();
                PreviewItems = items;

                int audioFound = items.Count(i => !string.IsNullOrEmpty(i.AudioFilePath));
                StatusMessage = $"{items.Count}件のデータを読み込みました（音声: {audioFound}件）";
            }
            catch (Exception ex)
            {
                StatusMessage = $"読み込みエラー: {ex.Message}";
                PreviewItems = new List<CsvTimelineItem>();
            }
        }

        private async void ImportButton_Click(object sender, RoutedEventArgs e)
        {
            if (string.IsNullOrEmpty(CsvPath) || !File.Exists(CsvPath))
            {
                StatusMessage = "CSVファイルを選択してください";
                return;
            }

            if (PreviewItems.Count == 0)
            {
                PreviewButton_Click(sender, e);
                if (PreviewItems.Count == 0)
                {
                    StatusMessage = "インポートするデータがありません";
                    return;
                }
            }

            try
            {
                ImportButton.IsEnabled = false;
                StatusMessage = "インポート中...";

                // TODO: YMM4 APIを使用して実際にタイムラインに追加
                await Task.Delay(500); // シミュレーション

                StatusMessage = $"{PreviewItems.Count}件のインポートが完了しました";
                
                // 成功ダイアログ
                MessageBox.Show($"{PreviewItems.Count}件のデータをインポートしました。\n\n" +
                              $"音声ファイル: {PreviewItems.Count(i => !string.IsNullOrEmpty(i.AudioFilePath))}件\n" +
                              $"字幕: {(AddSubtitles ? "追加" : "スキップ")}",
                              "インポート完了", MessageBoxButton.OK, MessageBoxImage.Information);

                DialogResult = true;
                Close();
            }
            catch (Exception ex)
            {
                StatusMessage = $"インポートエラー: {ex.Message}";
                MessageBox.Show($"インポート中にエラーが発生しました:\n{ex.Message}", 
                              "エラー", MessageBoxButton.OK, MessageBoxImage.Error);
            }
            finally
            {
                ImportButton.IsEnabled = true;
            }
        }

        #endregion

        #region INotifyPropertyChanged

        protected void OnPropertyChanged([CallerMemberName] string propertyName = null!)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
        }

        #endregion
    }
}

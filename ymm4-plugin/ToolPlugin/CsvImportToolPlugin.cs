using System;
using System.ComponentModel;
using System.Runtime.CompilerServices;
using System.Windows;
using System.Windows.Controls;
using NLMSlidePlugin.TimelinePlugin;
using YukkuriMovieMaker.Plugin;
using YukkuriMovieMaker.Project;
using YukkuriMovieMaker.UndoRedo;

namespace NLMSlidePlugin.ToolPlugin
{
    /// <summary>
    /// CSV timeline import tool plugin for YMM4.
    /// </summary>
    public sealed class CsvImportToolPlugin : IToolPlugin
    {
        public string Name => "CSV Timeline Import";
        public Type ViewModelType => typeof(CsvImportToolViewModel);
        public Type ViewType => typeof(CsvImportToolView);
    }

    /// <summary>
    /// Tool window view model for CSV timeline import.
    /// </summary>
    public sealed class CsvImportToolViewModel : INotifyPropertyChanged
    {
        public event PropertyChangedEventHandler? PropertyChanged;

        public string Title => "CSV Timeline Import";
        public string Description => "Import CSV rows and matching WAV files into the active timeline.";

        public Timeline Timeline { get; set; } = null!;
        public Scenes Scenes { get; set; } = null!;
        public UndoRedoManager UndoRedoManager { get; set; } = null!;

        private bool isBusy;

        public bool IsBusy
        {
            get => isBusy;
            private set
            {
                if (isBusy == value)
                {
                    return;
                }

                isBusy = value;
                OnPropertyChanged();
            }
        }

        public void ShowImportDialog()
        {
            if (IsBusy)
            {
                return;
            }

            try
            {
                IsBusy = true;
                var dialog = new CsvImportDialog(Timeline);
                dialog.ShowDialog();
            }
            catch (Exception ex)
            {
                MessageBox.Show(
                    $"Failed to open CSV import dialog.\n{ex.Message}",
                    "CSV Import Error",
                    MessageBoxButton.OK,
                    MessageBoxImage.Error);
            }
            finally
            {
                IsBusy = false;
            }
        }

        private void OnPropertyChanged([CallerMemberName] string? propertyName = null)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
        }
    }

    /// <summary>
    /// Tool window view.
    /// </summary>
    public sealed class CsvImportToolView : UserControl
    {
        private readonly TextBlock titleText;
        private readonly TextBlock descriptionText;

        public CsvImportToolView()
        {
            Width = 420;
            Height = 220;

            titleText = new TextBlock
            {
                FontSize = 16,
                FontWeight = FontWeights.Bold,
                Margin = new Thickness(0, 0, 0, 10)
            };

            descriptionText = new TextBlock
            {
                TextWrapping = TextWrapping.Wrap,
                Margin = new Thickness(0, 0, 0, 20)
            };

            var importButton = new Button
            {
                Content = "Open CSV Import Dialog",
                Width = 320,
                Height = 40,
                HorizontalAlignment = HorizontalAlignment.Center
            };
            importButton.Click += (_, _) => ResolveViewModel().ShowImportDialog();

            var stackPanel = new StackPanel
            {
                Margin = new Thickness(10)
            };
            stackPanel.Children.Add(titleText);
            stackPanel.Children.Add(descriptionText);
            stackPanel.Children.Add(importButton);
            Content = stackPanel;

            DataContextChanged += (_, _) => ApplyViewModelText();

            if (DataContext is null)
            {
                DataContext = new CsvImportToolViewModel();
            }

            ApplyViewModelText();
        }

        private CsvImportToolViewModel ResolveViewModel()
        {
            return DataContext as CsvImportToolViewModel ?? new CsvImportToolViewModel();
        }

        private void ApplyViewModelText()
        {
            var viewModel = DataContext as CsvImportToolViewModel;
            titleText.Text = viewModel?.Title ?? "CSV Timeline Import";
            descriptionText.Text = viewModel?.Description ?? "CSV import tool";
        }
    }
}

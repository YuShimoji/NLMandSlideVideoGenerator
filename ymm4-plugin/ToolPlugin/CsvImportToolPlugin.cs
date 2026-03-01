using System;
using System.Windows;
using System.Windows.Controls;
using NLMSlidePlugin.TimelinePlugin;
using YukkuriMovieMaker.Commons;
using YukkuriMovieMaker.Plugin;
using YukkuriMovieMaker.Project;
using YukkuriMovieMaker.UndoRedo;

namespace NLMSlidePlugin.ToolPlugin
{
    /// <summary>
    /// CSV timeline import tool plugin for YMM4.
    /// Appears in the Tools menu as an AvalonDock pane.
    /// </summary>
    public sealed class CsvImportToolPlugin : IToolPlugin
    {
        public string Name => "CSV Timeline Import";
        public Type ViewModelType => typeof(CsvImportToolViewModel);
        public Type ViewType => typeof(CsvImportToolView);
    }

    /// <summary>
    /// Tool window view model for CSV timeline import.
    /// Inherits from YMM4's Bindable to avoid AssemblyLoadContext type mismatch
    /// with INotifyPropertyChanged (InvalidCastException).
    /// Timeline, Scenes, UndoRedoManager are injected by YMM4 via property setters.
    /// </summary>
    public sealed class CsvImportToolViewModel : Bindable
    {
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
    }

    /// <summary>
    /// Tool window view (XAML-backed UserControl).
    /// </summary>
    public sealed partial class CsvImportToolView : UserControl
    {
        public CsvImportToolView()
        {
            InitializeComponent();
        }

        private void OpenImportDialog_Click(object sender, RoutedEventArgs e)
        {
            if (DataContext is CsvImportToolViewModel vm)
            {
                vm.ShowImportDialog();
            }
            else
            {
                // Fallback: open dialog without Timeline injection
                try
                {
                    var dialog = new CsvImportDialog();
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
            }
        }
    }
}

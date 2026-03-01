using System;
using System.Windows;
using System.Windows.Controls;
using NLMSlidePlugin.TimelinePlugin;
using YukkuriMovieMaker.Plugin;

namespace NLMSlidePlugin.SettingsPlugin
{
    /// <summary>
    /// Settings entry point for CSV timeline import.
    /// Appears in File > Settings left panel.
    /// Uses SettingsBase&lt;T&gt; pattern (matching YMM4 discovery mechanism).
    /// </summary>
    public class CsvImportSettingPlugin : SettingsBase<CsvImportSettingPlugin>
    {
        public override SettingsCategory Category => SettingsCategory.None;
        public override string Name => "CSV Timeline Import";
        public override bool HasSettingView => true;
        public override object SettingView => new CsvImportSettingView();

        public override void Initialize()
        {
        }
    }

    /// <summary>
    /// Settings view (XAML-backed UserControl).
    /// </summary>
    public partial class CsvImportSettingView : UserControl
    {
        public CsvImportSettingView()
        {
            InitializeComponent();
        }

        private void OpenDialog_Click(object sender, RoutedEventArgs e)
        {
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

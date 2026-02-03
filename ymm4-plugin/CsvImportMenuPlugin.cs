using System;
using System.Windows;
using YukkuriMovieMaker.Plugin;
using NLMSlidePlugin.TimelinePlugin;

namespace NLMSlidePlugin
{
    /// <summary>
    /// CSVタイムラインインポート メニュープラグイン
    /// YMM4のメニューからCSVインポートダイアログを起動
    /// </summary>
    public class CsvImportMenuPlugin : IPluginMenuItem
    {
        public string Name => "CSVタイムラインをインポート...";
        public string MenuPath => "ファイル/インポート";
        public string Description => "CSVタイムラインと音声ファイルをインポートします";

        /// <summary>
        /// メニュー項目がクリックされた時に呼ばれる
        /// </summary>
        public void Execute(IPluginContext context)
        {
            try
            {
                var dialog = new CsvImportDialog();
                dialog.ShowDialog();
            }
            catch (Exception ex)
            {
                MessageBox.Show($"エラーが発生しました:\n{ex.Message}", 
                    "CSVインポートエラー", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        /// <summary>
        /// メニュー項目の表示状態を確認
        /// </summary>
        public bool CanExecute(IPluginContext context)
        {
            // 常に有効
            return true;
        }
    }
}

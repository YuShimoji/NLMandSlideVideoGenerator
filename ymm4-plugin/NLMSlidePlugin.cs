using System;
using System.Windows;
using YukkuriMovieMaker.Plugin;

namespace NLMSlidePlugin
{
    /// <summary>
    /// NLM Slide Plugin メインクラス
    /// YMM4プラグインエントリポイント（シナリオA実装）
    /// </summary>
    public class NLMSlidePlugin : IPlugin
    {
        public string Name => "NLM Slide Plugin";
        public string Author => "NLMandSlideVideoGenerator Project";
        public string Description => "CSVタイムライン自動インポートプラグイン（シナリオA）";
        public string Version => "0.2.0";

        /// <summary>
        /// プラグイン初期化時に呼ばれる
        /// </summary>
        public void Initialize()
        {
            // プラグイン初期化
            System.Diagnostics.Debug.WriteLine($"[{Name}] Plugin initialized");
        }

        /// <summary>
        /// プラグイン終了時に呼ばれる
        /// </summary>
        public void Dispose()
        {
            // リソース解放
            System.Diagnostics.Debug.WriteLine($"[{Name}] Plugin disposed");
        }
    }
}

using YukkuriMovieMaker.Plugin;

namespace NLMSlidePlugin
{
    /// <summary>
    /// プラグイン情報クラス
    /// YMM4がプラグインを識別するためのメタデータを提供
    /// </summary>
    public class PluginInfo : IPlugin
    {
        public string Name => "NLM Slide Plugin";
        public string Author => "NLMandSlideVideoGenerator Project";
        public string Description => "NotebookLM台本からの自動タイムライン・音声連携プラグイン";
        public string Version => "0.1.0";
    }
}

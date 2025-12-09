using YukkuriMovieMaker.Plugin;

namespace NLMSlidePlugin.TextCompletionPlugin
{
    /// <summary>
    /// ITextCompletionPlugin の実装サンプル
    /// 将来的にはGemini APIや外部LLMとの連携に使用
    /// 現時点ではスケルトン実装
    /// </summary>
    /// <remarks>
    /// 用途:
    /// - 台本テキストの校正・修正提案
    /// - NotebookLM出力の整形
    /// - 解説動画用のテキスト調整
    /// </remarks>
    // [Export(typeof(ITextCompletionPlugin))]  // PoC完了後に有効化
    public class CsvScriptCompletionPlugin // : ITextCompletionPlugin
    {
        public string Name => "CSV Script Completion";
        public string Description => "台本CSVテキストの補完・校正";

        // TODO: ITextCompletionPlugin インターフェースの実装
        // - GetCompletionAsync(string text, CancellationToken ct)
        // - 設定UI（API Key等）
        
        /// <summary>
        /// テキスト補完のスタブ実装
        /// </summary>
        public Task<string> CompleteTextAsync(string inputText, CancellationToken cancellationToken = default)
        {
            // TODO: Gemini API連携
            // 現時点では入力をそのまま返す
            return Task.FromResult(inputText);
        }

        /// <summary>
        /// 校正提案のスタブ実装
        /// </summary>
        public Task<string> SuggestCorrectionsAsync(string inputText, CancellationToken cancellationToken = default)
        {
            // TODO: 校正ロジック実装
            return Task.FromResult(inputText);
        }
    }
}

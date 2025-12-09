using YukkuriMovieMaker.Plugin;

namespace NLMSlidePlugin.VoicePlugin
{
    /// <summary>
    /// IVoicePlugin の実装スケルトン
    /// CSVタイムラインの行に対応する音声アイテムを生成
    /// </summary>
    /// <remarks>
    /// 用途:
    /// - CSV行をYMM4タイムラインのボイスアイテムとして追加
    /// - 既存のYMM4ボイス（AquesTalk等）との連携
    /// - 外部TTS音声ファイルのインポート
    /// </remarks>
    // [Export(typeof(IVoicePlugin))]  // PoC完了後に有効化
    public class CsvTimelineVoicePlugin // : IVoicePlugin
    {
        public string Name => "CSV Timeline Voice";
        public string Description => "CSVタイムラインからボイスアイテムを生成";

        // TODO: IVoicePlugin インターフェースの実装
        // 必要なプロパティとメソッド:
        // - SupportedVoiceTypes
        // - CreateVoiceAsync(string text, VoiceSettings settings, CancellationToken ct)
        // - 設定UI

        /// <summary>
        /// CSVから音声生成するスタブ
        /// </summary>
        /// <param name="text">台本テキスト</param>
        /// <param name="speaker">話者名</param>
        /// <returns>生成された音声データのパス（仮）</returns>
        public Task<string?> GenerateVoiceAsync(string text, string speaker, CancellationToken cancellationToken = default)
        {
            // TODO: 実際の音声生成ロジック
            // - YMM4内蔵ボイスの呼び出し
            // - 外部WAVファイルの参照
            // - 非同期処理

            // 現時点ではnullを返す（未実装）
            return Task.FromResult<string?>(null);
        }

        /// <summary>
        /// 利用可能な話者一覧を取得（スタブ）
        /// </summary>
        public IEnumerable<string> GetAvailableSpeakers()
        {
            // TODO: YMM4から利用可能なボイスを取得
            return new[] { "れいむ", "まりさ", "ゆかり", "ずんだもん" };
        }
    }
}

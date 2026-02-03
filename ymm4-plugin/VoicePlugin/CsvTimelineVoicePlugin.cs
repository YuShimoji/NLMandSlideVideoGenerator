using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using NLMSlidePlugin.Core;
using NLMSlidePlugin.TimelinePlugin;

namespace NLMSlidePlugin.VoicePlugin
{
    /// <summary>
    /// CSVタイムラインボイスプラグイン（シナリオA実装）
    /// CSVタイムラインの行に対応する音声アイテムを生成
    /// </summary>
    /// <remarks>
    /// 用途:
    /// - CSV行をYMM4タイムラインのボイスアイテムとして追加
    /// - 既存のYMM4ボイス（AquesTalk等）との連携
    /// - 外部TTS音声ファイルのインポート
    /// </remarks>
    public class CsvTimelineVoicePlugin
    {
        public string Name => "CSV Timeline Voice";
        public string Author => "NLMandSlideVideoGenerator Project";
        public string Description => "CSVタイムラインからボイスアイテムを生成（シナリオA実装）";
        public string Version => "0.2.1";

        private CsvImportSettings _settings = new();

        /// <summary>
        /// CSVインポートダイアログを表示
        /// </summary>
        public void ShowImportDialog()
        {
            var dialog = new CsvImportDialog();
            dialog.ShowDialog();
        }

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

        /// <summary>
        /// CSVファイルからタイムラインを読み込み
        /// </summary>
        public List<CsvTimelineItem> LoadTimelineFromCsv(string csvPath, string? audioDir = null)
        {
            var reader = new CsvTimelineReader(csvPath, audioDir);
            return reader.ReadTimeline();
        }
    }
}

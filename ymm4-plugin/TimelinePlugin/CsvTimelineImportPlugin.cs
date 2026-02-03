using Microsoft.Win32;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using NLMSlidePlugin.Core;

namespace NLMSlidePlugin.TimelinePlugin
{
    /// <summary>
    /// CSVタイムラインからYMM4に音声と字幕をインポートするプラグイン
    /// シナリオA実装：CSV読み込み → WAV配置 → テキスト配置
    /// </summary>
    public class CsvTimelineImportPlugin
    {
        public string Name => "CSV Timeline Import";
        public string Author => "NLMandSlideVideoGenerator Project";
        public string Description => "CSVタイムラインから音声と字幕を一括インポート";
        public string Version => "0.2.0";

        /// <summary>
        /// CSVファイル選択ダイアログを表示
        /// </summary>
        public string? SelectCsvFile()
        {
            var dialog = new OpenFileDialog
            {
                Filter = "CSVファイル (*.csv)|*.csv|すべてのファイル (*.*)|*.*",
                Title = "タイムラインCSVを選択",
                CheckFileExists = true
            };

            if (dialog.ShowDialog() == true)
            {
                return dialog.FileName;
            }
            return null;
        }

        /// <summary>
        /// CSVからタイムラインを読み込み
        /// </summary>
        public List<CsvTimelineItem> LoadTimeline(string csvPath, string? audioDir = null)
        {
            var reader = new CsvTimelineReader(csvPath, audioDir);
            return reader.ReadTimeline();
        }

        /// <summary>
        /// 音声ファイルの長さを取得（秒）
        /// 現在は固定値、将来的にNAudio等で実測
        /// </summary>
        public double GetAudioDuration(string audioPath)
        {
            // TODO: NAudioを使用して実際の音声長を取得
            // 現在は3秒をデフォルトとする
            return 3.0;
        }
    }

    /// <summary>
    /// CSVインポート用の設定クラス
    /// </summary>
    public class CsvImportSettings
    {
        /// <summary>
        /// 最後に使用したCSVファイルパス
        /// </summary>
        public string? LastCsvPath { get; set; }

        /// <summary>
        /// 音声ファイル検索ディレクトリ
        /// </summary>
        public string? AudioDirectory { get; set; }

        /// <summary>
        /// デフォルトの音声長（秒）
        /// </summary>
        public double DefaultAudioDuration { get; set; } = 3.0;

        /// <summary>
        /// 字幕を追加するかどうか
        /// </summary>
        public bool AddSubtitles { get; set; } = true;

        /// <summary>
        /// 字幕と音声の間隔（秒）
        /// </summary>
        public double SubtitleOffset { get; set; } = 0.0;
    }
}

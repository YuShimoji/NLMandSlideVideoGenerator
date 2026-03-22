using System;
using System.Collections.Generic;

namespace NLMSlidePlugin.Core
{
    /// <summary>
    /// CSVのSpeaker名をYMM4のIVoiceSpeaker識別子(API, ID)にマッピングする。
    /// YMM4非依存（Core）のため、IVoiceSpeakerへの直接参照は持たない。
    /// </summary>
    public class VoiceSpeakerMapping
    {
        private readonly Dictionary<string, VoiceSpeakerId> _mappings;

        public VoiceSpeakerMapping(Dictionary<string, VoiceSpeakerId>? mappings = null)
        {
            _mappings = mappings ?? new Dictionary<string, VoiceSpeakerId>(StringComparer.OrdinalIgnoreCase);
        }

        /// <summary>
        /// CSV speaker名からYMM4のAPI/IDペアを解決する。
        /// 見つからない場合はデフォルトスピーカーを返す。
        /// </summary>
        public VoiceSpeakerId Resolve(string speakerName)
        {
            if (string.IsNullOrWhiteSpace(speakerName))
                return DefaultSpeaker;

            return _mappings.TryGetValue(speakerName, out var id)
                ? id
                : DefaultSpeaker;
        }

        /// <summary>
        /// マッピングが存在するかを返す
        /// </summary>
        public bool HasMapping(string speakerName)
        {
            return !string.IsNullOrWhiteSpace(speakerName) && _mappings.ContainsKey(speakerName);
        }

        /// <summary>
        /// 登録済みマッピング数
        /// </summary>
        public int Count => _mappings.Count;

        /// <summary>
        /// デフォルトスピーカー（マッピング未登録時のフォールバック）
        /// </summary>
        public static VoiceSpeakerId DefaultSpeaker { get; } = new("YukkuriVoice", "reimu");

        /// <summary>
        /// ゆっくりボイス中心のデフォルトマッピングを生成
        /// </summary>
        public static VoiceSpeakerMapping CreateDefault()
        {
            var mappings = new Dictionary<string, VoiceSpeakerId>(StringComparer.OrdinalIgnoreCase)
            {
                // ゆっくりボイス（YMM4組み込み）
                { "れいむ", new("YukkuriVoice", "reimu") },
                { "まりさ", new("YukkuriVoice", "marisa") },
                { "Reimu", new("YukkuriVoice", "reimu") },
                { "Marisa", new("YukkuriVoice", "marisa") },

                // 汎用Speaker名からのマッピング
                { "Speaker1", new("YukkuriVoice", "reimu") },
                { "Speaker2", new("YukkuriVoice", "marisa") },
                { "ナレーター", new("YukkuriVoice", "reimu") },
                { "Host", new("YukkuriVoice", "reimu") },
                { "Host1", new("YukkuriVoice", "reimu") },
                { "Host2", new("YukkuriVoice", "marisa") },

                // キャラクター名（すべてYMM4内蔵ゆっくりボイスにマッピング）
                { "ずんだもん", new("YukkuriVoice", "reimu") },
                { "四国めたん", new("YukkuriVoice", "marisa") },
                { "Zundamon", new("YukkuriVoice", "reimu") },
            };

            return new VoiceSpeakerMapping(mappings);
        }
    }

    /// <summary>
    /// YMM4のIVoiceSpeaker.IsMatch(api, id)に渡す識別子ペア
    /// </summary>
    public record VoiceSpeakerId(string Api, string Id);
}

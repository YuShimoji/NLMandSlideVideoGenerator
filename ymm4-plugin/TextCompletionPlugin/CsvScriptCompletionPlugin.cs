using System.Net.Http;
using System.Text;
using System.Text.Json;

namespace NLMSlidePlugin.TextCompletionPlugin
{
    /// <summary>
    /// Gemini APIを利用したテキスト補完プラグイン
    /// CSV台本テキストの校正・補完を行う
    /// </summary>
    /// <remarks>
    /// 用途:
    /// - 台本テキストの校正・修正提案
    /// - NotebookLM出力の整形
    /// - 解説動画用のテキスト調整
    ///
    /// APIキー未設定時やAPI呼び出し失敗時は入力テキストをそのまま返す（フォールバック）。
    /// 環境変数 GEMINI_API_KEY にAPIキーを設定すること。
    /// </remarks>
    public class CsvScriptCompletionPlugin
    {
        private static readonly HttpClient s_httpClient = new();

        private const string GeminiEndpoint =
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent";

        private const string CompletionPrompt =
            """
            あなたはYouTube解説動画の台本校正の専門家です。
            以下のテキストを校正・補完してください。

            【要件】
            1. 誤字脱字を修正
            2. 文体を統一（です・ます調）
            3. 不自然な表現を自然な説明文にリライト
            4. 元の内容・意味は維持

            【入力テキスト】
            {0}

            【出力】
            校正後のテキストのみを出力してください（説明不要）。
            """;

        private const string CorrectionPrompt =
            """
            以下のテキストの校正提案をしてください。
            修正箇所と理由を箇条書きで返してください。
            修正がない場合は「修正なし」と返してください。

            【テキスト】
            {0}
            """;

        public string Name => "CSV Script Completion";
        public string Description => "台本CSVテキストの補完・校正";

        /// <summary>
        /// 台本テキストを校正・補完する。
        /// Gemini APIで誤字修正・文体統一・自然なリライトを行う。
        /// </summary>
        public async Task<string> CompleteTextAsync(string inputText, CancellationToken cancellationToken = default)
        {
            var prompt = string.Format(CompletionPrompt, inputText);
            return await CallGeminiAsync(prompt, inputText, cancellationToken).ConfigureAwait(false);
        }

        /// <summary>
        /// 台本テキストの校正提案を返す。
        /// 修正箇所と理由を箇条書きで提示する。
        /// </summary>
        public async Task<string> SuggestCorrectionsAsync(string inputText, CancellationToken cancellationToken = default)
        {
            var prompt = string.Format(CorrectionPrompt, inputText);
            return await CallGeminiAsync(prompt, inputText, cancellationToken).ConfigureAwait(false);
        }

        /// <summary>
        /// Gemini REST APIを呼び出す共通メソッド。
        /// APIキー未設定・通信エラー時はfallbackTextを返す。
        /// </summary>
        internal async Task<string> CallGeminiAsync(string prompt, string fallbackText, CancellationToken cancellationToken)
        {
            var apiKey = Environment.GetEnvironmentVariable("GEMINI_API_KEY");
            if (string.IsNullOrEmpty(apiKey))
            {
                return fallbackText;
            }

            try
            {
                var url = $"{GeminiEndpoint}?key={apiKey}";
                var requestBody = new
                {
                    contents = new[]
                    {
                        new
                        {
                            parts = new[]
                            {
                                new { text = prompt }
                            }
                        }
                    }
                };

                var json = JsonSerializer.Serialize(requestBody);
                using var content = new StringContent(json, Encoding.UTF8, "application/json");
                using var response = await s_httpClient.PostAsync(url, content, cancellationToken).ConfigureAwait(false);

                if (!response.IsSuccessStatusCode)
                {
                    return fallbackText;
                }

                var responseJson = await response.Content.ReadAsStringAsync(cancellationToken).ConfigureAwait(false);
                using var doc = JsonDocument.Parse(responseJson);

                var text = doc.RootElement
                    .GetProperty("candidates")[0]
                    .GetProperty("content")
                    .GetProperty("parts")[0]
                    .GetProperty("text")
                    .GetString();

                return text ?? fallbackText;
            }
            catch (Exception) when (!cancellationToken.IsCancellationRequested)
            {
                return fallbackText;
            }
        }
    }
}

using System;
using System.Threading;
using System.Threading.Tasks;
using Xunit;
using NLMSlidePlugin.TextCompletionPlugin;

namespace NLMSlidePlugin.Tests
{
    /// <summary>
    /// CsvScriptCompletionPlugin のユニットテスト
    /// </summary>
    public class CsvScriptCompletionPluginTests
    {
        [Fact]
        public void Name_ReturnsExpectedValue()
        {
            var plugin = new CsvScriptCompletionPlugin();
            Assert.Equal("CSV Script Completion", plugin.Name);
        }

        [Fact]
        public void Description_ReturnsExpectedValue()
        {
            var plugin = new CsvScriptCompletionPlugin();
            Assert.Equal("台本CSVテキストの補完・校正", plugin.Description);
        }

        [Fact]
        public async Task CompleteTextAsync_NoApiKey_ReturnsFallback()
        {
            // APIキー未設定時は入力テキストをそのまま返す
            var original = Environment.GetEnvironmentVariable("GEMINI_API_KEY");
            try
            {
                Environment.SetEnvironmentVariable("GEMINI_API_KEY", null);
                var plugin = new CsvScriptCompletionPlugin();
                var input = "テスト入力テキスト";
                var result = await plugin.CompleteTextAsync(input);
                Assert.Equal(input, result);
            }
            finally
            {
                Environment.SetEnvironmentVariable("GEMINI_API_KEY", original);
            }
        }

        [Fact]
        public async Task SuggestCorrectionsAsync_NoApiKey_ReturnsFallback()
        {
            var original = Environment.GetEnvironmentVariable("GEMINI_API_KEY");
            try
            {
                Environment.SetEnvironmentVariable("GEMINI_API_KEY", null);
                var plugin = new CsvScriptCompletionPlugin();
                var input = "テスト入力テキスト";
                var result = await plugin.SuggestCorrectionsAsync(input);
                Assert.Equal(input, result);
            }
            finally
            {
                Environment.SetEnvironmentVariable("GEMINI_API_KEY", original);
            }
        }

        [Fact]
        public async Task CompleteTextAsync_CancelledToken_ThrowsOperationCancelled()
        {
            // APIキーがある場合のみHTTP呼び出しが発生し、キャンセルが効く
            var original = Environment.GetEnvironmentVariable("GEMINI_API_KEY");
            try
            {
                Environment.SetEnvironmentVariable("GEMINI_API_KEY", "dummy-key-for-test");
                var plugin = new CsvScriptCompletionPlugin();
                using var cts = new CancellationTokenSource();
                cts.Cancel();
                await Assert.ThrowsAnyAsync<OperationCanceledException>(
                    () => plugin.CompleteTextAsync("テスト", cts.Token));
            }
            finally
            {
                Environment.SetEnvironmentVariable("GEMINI_API_KEY", original);
            }
        }

        [Fact]
        public async Task CompleteTextAsync_InvalidApiKey_ReturnsFallback()
        {
            // 無効なAPIキーの場合、API呼び出しは失敗しフォールバックが返る
            var original = Environment.GetEnvironmentVariable("GEMINI_API_KEY");
            try
            {
                Environment.SetEnvironmentVariable("GEMINI_API_KEY", "invalid-key");
                var plugin = new CsvScriptCompletionPlugin();
                var input = "テスト入力";
                var result = await plugin.CompleteTextAsync(input);
                Assert.Equal(input, result);
            }
            finally
            {
                Environment.SetEnvironmentVariable("GEMINI_API_KEY", original);
            }
        }
    }
}

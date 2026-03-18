"""LLMプロバイダー抽象化テスト (SP-043)"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from core.llm_provider import (
    ILLMProvider,
    MockLLMProvider,
    OpenAILLMProvider,
    ClaudeLLMProvider,
    GeminiLLMProvider,
    DeepSeekLLMProvider,
    create_llm_provider,
)


class TestMockProvider:
    @pytest.mark.asyncio
    async def test_generate_text(self) -> None:
        provider = MockLLMProvider()
        result = await provider.generate_text("test prompt")
        assert "Mock LLM response" in result
        assert "test prompt" in result

    def test_model_name(self) -> None:
        provider = MockLLMProvider(model="test-model")
        assert provider.model_name == "test-model"

    def test_implements_protocol(self) -> None:
        provider = MockLLMProvider()
        assert isinstance(provider, ILLMProvider)


class TestOpenAIProvider:
    def test_init_with_key(self) -> None:
        provider = OpenAILLMProvider(api_key="test-key", model="gpt-4o")
        assert provider.api_key == "test-key"
        assert provider.model_name == "gpt-4o"

    def test_init_default_model(self) -> None:
        provider = OpenAILLMProvider(api_key="key")
        assert provider.model_name == "gpt-4o-mini"

    def test_implements_protocol(self) -> None:
        provider = OpenAILLMProvider(api_key="key")
        assert isinstance(provider, ILLMProvider)

    @pytest.mark.asyncio
    async def test_generate_text_calls_api(self) -> None:
        provider = OpenAILLMProvider(api_key="test-key")

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Generated text"

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        provider._client = mock_client

        result = await provider.generate_text("prompt", system_prompt="system")
        assert result == "Generated text"

        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"


class TestClaudeProvider:
    def test_init_with_key(self) -> None:
        provider = ClaudeLLMProvider(api_key="test-key", model="claude-sonnet-4-6")
        assert provider.api_key == "test-key"
        assert provider.model_name == "claude-sonnet-4-6"

    def test_init_default_model(self) -> None:
        provider = ClaudeLLMProvider(api_key="key")
        assert provider.model_name == "claude-haiku-4-5-20251001"

    def test_implements_protocol(self) -> None:
        provider = ClaudeLLMProvider(api_key="key")
        assert isinstance(provider, ILLMProvider)

    @pytest.mark.asyncio
    async def test_generate_text_calls_api(self) -> None:
        provider = ClaudeLLMProvider(api_key="test-key")

        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = "Claude response"

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        provider._client = mock_client

        result = await provider.generate_text("prompt", system_prompt="system")
        assert result == "Claude response"

        call_args = mock_client.messages.create.call_args
        assert call_args.kwargs["system"] == "system"


class TestDeepSeekProvider:
    def test_init_with_key(self) -> None:
        provider = DeepSeekLLMProvider(api_key="test-key")
        assert provider.api_key == "test-key"
        assert provider.model_name == "deepseek-chat"

    def test_implements_protocol(self) -> None:
        provider = DeepSeekLLMProvider(api_key="key")
        assert isinstance(provider, ILLMProvider)


class TestGeminiProvider:
    def test_init_with_key(self) -> None:
        provider = GeminiLLMProvider(api_key="test-key")
        assert provider.api_key == "test-key"
        assert provider.model_name == "gemini-2.5-flash"

    def test_implements_protocol(self) -> None:
        provider = GeminiLLMProvider(api_key="key")
        assert isinstance(provider, ILLMProvider)


class TestFactory:
    def test_create_mock(self) -> None:
        provider = create_llm_provider(provider="mock")
        assert isinstance(provider, MockLLMProvider)

    def test_create_openai(self) -> None:
        provider = create_llm_provider(provider="openai", api_key="test")
        assert isinstance(provider, OpenAILLMProvider)

    def test_create_claude(self) -> None:
        provider = create_llm_provider(provider="claude", api_key="test")
        assert isinstance(provider, ClaudeLLMProvider)

    def test_create_gemini(self) -> None:
        provider = create_llm_provider(provider="gemini", api_key="test")
        assert isinstance(provider, GeminiLLMProvider)

    def test_create_deepseek(self) -> None:
        provider = create_llm_provider(provider="deepseek", api_key="test")
        assert isinstance(provider, DeepSeekLLMProvider)

    def test_unknown_provider_falls_back_to_mock(self) -> None:
        provider = create_llm_provider(provider="unknown")
        assert isinstance(provider, MockLLMProvider)

    def test_env_var_provider(self) -> None:
        with patch.dict("os.environ", {"LLM_PROVIDER": "mock"}):
            provider = create_llm_provider()
            assert isinstance(provider, MockLLMProvider)

    def test_env_var_model(self) -> None:
        with patch.dict("os.environ", {"LLM_PROVIDER": "mock", "LLM_MODEL": "test-model"}):
            provider = create_llm_provider()
            assert provider.model_name == "test-model"

    def test_custom_model_override(self) -> None:
        provider = create_llm_provider(provider="openai", model="gpt-4o", api_key="test")
        assert provider.model_name == "gpt-4o"

    def test_api_key_override(self) -> None:
        provider = create_llm_provider(provider="openai", api_key="custom-key")
        assert provider.api_key == "custom-key"

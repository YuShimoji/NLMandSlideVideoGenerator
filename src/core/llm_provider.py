"""マルチLLMプロバイダー抽象化 (SP-043)

Gemini / OpenAI / Claude / DeepSeek 等の LLM API を統一インターフェースで利用可能にする。
.env の LLM_PROVIDER / LLM_MODEL / LLM_API_KEY で切替。
"""
from __future__ import annotations

import asyncio
import os
from typing import Optional, Protocol, runtime_checkable

from core.utils.logger import logger


@runtime_checkable
class ILLMProvider(Protocol):
    """LLM プロバイダーの共通インターフェース。"""

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        """テキスト生成。"""
        ...

    @property
    def model_name(self) -> str:
        """使用中のモデル名。"""
        ...


class OpenAILLMProvider:
    """OpenAI API (gpt-4o-mini / gpt-4o) プロバイダー。"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self._model = model
        self._client = None

    @property
    def model_name(self) -> str:
        return self._model

    def _ensure_client(self) -> None:
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=self.api_key)

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        self._ensure_client()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content or ""


class ClaudeLLMProvider:
    """Anthropic Claude API (claude-haiku-4-5 / claude-sonnet-4-6) プロバイダー。"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-haiku-4-5-20251001",
    ) -> None:
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self._model = model
        self._client = None

    @property
    def model_name(self) -> str:
        return self._model

    def _ensure_client(self) -> None:
        if self._client is None:
            from anthropic import AsyncAnthropic
            self._client = AsyncAnthropic(api_key=self.api_key)

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        self._ensure_client()
        kwargs = {
            "model": self._model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        response = await self._client.messages.create(**kwargs)
        return response.content[0].text if response.content else ""


class GeminiLLMProvider:
    """Google Gemini API (gemini-2.5-flash) プロバイダー。"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-2.5-flash",
    ) -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self._model = model
        self._client = None

    @property
    def model_name(self) -> str:
        return self._model

    def _ensure_client(self) -> None:
        if self._client is None:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        self._ensure_client()
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        try:
            response = await asyncio.to_thread(
                self._client.models.generate_content,
                model=self._model,
                contents=full_prompt,
            )
            return response.text or ""
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return ""


class DeepSeekLLMProvider:
    """DeepSeek API (OpenAI互換) プロバイダー。"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "deepseek-chat",
    ) -> None:
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
        self._model = model
        self._client = None

    @property
    def model_name(self) -> str:
        return self._model

    def _ensure_client(self) -> None:
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url="https://api.deepseek.com",
            )

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        self._ensure_client()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content or ""


class MockLLMProvider:
    """テスト・フォールバック用のモックプロバイダー。"""

    def __init__(self, model: str = "mock") -> None:
        self._model = model

    @property
    def model_name(self) -> str:
        return self._model

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        return f"[Mock LLM response for: {prompt[:50]}...]"


# --- ファクトリ ---

_PROVIDERS = {
    "openai": OpenAILLMProvider,
    "claude": ClaudeLLMProvider,
    "gemini": GeminiLLMProvider,
    "deepseek": DeepSeekLLMProvider,
    "mock": MockLLMProvider,
}

_DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "claude": "claude-haiku-4-5-20251001",
    "gemini": "gemini-2.5-flash",
    "deepseek": "deepseek-chat",
    "mock": "mock",
}


def create_llm_provider(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
) -> ILLMProvider:
    """環境変数またはパラメータから LLM プロバイダーを生成する。

    優先順位: パラメータ > 環境変数 > デフォルト (gemini)

    Args:
        provider: プロバイダー名 (openai/claude/gemini/deepseek/mock)
        model: モデル名
        api_key: API キー

    Returns:
        ILLMProvider 実装のインスタンス
    """
    provider_name = provider or os.getenv("LLM_PROVIDER", "gemini")
    provider_name = provider_name.lower().strip()

    if provider_name not in _PROVIDERS:
        logger.warning(f"Unknown LLM provider '{provider_name}', falling back to mock")
        provider_name = "mock"

    model_name = model or os.getenv("LLM_MODEL", _DEFAULT_MODELS.get(provider_name, ""))
    key = api_key or os.getenv("LLM_API_KEY", "")

    provider_class = _PROVIDERS[provider_name]

    if provider_name == "mock":
        return provider_class(model=model_name)

    kwargs = {"model": model_name}
    if key:
        kwargs["api_key"] = key

    instance = provider_class(**kwargs)
    logger.info(f"LLM Provider: {provider_name} ({model_name})")
    return instance

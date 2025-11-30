#!/usr/bin/env python3
"""
テスト: Script Provider コンポーネントテスト
OpenSpec IScriptProviderの実装を検証
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path
import sys

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from src.core.providers.script.gemini_provider import GeminiScriptProvider
from notebook_lm.source_collector import SourceInfo

class TestGeminiScriptProvider:
    """GeminiScriptProviderのテスト"""

    @pytest.fixture
    def mock_gemini_client(self):
        """GeminiIntegrationのモック"""
        mock_client = Mock()
        mock_script_info = Mock()
        mock_script_info.title = "テストタイトル"
        mock_script_info.content = "テストコンテンツ"
        mock_script_info.segments = []
        mock_client.generate_script_from_sources = AsyncMock(return_value=mock_script_info)
        return mock_client

    @pytest.fixture
    def provider(self, mock_gemini_client):
        """テスト用のプロバイダーインスタンス（モック使用）"""
        with patch('src.core.providers.script.gemini_provider.GeminiIntegration', return_value=mock_gemini_client):
            provider = GeminiScriptProvider()
            provider.api_key = "test_api_key"  # モック用APIキー
            provider.client = mock_gemini_client
            return provider

    @pytest.fixture
    def mock_sources(self):
        """モックソースデータ"""
        return [
            SourceInfo(
                url="https://example.com/article1",
                title="Test Article 1",
                content_preview="This is test content 1",
                relevance_score=0.9,
                reliability_score=0.8,
                source_type="article"
            ),
            SourceInfo(
                url="https://example.com/article2",
                title="Test Article 2",
                content_preview="This is test content 2",
                relevance_score=0.7,
                reliability_score=0.9,
                source_type="news"
            )
        ]

    @pytest.mark.asyncio
    async def test_generate_script_basic(self, provider, mock_sources):
        """基本的なスクリプト生成テスト"""
        topic = "AI技術の最新動向"
        
        result = await provider.generate_script(topic, mock_sources)
        
        assert isinstance(result, dict)
        assert 'title' in result
        assert 'content' in result
        assert 'segments' in result

    @pytest.mark.asyncio
    async def test_generate_script_with_mode(self, provider, mock_sources):
        """モード指定でのスクリプト生成テスト"""
        topic = "機械学習の基礎"
        
        for mode in ['auto', 'assist', 'manual']:
            result = await provider.generate_script(topic, mock_sources, mode)
            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_generate_script_empty_sources(self, provider):
        """空のソースリストでのスクリプト生成テスト"""
        topic = "テストトピック"
        
        result = await provider.generate_script(topic, [])
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_generate_script_api_error(self, mock_gemini_client, mock_sources):
        """APIエラー時の処理テスト"""
        topic = "エラーテスト"
        mock_gemini_client.generate_script_from_sources = AsyncMock(side_effect=Exception("API Error"))
        
        with patch('src.core.providers.script.gemini_provider.GeminiIntegration', return_value=mock_gemini_client):
            provider = GeminiScriptProvider()
            provider.api_key = "test_api_key"
            provider.client = mock_gemini_client
            
            with pytest.raises(Exception):
                await provider.generate_script(topic, mock_sources)

    def test_provider_initialization(self, provider):
        """プロバイダーの初期化テスト"""
        assert provider is not None
        assert hasattr(provider, 'generate_script')

    @pytest.mark.asyncio
    async def test_script_structure(self, provider, mock_sources):
        """生成されるスクリプトの構造テスト"""
        topic = "構造テスト"
        
        result = await provider.generate_script(topic, mock_sources)
        
        assert isinstance(result, dict)
        assert 'title' in result

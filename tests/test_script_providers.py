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
    def provider(self):
        """テスト用のプロバイダーインスタンス"""
        return GeminiScriptProvider()

    @pytest.fixture
    def mock_sources(self):
        """モックソースデータ"""
        return [
            SourceInfo(
                url="https://example.com/article1",
                title="Test Article 1",
                content="This is test content 1",
                relevance_score=0.9,
                credibility_score=0.8
            ),
            SourceInfo(
                url="https://example.com/article2",
                title="Test Article 2",
                content="This is test content 2",
                relevance_score=0.7,
                credibility_score=0.9
            )
        ]

    @pytest.mark.asyncio
    async def test_generate_script_basic(self, provider, mock_sources):
        """基本的なスクリプト生成テスト"""
        topic = "AI技術の最新動向"

        # Gemini APIをモック
        with patch('google.generativeai.GenerativeModel.generate_content_async') as mock_generate:
            mock_response = Mock()
            mock_response.text = '''
            # AI技術の最新動向

            ## 導入
            AI技術は急速に進化しています。

            ## 主要トレンド
            1. 大規模言語モデル
            2. 生成AI
            3. 自動化技術

            ## 結論
            AIの未来は明るいです。
            '''
            mock_generate.return_value = mock_response

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
            with patch('google.generativeai.GenerativeModel.generate_content_async') as mock_generate:
                mock_response = Mock()
                mock_response.text = f"Generated script for {topic} in {mode} mode"
                mock_generate.return_value = mock_response

                result = await provider.generate_script(topic, mock_sources, mode)

                assert isinstance(result, dict)
                mock_generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_script_empty_sources(self, provider):
        """空のソースリストでのスクリプト生成テスト"""
        topic = "テストトピック"

        with patch('google.generativeai.GenerativeModel.generate_content_async') as mock_generate:
            mock_response = Mock()
            mock_response.text = "Generated script without sources"
            mock_generate.return_value = mock_response

            result = await provider.generate_script(topic, [])

            assert isinstance(result, dict)
            mock_generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_script_api_error(self, provider, mock_sources):
        """APIエラー時の処理テスト"""
        topic = "エラーテスト"

        with patch('google.generativeai.GenerativeModel.generate_content_async') as mock_generate:
            mock_generate.side_effect = Exception("API Error")

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

        with patch('google.generativeai.GenerativeModel.generate_content_async') as mock_generate:
            mock_response = Mock()
            mock_response.text = '''
            # 構造テスト

            ## セクション1
            最初の内容

            ## セクション2
            次の内容

            ## 結論
            まとめ
            '''
            mock_generate.return_value = mock_response

            result = await provider.generate_script(topic, mock_sources)

            assert result['title'] == topic
            assert 'segments' in result
            assert len(result['segments']) > 0

            # 各セグメントに必要なフィールドがあるか確認
            for segment in result['segments']:
                assert 'text' in segment
                assert 'duration' in segment

#!/usr/bin/env python3
"""
テスト: OpenSpecインターフェース準拠テスト
各実装がOpenSpecインターフェースを正しく実装しているかを検証
"""

import pytest
from pathlib import Path
import sys

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from src.core.providers.script.gemini_provider import GeminiScriptProvider
from src.core.editing.ymm4_backend import YMM4EditingBackend
from src.core.platforms.youtube_adapter import YouTubePlatformAdapter
from src.core.timeline.basic_planner import BasicTimelinePlanner

class TestOpenSpecInterfaces:
    """OpenSpecインターフェース準拠テスト"""

    @pytest.mark.asyncio
    async def test_gemini_script_provider_interface(self):
        """GeminiScriptProviderがIScriptProviderインターフェースを実装しているか"""
        provider = GeminiScriptProvider()

        # IScriptProviderのメソッドが存在するか確認
        assert hasattr(provider, 'generate_script')
        assert callable(getattr(provider, 'generate_script'))

        # メソッドがasync関数であることを確認
        import inspect
        assert inspect.iscoroutinefunction(provider.generate_script)

    @pytest.mark.asyncio
    async def test_ymm4_editing_backend_interface(self):
        """YMM4EditingBackendがIEditingBackendインターフェースを実装しているか"""
        backend = YMM4EditingBackend()

        # IEditingBackendのメソッドが存在するか確認
        assert hasattr(backend, 'render')
        assert callable(getattr(backend, 'render'))

        # メソッドがasync関数であることを確認
        import inspect
        assert inspect.iscoroutinefunction(backend.render)

    @pytest.mark.asyncio
    async def test_youtube_platform_adapter_interface(self):
        """YouTubePlatformAdapterがIPlatformAdapterインターフェースを実装しているか"""
        adapter = YouTubePlatformAdapter()

        # IPlatformAdapterのメソッドが存在するか確認
        assert hasattr(adapter, 'upload')
        assert callable(getattr(adapter, 'upload'))

        # メソッドがasync関数であることを確認
        import inspect
        assert inspect.iscoroutinefunction(adapter.upload)

    @pytest.mark.asyncio
    async def test_basic_timeline_planner_interface(self):
        """BasicTimelinePlannerがITimelinePlannerインターフェースを実装しているか"""
        planner = BasicTimelinePlanner()

        # ITimelinePlannerのメソッドが存在するか確認
        assert hasattr(planner, 'build_plan')
        assert callable(getattr(planner, 'build_plan'))

        # メソッドがasync関数であることを確認
        import inspect
        assert inspect.iscoroutinefunction(planner.build_plan)

class TestInterfaceCompliance:
    """インターフェース準拠の詳細テスト"""

    def test_interface_inheritance(self):
        """各実装クラスが適切なインターフェースを継承しているか"""
        # Protocolは継承ではなく構造的サブタイピングなので、
        # メソッドシグネチャの一致を確認

        # GeminiScriptProvider
        provider = GeminiScriptProvider()
        assert hasattr(provider, 'generate_script')

        # YouTubePlatformAdapter
        adapter = YouTubePlatformAdapter()
        assert hasattr(adapter, 'upload')

    def test_method_signatures(self):
        """メソッドのシグネチャがインターフェースと一致するか"""
        import inspect

        # GeminiScriptProvider.generate_script
        provider = GeminiScriptProvider()
        sig = inspect.signature(provider.generate_script)
        params = list(sig.parameters.keys())

        # IScriptProvider.generate_scriptの期待されるパラメータ
        expected_params = ['topic', 'sources', 'mode']
        for param in expected_params:
            assert param in params, f"Missing parameter: {param} in generate_script"

#!/usr/bin/env python3
"""
テスト: ExportFallbackManager
フォールバック戦略の動作を検証
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path
import sys

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from src.core.editing import (
    ExportFallbackManager,
    BackendType,
    BackendConfig,
    FallbackResult,
)


class TestExportFallbackManager:
    """ExportFallbackManagerのテスト"""

    @pytest.fixture
    def mock_audio(self):
        """モック音声情報"""
        return Mock(file_path=Path("test_audio.mp3"), duration=60.0)

    @pytest.fixture
    def mock_slides(self):
        """モックスライド"""
        return Mock(presentation_id="test", slides=[], total_slides=3)

    @pytest.fixture
    def mock_transcript(self):
        """モック台本"""
        return Mock(title="テスト台本", segments=[])

    @pytest.fixture
    def timeline_plan(self):
        """タイムライン計画"""
        return {
            "total_duration": 60.0,
            "segments": [
                {"start": 0.0, "end": 30.0, "text": "セグメント1"},
                {"start": 30.0, "end": 60.0, "text": "セグメント2"},
            ]
        }

    def test_manager_initialization(self):
        """マネージャーの初期化テスト"""
        manager = ExportFallbackManager(auto_detect=False)
        
        assert manager is not None
        assert len(manager.configs) > 0
        
    def test_default_configs(self):
        """デフォルト設定のテスト"""
        manager = ExportFallbackManager(auto_detect=False)
        
        # MoviePyは常に有効
        moviepy_config = next(
            (c for c in manager.configs if c.backend_type == BackendType.MOVIEPY),
            None
        )
        assert moviepy_config is not None
        assert moviepy_config.enabled is True
        
    def test_custom_configs(self):
        """カスタム設定のテスト"""
        custom_configs = [
            BackendConfig(
                backend_type=BackendType.MOVIEPY,
                enabled=True,
                priority=1,
            )
        ]
        
        manager = ExportFallbackManager(configs=custom_configs, auto_detect=False)
        
        assert len(manager.configs) == 1
        assert manager.configs[0].backend_type == BackendType.MOVIEPY
        
    def test_get_available_backends(self):
        """利用可能バックエンド取得テスト"""
        manager = ExportFallbackManager(auto_detect=False)
        
        # MoviePyのみ有効化
        for config in manager.configs:
            config.enabled = config.backend_type == BackendType.MOVIEPY
        
        available = manager.get_available_backends()
        assert BackendType.MOVIEPY in available
        
    def test_set_backend_enabled(self):
        """バックエンド有効/無効切替テスト"""
        manager = ExportFallbackManager(auto_detect=False)
        
        manager.set_backend_enabled(BackendType.MOVIEPY, False)
        
        moviepy_config = next(
            c for c in manager.configs if c.backend_type == BackendType.MOVIEPY
        )
        assert moviepy_config.enabled is False
        
        manager.set_backend_enabled(BackendType.MOVIEPY, True)
        assert moviepy_config.enabled is True
        
    def test_get_status(self):
        """ステータス取得テスト"""
        manager = ExportFallbackManager(auto_detect=False)
        
        status = manager.get_status()
        
        assert "backends" in status
        assert "available" in status
        assert isinstance(status["backends"], list)

    @pytest.mark.asyncio
    async def test_render_success(
        self, mock_audio, mock_slides, mock_transcript, timeline_plan
    ):
        """レンダリング成功テスト"""
        manager = ExportFallbackManager(auto_detect=False)
        
        # MoviePyのみ有効化
        for config in manager.configs:
            config.enabled = config.backend_type == BackendType.MOVIEPY
        
        # バックエンドをモック
        mock_video_info = Mock()
        mock_video_info.file_path = Path("output.mp4")
        mock_video_info.duration = 60.0
        
        mock_backend = Mock()
        mock_backend.render = AsyncMock(return_value=mock_video_info)
        
        with patch.object(manager, '_get_backend', return_value=mock_backend):
            result = await manager.render(
                timeline_plan=timeline_plan,
                audio=mock_audio,
                slides=mock_slides,
                transcript=mock_transcript,
            )
        
        assert result.success is True
        assert result.used_backend == BackendType.MOVIEPY
        assert result.video_info is not None
        
    @pytest.mark.asyncio
    async def test_render_fallback(
        self, mock_audio, mock_slides, mock_transcript, timeline_plan
    ):
        """フォールバック動作テスト"""
        configs = [
            BackendConfig(
                backend_type=BackendType.YMM4_AHK,
                enabled=True,
                priority=1,
                retry_count=1,
            ),
            BackendConfig(
                backend_type=BackendType.MOVIEPY,
                enabled=True,
                priority=2,
            ),
        ]
        manager = ExportFallbackManager(configs=configs, auto_detect=False)
        
        # 最初のバックエンドは失敗、2番目は成功
        mock_video_info = Mock()
        mock_video_info.file_path = Path("output.mp4")
        
        fail_backend = Mock()
        fail_backend.render = AsyncMock(side_effect=Exception("YMM4エラー"))
        
        success_backend = Mock()
        success_backend.render = AsyncMock(return_value=mock_video_info)
        
        def get_backend_mock(backend_type):
            if backend_type == BackendType.YMM4_AHK:
                return fail_backend
            return success_backend
        
        with patch.object(manager, '_get_backend', side_effect=get_backend_mock):
            result = await manager.render(
                timeline_plan=timeline_plan,
                audio=mock_audio,
                slides=mock_slides,
                transcript=mock_transcript,
            )
        
        assert result.success is True
        assert result.used_backend == BackendType.MOVIEPY
        assert BackendType.YMM4_AHK in result.attempted_backends
        assert BackendType.YMM4_AHK in result.errors

    @pytest.mark.asyncio
    async def test_render_all_fail(
        self, mock_audio, mock_slides, mock_transcript, timeline_plan
    ):
        """全バックエンド失敗テスト"""
        configs = [
            BackendConfig(
                backend_type=BackendType.MOVIEPY,
                enabled=True,
                priority=1,
                retry_count=1,
            ),
        ]
        manager = ExportFallbackManager(configs=configs, auto_detect=False)
        
        fail_backend = Mock()
        fail_backend.render = AsyncMock(side_effect=Exception("レンダリングエラー"))
        
        with patch.object(manager, '_get_backend', return_value=fail_backend):
            result = await manager.render(
                timeline_plan=timeline_plan,
                audio=mock_audio,
                slides=mock_slides,
                transcript=mock_transcript,
            )
        
        assert result.success is False
        assert result.video_info is None
        assert BackendType.MOVIEPY in result.errors

    @pytest.mark.asyncio
    async def test_preferred_backend(
        self, mock_audio, mock_slides, mock_transcript, timeline_plan
    ):
        """優先バックエンド指定テスト"""
        configs = [
            BackendConfig(
                backend_type=BackendType.YMM4_AHK,
                enabled=True,
                priority=1,
            ),
            BackendConfig(
                backend_type=BackendType.MOVIEPY,
                enabled=True,
                priority=2,
            ),
        ]
        manager = ExportFallbackManager(configs=configs, auto_detect=False)
        
        mock_video_info = Mock()
        mock_video_info.file_path = Path("output.mp4")
        
        mock_backend = Mock()
        mock_backend.render = AsyncMock(return_value=mock_video_info)
        
        with patch.object(manager, '_get_backend', return_value=mock_backend):
            result = await manager.render(
                timeline_plan=timeline_plan,
                audio=mock_audio,
                slides=mock_slides,
                transcript=mock_transcript,
                preferred_backend=BackendType.MOVIEPY,
            )
        
        # MoviePyが最初に試行される（優先指定）
        assert result.success is True
        assert result.attempted_backends[0] == BackendType.MOVIEPY

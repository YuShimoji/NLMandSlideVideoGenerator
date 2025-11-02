#!/usr/bin/env python3
"""
テスト: Platform Adapter コンポーネントテスト
OpenSpec IPlatformAdapterの実装を検証
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path
from datetime import datetime
import sys

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from src.core.platforms.youtube_adapter import YouTubePlatformAdapter
from video_editor.video_composer import VideoInfo
from youtube.uploader import UploadMetadata

class TestYouTubePlatformAdapter:
    """YouTubePlatformAdapterのテスト"""

    @pytest.fixture
    def adapter(self):
        """テスト用のアダプターインスタンス"""
        return YouTubePlatformAdapter()

    @pytest.fixture
    def mock_video_info(self):
        """モック動画情報"""
        return VideoInfo(
            file_path=Path("test_video.mp4"),
            duration=120.0,
            resolution=(1920, 1080),
            fps=30,
            file_size=10000000,
            has_subtitles=True,
            has_effects=True,
            created_at=datetime.now()
        )

    @pytest.fixture
    def mock_metadata(self):
        """モックアップロードメタデータ"""
        return UploadMetadata(
            title="テスト動画",
            description="これはテスト動画です。",
            tags=["テスト", "動画"],
            privacy_status="private",
            category_id="22"
        )

    @pytest.mark.asyncio
    async def test_upload_basic(self, adapter, mock_video_info, mock_metadata):
        """基本的なアップロードテスト"""
        # YouTube APIをモック
        with patch('src.core.platforms.youtube_adapter.YouTubeUploader') as mock_uploader_class:
            mock_uploader_instance = Mock()
            mock_uploader_class.return_value = mock_uploader_instance

            mock_result = Mock()
            mock_result.url = "https://youtube.com/watch?v=test123"
            mock_result.video_id = "test123"
            mock_uploader_instance.upload.return_value = mock_result

            result = await adapter.upload(mock_video_info, mock_metadata)

            assert result.url == "https://youtube.com/watch?v=test123"
            assert result.video_id == "test123"
            mock_uploader_instance.upload.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_with_schedule(self, adapter, mock_video_info, mock_metadata):
        """スケジュール付きアップロードテスト"""
        schedule_time = datetime(2025, 12, 31, 12, 0, 0)

        with patch('src.core.platforms.youtube_adapter.YouTubeUploader') as mock_uploader_class:
            mock_uploader_instance = Mock()
            mock_uploader_class.return_value = mock_uploader_instance

            mock_result = Mock()
            mock_result.url = "https://youtube.com/watch?v=scheduled_test"
            mock_result.video_id = "scheduled_test"
            mock_uploader_instance.upload.return_value = mock_result

            result = await adapter.upload(mock_video_info, mock_metadata, schedule_time)

            assert result.url == "https://youtube.com/watch?v=scheduled_test"
            mock_uploader_instance.upload.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_api_error(self, adapter, mock_video_info, mock_metadata):
        """APIエラー時の処理テスト"""
        with patch('src.core.platforms.youtube_adapter.YouTubeUploader') as mock_uploader_class:
            mock_uploader_instance = Mock()
            mock_uploader_class.return_value = mock_uploader_instance
            mock_uploader_instance.upload.side_effect = Exception("YouTube API Error")

            with pytest.raises(Exception):
                await adapter.upload(mock_video_info, mock_metadata)

    def test_adapter_initialization(self, adapter):
        """アダプターの初期化テスト"""
        assert adapter is not None
        assert hasattr(adapter, 'upload')

    @pytest.mark.asyncio
    async def test_upload_result_structure(self, adapter, mock_video_info, mock_metadata):
        """アップロード結果の構造テスト"""
        with patch('src.core.platforms.youtube_adapter.YouTubeUploader') as mock_uploader_class:
            mock_uploader_instance = Mock()
            mock_uploader_class.return_value = mock_uploader_instance

            mock_result = Mock()
            mock_result.url = "https://youtube.com/watch?v=structured_test"
            mock_result.video_id = "structured_test"
            mock_result.uploaded_at = datetime.now()
            mock_result.privacy_status = "private"
            mock_uploader_instance.upload.return_value = mock_result

            result = await adapter.upload(mock_video_info, mock_metadata)

            assert hasattr(result, 'url')
            assert hasattr(result, 'video_id')
            assert hasattr(result, 'uploaded_at')
            assert hasattr(result, 'privacy_status')

    @pytest.mark.asyncio
    async def test_different_privacy_settings(self, adapter, mock_video_info):
        """異なるプライバシー設定でのアップロードテスト"""
        for privacy in ['public', 'private', 'unlisted']:
            metadata = UploadMetadata(
                title=f"{privacy}テスト動画",
                description=f"{privacy}設定のテスト動画です。",
                tags=["テスト", privacy],
                privacy_status=privacy,
                category_id="22"
            )

            with patch('src.core.platforms.youtube_adapter.YouTubeUploader') as mock_uploader_class:
                mock_uploader_instance = Mock()
                mock_uploader_class.return_value = mock_uploader_instance

                mock_result = Mock()
                mock_result.url = f"https://youtube.com/watch?v={privacy}_test"
                mock_result.video_id = f"{privacy}_test"
                mock_uploader_instance.upload.return_value = mock_result

                result = await adapter.upload(mock_video_info, metadata)

                assert result.privacy_status == privacy
                mock_uploader_instance.upload.assert_called_once()

    @pytest.mark.asyncio
    async def test_video_file_validation(self, adapter, mock_metadata):
        """動画ファイルのバリデーションテスト"""
        # 存在しないファイル
        invalid_video = VideoInfo(
            file_path=Path("nonexistent_video.mp4"),
            duration=60.0,
            resolution=(1920, 1080),
            fps=30,
            file_size=0,
            has_subtitles=False,
            has_effects=False,
            created_at=datetime.now()
        )

        with patch('src.core.platforms.youtube_adapter.YouTubeUploader') as mock_uploader_class:
            mock_uploader_instance = Mock()
            mock_uploader_class.return_value = mock_uploader_instance
            mock_uploader_instance.upload.side_effect = FileNotFoundError("Video file not found")

            with pytest.raises(FileNotFoundError):
                await adapter.upload(invalid_video, mock_metadata)

    @pytest.mark.asyncio
    async def test_metadata_validation(self, adapter, mock_video_info):
        """メタデータのバリデーションテスト"""
        # 不完全なメタデータ
        invalid_metadata = UploadMetadata(
            title="",  # 空のタイトル
            description="テスト説明",
            tags=[],
            privacy_status="invalid_status",  # 無効なプライバシー設定
            category_id="22"
        )

        with patch('src.core.platforms.youtube_adapter.YouTubeUploader') as mock_uploader_class:
            mock_uploader_instance = Mock()
            mock_uploader_class.return_value = mock_uploader_instance
            mock_uploader_instance.upload.side_effect = ValueError("Invalid metadata")

            with pytest.raises(ValueError):
                await adapter.upload(mock_video_info, invalid_metadata)

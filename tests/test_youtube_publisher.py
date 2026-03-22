"""YouTubePublisher (Phase 7 統合オーケストレーター) のテスト。

SP-038 Phase 7: MP4品質検証 → メタデータ → YouTube公開 → 結果永続化
"""
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from youtube.publisher import PublishOptions, PublishResult, YouTubePublisher
from youtube.uploader import UploadResult


# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture
def tmp_topic_dir(tmp_path: Path) -> Path:
    """トピックディレクトリ構造を作成"""
    topic_dir = tmp_path / "data" / "topics" / "test_topic"
    (topic_dir / "output_csv").mkdir(parents=True)
    (topic_dir / "final").mkdir(parents=True)

    # metadata.json
    metadata = {
        "title": "テスト動画タイトル",
        "description": "テスト概要",
        "tags": ["test", "demo"],
        "category_id": "22",
        "language": "ja",
    }
    (topic_dir / "output_csv" / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False), encoding="utf-8"
    )

    # thumbnail
    (topic_dir / "final" / "thumbnail.png").write_bytes(b"PNG_FAKE")

    return topic_dir


@pytest.fixture
def fake_mp4(tmp_path: Path) -> Path:
    """ダミーMP4ファイル"""
    mp4 = tmp_path / "video.mp4"
    mp4.write_bytes(b"\x00" * (2 * 1024 * 1024))  # 2MB
    return mp4


@pytest.fixture
def mock_upload_result() -> UploadResult:
    return UploadResult(
        video_id="test_vid_123",
        video_url="https://www.youtube.com/watch?v=test_vid_123",
        upload_status="uploaded",
        processing_status="processing",
        privacy_status="private",
    )


# ── PublishResult Tests ──────────────────────────────────────


class TestPublishResult:
    def test_to_dict(self):
        result = PublishResult(
            video_id="abc",
            video_url="https://youtube.com/watch?v=abc",
            upload_status="uploaded",
            privacy_status="private",
            quality_passed=True,
            quality_warnings=[],
            metadata_source="auto",
        )
        d = result.to_dict()
        assert d["video_id"] == "abc"
        assert d["quality_passed"] is True
        assert d["metadata_source"] == "auto"

    def test_to_dict_with_error(self):
        result = PublishResult(
            video_id="",
            video_url="",
            upload_status="failed",
            privacy_status="private",
            quality_passed=False,
            quality_warnings=["codec mismatch"],
            metadata_source="none",
            error="MP4品質検証で致命的エラー",
        )
        d = result.to_dict()
        assert d["error"] is not None
        assert len(d["quality_warnings"]) == 1


# ── PublishOptions Tests ──────────────────────────────────────


class TestPublishOptions:
    def test_defaults(self, fake_mp4: Path):
        opts = PublishOptions(video_path=fake_mp4)
        assert opts.privacy == "private"
        assert opts.verify_quality is True
        assert opts.save_result is True
        assert opts.topic_dir is None


# ── Metadata Loading Tests ──────────────────────────────────────


class TestMetadataLoading:
    def test_load_from_topic_dir(self, tmp_topic_dir: Path, fake_mp4: Path):
        publisher = YouTubePublisher()
        options = PublishOptions(
            video_path=fake_mp4,
            topic_dir=tmp_topic_dir,
        )
        metadata, source = publisher._load_metadata(options)
        assert metadata is not None
        assert source == "auto"
        assert metadata["title"] == "テスト動画タイトル"

    def test_load_from_explicit_path(self, tmp_path: Path, fake_mp4: Path):
        meta_path = tmp_path / "custom_meta.json"
        meta_path.write_text(
            json.dumps({"title": "Custom"}), encoding="utf-8"
        )
        publisher = YouTubePublisher()
        options = PublishOptions(
            video_path=fake_mp4,
            metadata_path=meta_path,
        )
        metadata, source = publisher._load_metadata(options)
        assert metadata is not None
        assert source == "file"
        assert metadata["title"] == "Custom"

    def test_load_from_video_sibling(self, tmp_path: Path):
        mp4 = tmp_path / "output" / "video.mp4"
        mp4.parent.mkdir(parents=True)
        mp4.write_bytes(b"\x00" * 1024)
        meta = tmp_path / "output" / "metadata.json"
        meta.write_text(json.dumps({"title": "Sibling"}), encoding="utf-8")

        publisher = YouTubePublisher()
        options = PublishOptions(video_path=mp4)
        metadata, source = publisher._load_metadata(options)
        assert metadata is not None
        assert source == "auto"
        assert metadata["title"] == "Sibling"

    def test_load_missing_returns_none(self, fake_mp4: Path):
        publisher = YouTubePublisher()
        options = PublishOptions(video_path=fake_mp4)
        metadata, source = publisher._load_metadata(options)
        assert metadata is None
        assert source == "none"

    def test_explicit_path_takes_priority(
        self, tmp_topic_dir: Path, tmp_path: Path, fake_mp4: Path
    ):
        """明示パスがトピックディレクトリより優先される"""
        explicit = tmp_path / "explicit.json"
        explicit.write_text(
            json.dumps({"title": "Explicit"}), encoding="utf-8"
        )
        publisher = YouTubePublisher()
        options = PublishOptions(
            video_path=fake_mp4,
            topic_dir=tmp_topic_dir,
            metadata_path=explicit,
        )
        metadata, source = publisher._load_metadata(options)
        assert metadata["title"] == "Explicit"
        assert source == "file"


# ── Thumbnail Resolution Tests ──────────────────────────────────


class TestThumbnailResolution:
    def test_auto_detect_from_topic_dir(
        self, tmp_topic_dir: Path, fake_mp4: Path
    ):
        publisher = YouTubePublisher()
        options = PublishOptions(
            video_path=fake_mp4, topic_dir=tmp_topic_dir
        )
        thumb = publisher._resolve_thumbnail(options)
        assert thumb is not None
        assert thumb.name == "thumbnail.png"

    def test_explicit_thumbnail_takes_priority(
        self, tmp_topic_dir: Path, tmp_path: Path, fake_mp4: Path
    ):
        explicit_thumb = tmp_path / "my_thumb.jpg"
        explicit_thumb.write_bytes(b"JPG")
        publisher = YouTubePublisher()
        options = PublishOptions(
            video_path=fake_mp4,
            topic_dir=tmp_topic_dir,
            thumbnail_path=explicit_thumb,
        )
        thumb = publisher._resolve_thumbnail(options)
        assert thumb == explicit_thumb

    def test_no_thumbnail_returns_none(self, fake_mp4: Path):
        publisher = YouTubePublisher()
        options = PublishOptions(video_path=fake_mp4)
        thumb = publisher._resolve_thumbnail(options)
        assert thumb is None


# ── Quality Verification Tests ──────────────────────────────────


class TestQualityVerification:
    @patch("youtube.publisher.check_mp4")
    def test_skip_when_disabled(self, mock_check: MagicMock, fake_mp4: Path):
        publisher = YouTubePublisher()
        options = PublishOptions(
            video_path=fake_mp4, verify_quality=False
        )
        result = publisher._verify_quality(options)
        mock_check.assert_not_called()
        assert result.passed is True

    @patch("youtube.publisher.check_mp4")
    def test_calls_check_mp4(self, mock_check: MagicMock, fake_mp4: Path):
        from core.utils.mp4_checker import MP4CheckResult

        mock_check.return_value = MP4CheckResult(file_path=fake_mp4)
        publisher = YouTubePublisher()
        options = PublishOptions(video_path=fake_mp4)
        result = publisher._verify_quality(options)
        mock_check.assert_called_once_with(fake_mp4)
        assert result.passed is True


# ── Full Publish Flow Tests ──────────────────────────────────


class TestPublishFlow:
    @pytest.mark.asyncio
    @patch("youtube.publisher.check_mp4")
    async def test_successful_publish(
        self,
        mock_check: MagicMock,
        tmp_topic_dir: Path,
        fake_mp4: Path,
        mock_upload_result: UploadResult,
    ):
        from core.utils.mp4_checker import MP4CheckResult

        mock_check.return_value = MP4CheckResult(file_path=fake_mp4)

        publisher = YouTubePublisher()
        publisher.uploader.authenticate = AsyncMock(return_value=True)
        publisher.uploader.upload_video = AsyncMock(
            return_value=mock_upload_result
        )

        options = PublishOptions(
            video_path=fake_mp4,
            topic_dir=tmp_topic_dir,
            save_result=True,
        )
        result = await publisher.publish(options)

        assert result.video_id == "test_vid_123"
        assert result.error is None
        assert result.quality_passed is True
        assert result.metadata_source == "auto"

        # 結果ファイルが保存されている
        result_file = tmp_topic_dir / "publish_result.json"
        assert result_file.exists()
        saved = json.loads(result_file.read_text(encoding="utf-8"))
        assert saved["video_id"] == "test_vid_123"

    @pytest.mark.asyncio
    @patch("youtube.publisher.check_mp4")
    async def test_quality_failure_aborts(
        self, mock_check: MagicMock, fake_mp4: Path
    ):
        from core.utils.mp4_checker import CheckItem, MP4CheckResult

        failed_result = MP4CheckResult(file_path=fake_mp4, passed=False)
        failed_result.checks = [
            CheckItem(
                name="codec",
                category="codec",
                severity="CRITICAL",
                expected="h264",
                actual="unknown",
                passed=False,
                message="Unsupported codec",
            )
        ]
        mock_check.return_value = failed_result

        publisher = YouTubePublisher()
        options = PublishOptions(video_path=fake_mp4)
        result = await publisher.publish(options)

        assert result.upload_status == "quality_failed"
        assert result.error is not None
        assert "品質検証" in result.error

    @pytest.mark.asyncio
    @patch("youtube.publisher.check_mp4")
    async def test_missing_metadata_aborts(
        self, mock_check: MagicMock, fake_mp4: Path
    ):
        from core.utils.mp4_checker import MP4CheckResult

        mock_check.return_value = MP4CheckResult(file_path=fake_mp4)

        publisher = YouTubePublisher()
        options = PublishOptions(video_path=fake_mp4)
        result = await publisher.publish(options)

        assert result.upload_status == "metadata_missing"
        assert result.error is not None

    @pytest.mark.asyncio
    @patch("youtube.publisher.check_mp4")
    async def test_upload_failure_returns_error(
        self,
        mock_check: MagicMock,
        tmp_topic_dir: Path,
        fake_mp4: Path,
    ):
        from core.utils.mp4_checker import MP4CheckResult

        mock_check.return_value = MP4CheckResult(file_path=fake_mp4)

        publisher = YouTubePublisher()
        publisher.uploader.authenticate = AsyncMock(return_value=False)

        options = PublishOptions(
            video_path=fake_mp4, topic_dir=tmp_topic_dir
        )
        result = await publisher.publish(options)

        assert result.upload_status == "upload_failed"
        assert result.error is not None

    @pytest.mark.asyncio
    @patch("youtube.publisher.check_mp4")
    async def test_no_save_skips_result_file(
        self,
        mock_check: MagicMock,
        tmp_topic_dir: Path,
        fake_mp4: Path,
        mock_upload_result: UploadResult,
    ):
        from core.utils.mp4_checker import MP4CheckResult

        mock_check.return_value = MP4CheckResult(file_path=fake_mp4)

        publisher = YouTubePublisher()
        publisher.uploader.authenticate = AsyncMock(return_value=True)
        publisher.uploader.upload_video = AsyncMock(
            return_value=mock_upload_result
        )

        options = PublishOptions(
            video_path=fake_mp4,
            topic_dir=tmp_topic_dir,
            save_result=False,
        )
        result = await publisher.publish(options)

        assert result.result_file is None
        assert not (tmp_topic_dir / "publish_result.json").exists()

    @pytest.mark.asyncio
    @patch("youtube.publisher.check_mp4")
    async def test_progress_callback_called(
        self,
        mock_check: MagicMock,
        tmp_topic_dir: Path,
        fake_mp4: Path,
        mock_upload_result: UploadResult,
    ):
        from core.utils.mp4_checker import MP4CheckResult

        mock_check.return_value = MP4CheckResult(file_path=fake_mp4)

        publisher = YouTubePublisher()
        publisher.uploader.authenticate = AsyncMock(return_value=True)
        publisher.uploader.upload_video = AsyncMock(
            return_value=mock_upload_result
        )

        steps_seen: list[str] = []

        def track_progress(step: str, pct: float) -> None:
            steps_seen.append(step)

        options = PublishOptions(
            video_path=fake_mp4,
            topic_dir=tmp_topic_dir,
            progress_callback=track_progress,
        )
        result = await publisher.publish(options)

        assert "phase7_start" in steps_seen
        assert "quality_done" in steps_seen
        assert "phase7_complete" in steps_seen
        assert result.error is None


# ── Result Persistence Tests ──────────────────────────────────


class TestResultPersistence:
    def test_save_to_topic_dir(self, tmp_topic_dir: Path, fake_mp4: Path):
        publisher = YouTubePublisher()
        result = PublishResult(
            video_id="save_test",
            video_url="https://youtube.com/watch?v=save_test",
            upload_status="uploaded",
            privacy_status="private",
            quality_passed=True,
            quality_warnings=[],
            metadata_source="auto",
        )
        options = PublishOptions(
            video_path=fake_mp4, topic_dir=tmp_topic_dir
        )
        path = publisher._save_result(result, options)

        assert path.exists()
        saved = json.loads(path.read_text(encoding="utf-8"))
        assert saved["video_id"] == "save_test"

    def test_save_to_video_dir_fallback(self, tmp_path: Path):
        mp4 = tmp_path / "output" / "video.mp4"
        mp4.parent.mkdir(parents=True)
        mp4.write_bytes(b"\x00")

        publisher = YouTubePublisher()
        result = PublishResult(
            video_id="fallback_test",
            video_url="",
            upload_status="uploaded",
            privacy_status="private",
            quality_passed=True,
            quality_warnings=[],
            metadata_source="file",
        )
        options = PublishOptions(video_path=mp4)
        path = publisher._save_result(result, options)

        assert path.parent == mp4.parent
        assert path.exists()


# ── Schedule Publishing Tests ──────────────────────────────────


class TestSchedulePublishing:
    @pytest.mark.asyncio
    @patch("youtube.publisher.check_mp4")
    async def test_schedule_sets_publish_at(
        self,
        mock_check: MagicMock,
        tmp_topic_dir: Path,
        fake_mp4: Path,
        mock_upload_result: UploadResult,
    ):
        from core.utils.mp4_checker import MP4CheckResult

        mock_check.return_value = MP4CheckResult(file_path=fake_mp4)

        publisher = YouTubePublisher()
        publisher.uploader.authenticate = AsyncMock(return_value=True)
        publisher.uploader.upload_video = AsyncMock(
            return_value=mock_upload_result
        )

        options = PublishOptions(
            video_path=fake_mp4,
            topic_dir=tmp_topic_dir,
            schedule="2026-03-25T18:00:00Z",
        )
        result = await publisher.publish(options)

        assert result.error is None
        # upload_video に渡された metadata に publish_at が含まれている
        call_kwargs = publisher.uploader.upload_video.call_args
        passed_metadata = call_kwargs.kwargs.get("metadata") or call_kwargs[1].get("metadata")
        if passed_metadata is None:
            # positional args
            passed_metadata = call_kwargs[0][1] if len(call_kwargs[0]) > 1 else {}
        assert passed_metadata.get("publish_at") == "2026-03-25T18:00:00Z"

    def test_publish_options_schedule_default_none(self, fake_mp4: Path):
        opts = PublishOptions(video_path=fake_mp4)
        assert opts.schedule is None


class TestUploadMetadataSchedule:
    def test_normalize_metadata_with_publish_at(self):
        from youtube.uploader import _normalize_metadata

        meta = _normalize_metadata({
            "title": "Test",
            "description": "Desc",
            "tags": ["t1"],
            "category_id": "22",
            "language": "ja",
            "publish_at": "2026-03-25T18:00:00Z",
        })
        assert meta.publish_at == "2026-03-25T18:00:00Z"

    def test_normalize_metadata_with_publishAt_key(self):
        from youtube.uploader import _normalize_metadata

        meta = _normalize_metadata({
            "title": "Test",
            "description": "Desc",
            "tags": [],
            "category_id": "22",
            "language": "ja",
            "publishAt": "2026-04-01T12:00:00Z",
        })
        assert meta.publish_at == "2026-04-01T12:00:00Z"

    def test_normalize_metadata_without_schedule(self):
        from youtube.uploader import _normalize_metadata

        meta = _normalize_metadata({
            "title": "Test",
            "description": "Desc",
            "tags": [],
            "category_id": "22",
            "language": "ja",
        })
        assert meta.publish_at is None

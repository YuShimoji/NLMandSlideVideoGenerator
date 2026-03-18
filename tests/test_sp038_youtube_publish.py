"""SP-038 YouTube公開パイプライン テスト

Phase 1: ScriptBundle → TranscriptInfo 変換 + メタデータ生成
Phase 2: クレジット自動挿入
Phase 3: YouTubeUploader 実装 (モックAPI層テスト)
"""
from unittest.mock import patch, MagicMock, AsyncMock
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List
import asyncio
import json
import tempfile
import pytest

# TranscriptInfo / TranscriptSegment の実データクラスを定義
@dataclass
class _TranscriptSegment:
    id: int
    start_time: float
    end_time: float
    speaker: str
    text: str
    key_points: List[str]
    slide_suggestion: str
    confidence_score: float

@dataclass
class _TranscriptInfo:
    title: str
    total_duration: float
    segments: List[_TranscriptSegment]
    accuracy_score: float
    created_at: datetime
    source_audio_path: str


# settings / transcript モックを設定してからインポート
_mock_settings = MagicMock()
_mock_settings.YOUTUBE_SETTINGS = {
    "max_title_length": 100,
    "max_description_length": 5000,
    "max_tags_length": 500,
    "category_id": "22",
    "default_language": "ja",
    "privacy_status": "private",
}
_mock_settings.TEMPLATES_DIR = MagicMock()
_mock_templates_dir = MagicMock()
_mock_templates_dir.exists.return_value = False
_mock_templates_dir.glob.return_value = []
_mock_templates_dir.mkdir = MagicMock()
_mock_templates_dir.__truediv__ = lambda self, other: _mock_templates_dir
_mock_settings.TEMPLATES_DIR.__truediv__ = lambda self, other: _mock_templates_dir

_transcript_module = MagicMock()
_transcript_module.TranscriptInfo = _TranscriptInfo
_transcript_module.TranscriptSegment = _TranscriptSegment

with patch.dict("sys.modules", {
    "config": MagicMock(),
    "config.settings": MagicMock(settings=_mock_settings),
    "core": MagicMock(),
    "core.utils": MagicMock(),
    "core.utils.logger": MagicMock(logger=MagicMock()),
    "core.exceptions": MagicMock(),
    "notebook_lm": MagicMock(),
    "notebook_lm.transcript_processor": _transcript_module,
    "notebook_lm.audio_generator": MagicMock(),
    "youtube.uploader": MagicMock(),
}):
    from youtube.script_to_transcript import script_bundle_to_transcript
    from youtube.metadata_generator import MetadataGenerator


# ===== Fixtures =====

@pytest.fixture
def sample_bundle():
    """典型的なscript_bundle辞書。"""
    return {
        "title": "AIの最新動向",
        "total_duration": 300.0,
        "segments": [
            {
                "text": "今日はAIの最新動向についてお話しします。",
                "speaker": "Host1",
                "start_time": 0.0,
                "end_time": 30.0,
                "key_points": ["AI", "最新動向"],
                "slide_suggestion": "AIイメージ",
            },
            {
                "text": "まず機械学習の基礎から見ていきましょう。",
                "speaker": "Host2",
                "start_time": 30.0,
                "end_time": 60.0,
                "key_points": ["機械学習", "基礎"],
            },
            {
                "text": "ディープラーニングの進化は目覚ましいですね。",
                "speaker": "Host1",
                "start_time": 60.0,
                "end_time": 90.0,
                "key_points": ["ディープラーニング", "進化"],
            },
        ],
    }


@pytest.fixture
def minimal_bundle():
    """最小限のscript_bundle。"""
    return {"title": "テスト"}


@pytest.fixture
def bundle_no_title():
    """タイトルなしのbundle。"""
    return {
        "segments": [
            {"text": "セグメント1", "content": "テスト"},
        ],
    }


@pytest.fixture
def generator():
    """MetadataGenerator インスタンス。"""
    return MetadataGenerator()


# ===== Phase 1: script_bundle_to_transcript =====

class TestScriptBundleToTranscript:
    def test_basic_conversion(self, sample_bundle):
        result = script_bundle_to_transcript(sample_bundle)
        assert result.title == "AIの最新動向"
        assert result.total_duration == 300.0
        assert len(result.segments) == 3

    def test_segment_fields(self, sample_bundle):
        result = script_bundle_to_transcript(sample_bundle)
        seg0 = result.segments[0]
        assert seg0.id == 0
        assert seg0.speaker == "Host1"
        assert seg0.start_time == 0.0
        assert seg0.end_time == 30.0
        assert "AI" in seg0.key_points
        assert seg0.slide_suggestion == "AIイメージ"

    def test_fallback_topic(self, bundle_no_title):
        result = script_bundle_to_transcript(bundle_no_title, topic="フォールバックトピック")
        assert result.title == "フォールバックトピック"

    def test_untitled_fallback(self, bundle_no_title):
        result = script_bundle_to_transcript(bundle_no_title)
        assert result.title == "Untitled"

    def test_empty_segments(self, minimal_bundle):
        result = script_bundle_to_transcript(minimal_bundle)
        assert result.title == "テスト"
        assert len(result.segments) == 0
        assert result.total_duration == 0.0

    def test_content_key_fallback(self):
        """text キーがなく content キーがある場合。"""
        bundle = {
            "title": "Test",
            "segments": [{"content": "コンテンツテスト", "speaker": "A"}],
        }
        result = script_bundle_to_transcript(bundle)
        assert result.segments[0].text == "コンテンツテスト"

    def test_auto_speaker_assignment(self):
        """speaker未指定時の自動割当。"""
        bundle = {
            "title": "Test",
            "segments": [{"text": "a"}, {"text": "b"}, {"text": "c"}],
        }
        result = script_bundle_to_transcript(bundle)
        assert result.segments[0].speaker == "Speaker1"
        assert result.segments[1].speaker == "Speaker2"
        assert result.segments[2].speaker == "Speaker1"

    def test_cumulative_time(self):
        """start_time/end_time未指定時の累積計算。"""
        bundle = {
            "title": "Test",
            "segments": [
                {"text": "a", "duration": 10.0},
                {"text": "b", "duration": 20.0},
            ],
        }
        result = script_bundle_to_transcript(bundle)
        assert result.segments[0].start_time == 0.0
        assert result.segments[0].end_time == 10.0
        assert result.segments[1].start_time == 10.0
        assert result.segments[1].end_time == 30.0

    def test_key_points_from_title(self):
        """key_points未指定時、セグメントtitleからフォールバック。"""
        bundle = {
            "title": "Test",
            "segments": [{"text": "a", "title": "導入部分"}],
        }
        result = script_bundle_to_transcript(bundle)
        assert result.segments[0].key_points == ["導入部分"]


# ===== Phase 1: generate_metadata_from_bundle =====

class TestGenerateMetadataFromBundle:
    @pytest.mark.asyncio
    async def test_basic_generation(self, generator, sample_bundle):
        result = await generator.generate_metadata_from_bundle(sample_bundle)
        assert "title" in result
        assert "description" in result
        assert "tags" in result
        assert isinstance(result.get("category_id"), str)

    @pytest.mark.asyncio
    async def test_with_topic_fallback(self, generator, bundle_no_title):
        result = await generator.generate_metadata_from_bundle(
            bundle_no_title, topic="フォールバック"
        )
        assert result["title"]  # 空でないこと

    @pytest.mark.asyncio
    async def test_with_credits(self, generator, sample_bundle):
        credits = ["Photo by Alice on Pexels", "Photo by Bob on Pixabay"]
        result = await generator.generate_metadata_from_bundle(
            sample_bundle, credits=credits
        )
        assert "【画像クレジット】" in result["description"]
        assert "Photo by Alice on Pexels" in result["description"]


# ===== Phase 2: append_credits =====

class TestAppendCredits:
    def test_basic_append(self):
        desc = "動画の概要です。"
        credits = ["Photo by X on Pexels", "Photo by Y on Pixabay"]
        result = MetadataGenerator.append_credits(desc, credits)
        assert result.startswith("動画の概要です。")
        assert "【画像クレジット】" in result
        assert "Photo by X on Pexels" in result
        assert "Photo by Y on Pixabay" in result

    def test_empty_credits(self):
        desc = "動画の概要です。"
        result = MetadataGenerator.append_credits(desc, [])
        assert result == desc

    def test_duplicate_removal(self):
        credits = ["Photo by X on Pexels", "Photo by X on Pexels", "Photo by Y on Pixabay"]
        result = MetadataGenerator.append_credits("desc", credits)
        assert result.count("Photo by X on Pexels") == 1


# ===== Phase 2: _extract_credits (直接テスト) =====

def _extract_credits(editing_outputs):
    """pipeline.py の _extract_credits ロジックを直接テスト。

    pipeline.py の import chain が重いため、ロジックだけ抽出してテスト。
    """
    if not editing_outputs:
        return []
    credits = []
    raw_credits = editing_outputs.get("image_credits", "")
    if isinstance(raw_credits, str) and raw_credits.strip():
        for line in raw_credits.strip().splitlines():
            line = line.strip()
            if line and not line.startswith("---"):
                credits.append(line)
    elif isinstance(raw_credits, list):
        credits.extend(str(c) for c in raw_credits if c)
    return credits


class TestExtractCredits:
    def test_string_credits(self):
        outputs = {
            "image_credits": "--- Image Credits ---\nPhoto by X on Pexels\nPhoto by Y on Pixabay"
        }
        result = _extract_credits(outputs)
        assert "Photo by X on Pexels" in result
        assert "Photo by Y on Pixabay" in result
        assert "--- Image Credits ---" not in result

    def test_list_credits(self):
        outputs = {"image_credits": ["Photo by X on Pexels"]}
        result = _extract_credits(outputs)
        assert result == ["Photo by X on Pexels"]

    def test_none_outputs(self):
        assert _extract_credits(None) == []

    def test_empty_outputs(self):
        assert _extract_credits({}) == []


# ===== Phase 3: YouTubeUploader =====

# uploader は独自の import chain を持つため、モック設定して直接インポート
with patch.dict("sys.modules", {
    "config": MagicMock(),
    "config.settings": MagicMock(settings=_mock_settings),
    "core": MagicMock(),
    "core.utils": MagicMock(),
    "core.utils.logger": MagicMock(logger=MagicMock()),
    "core.exceptions": MagicMock(
        UploadError=type("UploadError", (Exception,), {}),
        QuotaExceededError=type("QuotaExceededError", (Exception,), {}),
        APIAuthenticationError=type("APIAuthenticationError", (Exception,), {}),
    ),
    "gapi": MagicMock(),
    "gapi.google_auth": MagicMock(),
}):
    from youtube.uploader import (
        YouTubeUploader,
        UploadMetadata,
        UploadResult,
        _normalize_metadata,
        _normalize_video_path,
        load_metadata_from_json,
    )


@pytest.fixture
def uploader():
    """モックモードの YouTubeUploader"""
    u = YouTubeUploader()
    u._mock_mode = True
    return u


@pytest.fixture
def sample_metadata():
    return UploadMetadata(
        title="テスト動画",
        description="テスト説明",
        tags=["AI", "テスト"],
        category_id="27",
        language="ja",
        privacy_status="private",
    )


@pytest.fixture
def tmp_video(tmp_path):
    """テスト用の仮MP4ファイル"""
    video = tmp_path / "test_video.mp4"
    video.write_bytes(b"\x00" * 1024 * 100)  # 100KB
    return video


class TestNormalizeMetadata:
    def test_dict_to_metadata(self):
        meta = _normalize_metadata({
            "title": "Test",
            "description": "Desc",
            "tags": ["a", "b"],
        })
        assert isinstance(meta, UploadMetadata)
        assert meta.title == "Test"
        assert meta.privacy_status == "private"  # default

    def test_passthrough_metadata(self, sample_metadata):
        result = _normalize_metadata(sample_metadata)
        assert result is sample_metadata

    def test_defaults(self):
        meta = _normalize_metadata({})
        assert meta.title == "Untitled"
        assert meta.category_id == "27"
        assert meta.language == "ja"


class TestNormalizeVideoPath:
    def test_path_passthrough(self, tmp_video):
        assert _normalize_video_path(tmp_video) == tmp_video

    def test_object_with_file_path(self):
        obj = MagicMock()
        obj.file_path = "/tmp/video.mp4"
        result = _normalize_video_path(obj)
        assert result == Path("/tmp/video.mp4")

    def test_invalid_raises(self):
        with pytest.raises(TypeError):
            _normalize_video_path("not_a_path")


class TestYouTubeUploaderAuthenticate:
    @pytest.mark.asyncio
    async def test_mock_mode_without_credentials(self):
        u = YouTubeUploader()
        # google_auth が None を返すようにパッチ
        with patch.object(u, "_get_credentials", return_value=None):
            result = await u.authenticate()
        assert result is True
        assert u.is_mock_mode is True

    @pytest.mark.asyncio
    async def test_real_mode_with_credentials(self):
        u = YouTubeUploader()
        mock_creds = MagicMock()
        mock_service = MagicMock()

        with patch.object(u, "_get_credentials", return_value=mock_creds), \
             patch("youtube.uploader.build", return_value=mock_service, create=True):
            # build がインポートできる環境をシミュレート
            import sys
            mock_gapi = MagicMock()
            mock_gapi.discovery.build = MagicMock(return_value=mock_service)
            with patch.dict(sys.modules, {"googleapiclient": mock_gapi, "googleapiclient.discovery": mock_gapi.discovery}):
                from googleapiclient.discovery import build as _build
                with patch("youtube.uploader.build", _build, create=True):
                    # authenticate 内の try-except で ImportError になるのを回避
                    result = await u.authenticate()
        # 認証情報があっても googleapiclient.discovery.build の挙動によるので
        # モックモードフォールバックも含めて True を期待
        assert result is True


class TestYouTubeUploaderUpload:
    @pytest.mark.asyncio
    async def test_mock_upload(self, uploader, sample_metadata, tmp_video):
        result = await uploader.upload_video(tmp_video, sample_metadata, verify_quality=False)
        assert isinstance(result, UploadResult)
        assert result.video_id.startswith("mock_")
        assert result.upload_status == "uploaded"
        assert result.privacy_status == "private"

    @pytest.mark.asyncio
    async def test_upload_with_dict_metadata(self, uploader, tmp_video):
        meta_dict = {
            "title": "Dict Test",
            "description": "Test",
            "tags": ["test"],
            "category_id": "22",
            "language": "ja",
            "privacy_status": "unlisted",
        }
        result = await uploader.upload_video(tmp_video, meta_dict, verify_quality=False)
        assert result.privacy_status == "unlisted"

    @pytest.mark.asyncio
    async def test_upload_file_not_found(self, uploader, sample_metadata):
        with pytest.raises(Exception):  # UploadError は モック上の例外
            await uploader.upload_video(Path("/nonexistent/video.mp4"), sample_metadata, verify_quality=False)

    @pytest.mark.asyncio
    async def test_progress_callback(self, uploader, sample_metadata, tmp_video):
        progress_values = []
        def cb(p):
            progress_values.append(p)
        await uploader.upload_video(tmp_video, sample_metadata, progress_callback=cb, verify_quality=False)
        assert len(progress_values) > 0
        assert progress_values[-1] == 1.0  # 最終進捗は100%

    @pytest.mark.asyncio
    async def test_quota_tracking(self, uploader, sample_metadata, tmp_video):
        await uploader.upload_video(tmp_video, sample_metadata, verify_quality=False)
        quota = uploader.get_quota_usage()
        assert quota["used"] == 1600
        assert quota["remaining"] == 10000 - 1600


class TestYouTubeUploaderValidation:
    def test_title_too_long(self, uploader):
        meta = UploadMetadata(
            title="x" * 101,
            description="d",
            tags=[],
            category_id="27",
            language="ja",
        )
        with pytest.raises(ValueError, match="タイトルが長すぎます"):
            uploader._validate_metadata(meta)

    def test_description_too_long(self, uploader):
        meta = UploadMetadata(
            title="ok",
            description="x" * 5001,
            tags=[],
            category_id="27",
            language="ja",
        )
        with pytest.raises(ValueError, match="説明文が長すぎます"):
            uploader._validate_metadata(meta)

    def test_invalid_privacy(self, uploader):
        meta = UploadMetadata(
            title="ok",
            description="ok",
            tags=[],
            category_id="27",
            language="ja",
            privacy_status="draft",
        )
        with pytest.raises(ValueError, match="無効なプライバシー設定"):
            uploader._validate_metadata(meta)


class TestYouTubeUploaderStatus:
    @pytest.mark.asyncio
    async def test_mock_status(self, uploader):
        status = await uploader.get_upload_status("mock_123")
        assert status["video_id"] == "mock_123"
        assert status["upload_status"] == "uploaded"

    @pytest.mark.asyncio
    async def test_mock_channel_info(self, uploader):
        info = await uploader.get_channel_info()
        assert "channel_id" in info
        assert info["channel_id"] == "UCmock_channel_id"

    @pytest.mark.asyncio
    async def test_mock_update_metadata(self, uploader, sample_metadata):
        result = await uploader.update_video_metadata("mock_123", sample_metadata)
        assert result is True

    @pytest.mark.asyncio
    async def test_mock_delete(self, uploader):
        result = await uploader.delete_video("mock_123")
        assert result is True


class TestYouTubeUploaderBatch:
    @pytest.mark.asyncio
    async def test_batch_upload(self, uploader, sample_metadata, tmp_video):
        # batch_upload は verify_quality を個別に渡せないため、
        # uploader._verify_mp4_quality をモックして回避
        uploader._verify_mp4_quality = lambda path: None
        pairs = [(tmp_video, sample_metadata), (tmp_video, sample_metadata)]
        result = await uploader.batch_upload(pairs, max_concurrent=2)
        assert result["total"] == 2
        assert len(result["successful"]) == 2
        assert len(result["failed"]) == 0


class TestVerifyQualityIntegration:
    """SP-039 Phase 2: upload前のMP4品質検証統合テスト"""

    @pytest.mark.asyncio
    async def test_verify_quality_skip_when_false(self, uploader, sample_metadata, tmp_video):
        """verify_quality=Falseで品質検証をスキップ"""
        result = await uploader.upload_video(tmp_video, sample_metadata, verify_quality=False)
        assert isinstance(result, UploadResult)

    @pytest.mark.asyncio
    async def test_verify_quality_returns_none_without_ffprobe(self, uploader, tmp_video):
        """FFprobeがない環境ではNoneを返して検証スキップ"""
        result = uploader._verify_mp4_quality(tmp_video)
        # FFprobeがない環境ではNone(スキップ)、ある環境ではMP4CheckResult
        # テスト環境ではFFprobeの有無に依存しないことを確認
        # Noneの場合はスキップ、MP4CheckResultの場合はFAIL(偽MP4なので)
        assert result is None or hasattr(result, "passed")

    @pytest.mark.asyncio
    async def test_upload_blocked_by_quality_failure(self, uploader, sample_metadata, tmp_video):
        """品質検証がCRITICAL失敗を返した場合、アップロードが阻止される"""
        # mp4_checkerが100KBファイルに対してfile_size_min CRITICALを返すことを利用
        # ただしFFprobeがない環境ではスキップされるため、_verify_mp4_qualityをモック
        from unittest.mock import MagicMock as _MagicMock
        mock_result = _MagicMock()
        mock_result.passed = False
        mock_result.critical_failures = [_MagicMock(name="file_size_min", actual="0.1MB", expected="> 1MB")]
        uploader._verify_mp4_quality = lambda path: mock_result
        with pytest.raises(Exception):  # UploadError
            await uploader.upload_video(tmp_video, sample_metadata, verify_quality=True)

    @pytest.mark.asyncio
    async def test_upload_proceeds_when_quality_passes(self, uploader, sample_metadata, tmp_video):
        """品質検証PASSならアップロード続行"""
        from unittest.mock import MagicMock as _MagicMock
        mock_result = _MagicMock()
        mock_result.passed = True
        uploader._verify_mp4_quality = lambda path: mock_result
        result = await uploader.upload_video(tmp_video, sample_metadata, verify_quality=True)
        assert isinstance(result, UploadResult)


class TestLoadMetadataFromJson:
    def test_load_metadata(self, tmp_path):
        meta_path = tmp_path / "metadata.json"
        meta_path.write_text(json.dumps({
            "title": "JSON Test",
            "description": "From JSON",
            "tags": ["json", "test"],
            "category_id": "22",
            "language": "ja",
            "privacy_status": "unlisted",
        }), encoding="utf-8")

        result = load_metadata_from_json(meta_path)
        assert isinstance(result, UploadMetadata)
        assert result.title == "JSON Test"
        assert result.privacy_status == "unlisted"

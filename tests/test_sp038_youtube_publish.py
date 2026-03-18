"""SP-038 YouTube公開パイプライン テスト

Phase 1: ScriptBundle → TranscriptInfo 変換 + メタデータ生成
Phase 2: クレジット自動挿入
"""
from unittest.mock import patch, MagicMock
from dataclasses import dataclass
from datetime import datetime
from typing import List
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

"""MetadataGenerator テスト"""
from unittest.mock import patch, MagicMock
from collections import Counter

import pytest

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
_mock_templates_dir.__truediv__ = lambda self, other: MagicMock()
_mock_settings.TEMPLATES_DIR.__truediv__ = lambda self, other: _mock_templates_dir

with patch.dict("sys.modules", {
    "config": MagicMock(),
    "config.settings": MagicMock(settings=_mock_settings),
    "notebook_lm": MagicMock(),
    "notebook_lm.transcript_processor": MagicMock(
        TranscriptInfo=MagicMock,
        TranscriptSegment=MagicMock,
    ),
    "youtube.uploader": MagicMock(),
}):
    from youtube.metadata_generator import MetadataGenerator, VideoMetadata


def _make_segment(
    id: int = 0,
    text: str = "テスト",
    speaker: str = "Host1",
    start_time: float = 0.0,
    end_time: float = 5.0,
    key_points: list | None = None,
    slide_suggestion: str = "",
    confidence_score: float = 0.95,
):
    seg = MagicMock()
    seg.id = id
    seg.text = text
    seg.speaker = speaker
    seg.start_time = start_time
    seg.end_time = end_time
    seg.key_points = key_points or []
    seg.slide_suggestion = slide_suggestion
    seg.confidence_score = confidence_score
    return seg


def _make_transcript(title="テスト動画", segments=None):
    t = MagicMock()
    t.title = title
    t.segments = segments or []
    return t


class TestVideoMetadata:
    def test_dataclass_creation(self):
        m = VideoMetadata(
            title="T", description="D", tags=["a"],
            category_id="22",
        )
        assert m.title == "T"
        assert m.thumbnail_suggestions is None

    def test_optional_fields(self):
        m = VideoMetadata(
            title="T", description="D", tags=[],
            category_id="22", language="ja", privacy_status="public",
            thumbnail_suggestions=["img"],
        )
        assert m.language == "ja"
        assert m.thumbnail_suggestions == ["img"]


class TestSecondsToTimestamp:
    def test_zero(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        assert gen._seconds_to_timestamp(0) == "00:00"

    def test_normal(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        assert gen._seconds_to_timestamp(65) == "01:05"

    def test_large(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        assert gen._seconds_to_timestamp(3661) == "61:01"


class TestExtractMainKeywords:
    def test_empty_segments(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        transcript = _make_transcript(segments=[])
        assert gen._extract_main_keywords(transcript) == []

    def test_returns_most_common(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        segments = [
            _make_segment(key_points=["AI", "ML"]),
            _make_segment(key_points=["AI", "データ"]),
            _make_segment(key_points=["AI", "ML"]),
        ]
        transcript = _make_transcript(segments=segments)
        keywords = gen._extract_main_keywords(transcript)
        assert keywords[0] == "AI"  # 最頻出
        assert len(keywords) <= 5


class TestGetMainHashtag:
    def test_with_keywords(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        segments = [_make_segment(key_points=["機械学習"])]
        transcript = _make_transcript(segments=segments)
        assert gen._get_main_hashtag(transcript) == "機械学習"

    def test_no_keywords(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        transcript = _make_transcript(segments=[])
        assert gen._get_main_hashtag(transcript) == "解説"


class TestGenerateChapterTitle:
    def test_with_key_points(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        segments = [_make_segment(key_points=["AI", "ML"]),
                     _make_segment(key_points=["AI"])]
        title = gen._generate_chapter_title(segments)
        assert "AI" in title

    def test_no_key_points(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        segments = [_make_segment(text="短いテキスト", key_points=[])]
        title = gen._generate_chapter_title(segments)
        assert "短いテキスト" in title

    def test_long_text_truncated(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        segments = [_make_segment(text="あ" * 50, key_points=[])]
        title = gen._generate_chapter_title(segments)
        assert len(title) <= 24  # 20 + "..."

    def test_empty_segments(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        assert gen._generate_chapter_title([]) == "詳細解説"


class TestGenerateVideoSummary:
    def test_empty_segments(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        transcript = _make_transcript(segments=[])
        summary = gen._generate_video_summary(transcript)
        assert "解説" in summary

    def test_with_segments(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        segments = [
            _make_segment(text="AIの基礎について", key_points=["AI"]),
            _make_segment(text="詳細説明", key_points=["AI"]),
        ]
        transcript = _make_transcript(segments=segments)
        summary = gen._generate_video_summary(transcript)
        assert "AI" in summary

    def test_truncation(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        segments = [_make_segment(text="あ" * 400, key_points=["k" * 50] * 10)]
        transcript = _make_transcript(segments=segments)
        summary = gen._generate_video_summary(transcript)
        assert len(summary) <= 304  # 300 + "..."


class TestExtractKeyPointsForDescription:
    def test_empty(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        transcript = _make_transcript(segments=[])
        assert gen._extract_key_points_for_description(transcript) == []

    def test_top_5(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        segments = [_make_segment(key_points=[f"point{i}" for i in range(10)])]
        transcript = _make_transcript(segments=segments)
        result = gen._extract_key_points_for_description(transcript)
        assert len(result) <= 5


class TestExtractSourceInformation:
    def test_url_extraction(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        segments = [_make_segment(text="詳しくは https://example.com を参照")]
        transcript = _make_transcript(segments=segments)
        sources = gen._extract_source_information(transcript)
        assert any("example.com" in s for s in sources)

    def test_no_sources_default(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        segments = [_make_segment(text="普通のテキスト", key_points=[])]
        transcript = _make_transcript(segments=segments)
        sources = gen._extract_source_information(transcript)
        assert any("信頼" in s for s in sources)

    def test_quote_extraction(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        segments = [_make_segment(
            text="総務省が発表した統計データによると",
            key_points=[]
        )]
        transcript = _make_transcript(segments=segments)
        sources = gen._extract_source_information(transcript)
        assert any("総務省" in s for s in sources)

    def test_max_10_sources(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        urls = " ".join(f"https://example{i}.com" for i in range(20))
        segments = [_make_segment(text=urls)]
        transcript = _make_transcript(segments=segments)
        sources = gen._extract_source_information(transcript)
        assert len(sources) <= 10


class TestGenerateTopicTags:
    def test_tech_terms_extracted(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        segments = [_make_segment(text="AIとプログラミングのデータ分析")]
        transcript = _make_transcript(segments=segments)
        tags = gen._generate_topic_tags(transcript)
        assert any("AI" in t for t in tags)

    def test_no_tech_terms(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        segments = [_make_segment(text="今日の天気は晴れ")]
        transcript = _make_transcript(segments=segments)
        tags = gen._generate_topic_tags(transcript)
        assert tags == []


class TestGenerateThumbnailSuggestions:
    def test_with_keywords(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        segments = [_make_segment(key_points=["AI", "ML"])]
        transcript = _make_transcript(segments=segments)
        suggestions = gen._generate_thumbnail_suggestions(transcript)
        assert len(suggestions) >= 4

    def test_empty_keywords(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        transcript = _make_transcript(segments=[])
        suggestions = gen._generate_thumbnail_suggestions(transcript)
        assert len(suggestions) >= 4  # 一般的な提案が含まれる


class TestOptimizeForSeo:
    def test_adds_keyword_to_title(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        gen.max_title_length = 100
        metadata = {"title": "元のタイトル", "description": "概要", "tags": []}
        result = gen.optimize_for_seo(metadata, ["SEOキーワード"])
        assert "SEOキーワード" in result["title"]

    def test_keyword_already_in_title(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        gen.max_title_length = 100
        metadata = {"title": "SEOキーワードの解説", "description": "概要", "tags": []}
        result = gen.optimize_for_seo(metadata, ["SEOキーワード"])
        assert result["title"] == "SEOキーワードの解説"

    def test_adds_keyword_to_description(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        gen.max_title_length = 100
        metadata = {"title": "タイトル", "description": "概要テキスト", "tags": []}
        result = gen.optimize_for_seo(metadata, ["kw1", "kw2"])
        assert result["description"].startswith("キーワード:")

    def test_empty_keywords(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        gen.max_title_length = 100
        metadata = {"title": "タイトル", "description": "概要", "tags": []}
        result = gen.optimize_for_seo(metadata, [])
        assert result["title"] == "タイトル"


class TestTemplateMethods:
    def test_generate_title_from_template(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        gen.max_title_length = 100
        transcript = _make_transcript(title="AIトピック", segments=[
            _make_segment(key_points=["機械学習"]),
        ])
        template = {"title_template": "{topic} - {key_points}"}
        title = gen._generate_title_from_template(transcript, template)
        assert "AIトピック" in title
        assert "機械学習" in title

    def test_title_truncation(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        gen.max_title_length = 20
        transcript = _make_transcript(title="あ" * 50, segments=[])
        template = {"title_template": "{topic}"}
        title = gen._generate_title_from_template(transcript, template)
        assert len(title) <= 20
        assert title.endswith("...")

    def test_generate_description_from_template(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        gen.max_description_length = 5000
        transcript = _make_transcript(title="テーマ", segments=[
            _make_segment(start_time=0, end_time=30, key_points=["AI"]),
        ])
        template = {"description_template": "この動画では{topic}について解説します。"}
        desc = gen._generate_description_from_template(transcript, template)
        assert "テーマ" in desc

    def test_generate_tags_from_template(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        gen.max_tags_length = 500
        transcript = _make_transcript(title="Python", segments=[])
        template = {"tags_template": ["{topic}", "プログラミング"]}
        tags = gen._generate_tags_from_template(transcript, template)
        assert "Python" in tags
        assert "プログラミング" in tags

    def test_format_duration_with_segments(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        segments = [
            _make_segment(end_time=120),
            _make_segment(end_time=300),
        ]
        transcript = _make_transcript(segments=segments)
        assert gen._format_duration(transcript) == "5分"

    def test_format_duration_no_segments(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        transcript = _make_transcript(segments=[])
        assert gen._format_duration(transcript) == "不明"

    def test_get_key_points_string(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        segments = [_make_segment(key_points=["AI", "ML", "DL", "NLP"])]
        transcript = _make_transcript(segments=segments)
        result = gen._get_key_points_string(transcript)
        assert "AI" in result
        assert result.count(",") <= 2  # 最大3つ

    def test_generate_hashtags_string(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        segments = [_make_segment(key_points=["AI", "ML"])]
        transcript = _make_transcript(segments=segments)
        result = gen._generate_hashtags_string(transcript)
        assert "#AI" in result


class TestGroupSegmentsIntoChapters:
    def test_empty_segments(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        assert gen._group_segments_into_chapters([]) == []

    def test_single_segment(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        segments = [_make_segment(id=1, start_time=0, end_time=30, speaker="A", key_points=["AI"])]
        chapters = gen._group_segments_into_chapters(segments)
        assert len(chapters) >= 1
        assert chapters[0] == (0.0, "イントロダクション")

    def test_speaker_change_creates_chapter(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        segments = [
            _make_segment(id=1, start_time=0, end_time=30, speaker="A", key_points=["AI"]),
            _make_segment(id=2, start_time=30, end_time=60, speaker="B", key_points=["AI"]),
            _make_segment(id=3, start_time=60, end_time=90, speaker="B", key_points=["AI"]),
        ]
        chapters = gen._group_segments_into_chapters(segments)
        assert len(chapters) >= 1

    def test_max_10_chapters(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        segments = [
            _make_segment(
                id=i, start_time=i * 130.0, end_time=(i + 1) * 130.0,
                speaker=f"Speaker{i % 3}", key_points=[f"topic{i}"]
            )
            for i in range(30)
        ]
        chapters = gen._group_segments_into_chapters(segments)
        assert len(chapters) <= 10


class TestGenerateChapters:
    def test_empty(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        transcript = _make_transcript(segments=[])
        assert gen._generate_chapters(transcript) == []

    def test_has_timestamps(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        segments = [
            _make_segment(id=1, start_time=0, end_time=60, speaker="A", key_points=["AI"]),
            _make_segment(id=2, start_time=60, end_time=120, speaker="B", key_points=["ML"]),
            _make_segment(id=3, start_time=120, end_time=180, speaker="A", key_points=["DL"]),
        ]
        transcript = _make_transcript(segments=segments)
        chapters = gen._generate_chapters(transcript)
        assert any("00:00" in ch for ch in chapters)

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


class TestGenerateTitle:
    def test_with_keywords(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        gen.max_title_length = 100
        segments = [_make_segment(key_points=["AI", "ML"])]
        transcript = _make_transcript(title="AI解説", segments=segments)
        title = gen._generate_title(transcript)
        assert "AI" in title
        assert len(title) <= 100

    def test_no_keywords_uses_title(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        gen.max_title_length = 100
        transcript = _make_transcript(title="素晴らしいタイトル", segments=[])
        title = gen._generate_title(transcript)
        assert "素晴らしいタイトル" in title

    def test_long_title_truncated(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        gen.max_title_length = 20
        transcript = _make_transcript(title="あ" * 50, segments=[])
        title = gen._generate_title(transcript)
        assert len(title) <= 20
        assert title.endswith("...")


class TestGenerateDescription:
    def test_basic_structure(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        gen.max_description_length = 5000
        segments = [
            _make_segment(id=1, start_time=0, end_time=60, speaker="A", key_points=["AI"]),
        ]
        transcript = _make_transcript(title="テスト", segments=segments)
        desc = gen._generate_description(transcript)
        assert "【動画概要】" in desc
        assert "チャンネル登録" in desc

    def test_includes_chapters(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        gen.max_description_length = 5000
        segments = [
            _make_segment(id=1, start_time=0, end_time=60, speaker="A", key_points=["AI"]),
            _make_segment(id=2, start_time=60, end_time=120, speaker="B", key_points=["ML"]),
        ]
        transcript = _make_transcript(segments=segments)
        desc = gen._generate_description(transcript)
        assert "【目次】" in desc

    def test_short_limit_creates_shortened(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        gen.max_description_length = 50
        segments = [
            _make_segment(id=1, start_time=0, end_time=60, speaker="A", key_points=["AI"]),
        ]
        transcript = _make_transcript(segments=segments)
        desc = gen._generate_description(transcript)
        assert isinstance(desc, str)


class TestGenerateTags:
    def test_includes_general_tags(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        gen.max_tags_length = 500
        segments = [_make_segment(key_points=["AI"])]
        transcript = _make_transcript(segments=segments)
        tags = gen._generate_tags(transcript)
        assert "解説動画" in tags
        assert "AI" in tags

    def test_max_tags_limit(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        gen.max_tags_length = 500
        segments = [_make_segment(key_points=[f"kw{i}" for i in range(20)])]
        transcript = _make_transcript(segments=segments)
        tags = gen._generate_tags(transcript)
        assert len(tags) <= 15

    def test_tags_length_limit(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        gen.max_tags_length = 30
        segments = [_make_segment(key_points=["AI", "ML", "DL", "NLP"])]
        transcript = _make_transcript(segments=segments)
        tags = gen._generate_tags(transcript)
        total = sum(len(t) for t in tags) + len(tags) - 1
        assert total <= 30


class TestCreateShortenedDescription:
    def test_basic_structure(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        segments = [_make_segment(key_points=["AI"])]
        transcript = _make_transcript(segments=segments)
        desc = gen._create_shortened_description(transcript, "要約文", ["00:00 イントロ"])
        assert "要約文" in desc
        assert "00:00 イントロ" in desc


class TestTemplateManagement:
    def test_create_template(self, tmp_path):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        gen.template_dir = tmp_path
        gen.templates = {"default": {}}
        gen.youtube_settings = {"category_id": "22", "default_language": "ja"}
        metadata = {"title": "テンプレタイトル", "tags": ["tag1"]}
        gen.create_template_from_metadata(metadata, "custom")
        assert "custom" in gen.templates
        assert (tmp_path / "custom.json").exists()

    def test_edit_template(self, tmp_path):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        gen.template_dir = tmp_path
        gen.templates = {"default": {"title_template": "old"}}
        gen.youtube_settings = {"category_id": "22", "default_language": "ja"}
        (tmp_path / "default.json").write_text("{}", encoding="utf-8")
        gen.edit_template("default", {"title_template": "new"})
        assert gen.templates["default"]["title_template"] == "new"

    def test_edit_nonexistent_raises(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        gen.templates = {}
        with pytest.raises(ValueError, match="見つかりません"):
            gen.edit_template("nope", {})

    def test_list_templates(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        gen.templates = {"a": {}, "b": {}}
        result = gen.list_templates()
        assert "a" in result
        assert "b" in result
        assert result is not gen.templates


class TestGenerateMetadataAsync:
    @pytest.mark.asyncio
    async def test_basic_generate(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        gen.max_title_length = 100
        gen.max_description_length = 5000
        gen.max_tags_length = 500
        gen.youtube_settings = {
            "category_id": "22",
            "default_language": "ja",
            "privacy_status": "private",
        }
        gen.templates = {
            "default": {
                "title_template": "{topic} - {key_points}",
                "description_template": "{topic}の解説。{toc}",
                "tags_template": ["{topic}", "解説"],
            }
        }
        segments = [_make_segment(key_points=["AI"])]
        transcript = _make_transcript(title="テスト", segments=segments)
        metadata = await gen.generate_metadata(transcript)
        assert "title" in metadata
        assert "description" in metadata
        assert "tags" in metadata
        assert metadata["category_id"] == "22"

    @pytest.mark.asyncio
    async def test_unknown_template_fallback(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        gen.max_title_length = 100
        gen.max_description_length = 5000
        gen.max_tags_length = 500
        gen.youtube_settings = {
            "category_id": "22",
            "default_language": "ja",
            "privacy_status": "private",
        }
        gen.templates = {
            "default": {
                "title_template": "{topic}",
                "description_template": "{topic}",
                "tags_template": ["{topic}"],
            }
        }
        transcript = _make_transcript(segments=[])
        metadata = await gen.generate_metadata(transcript, template_name="nonexistent")
        assert "title" in metadata


class TestLoadTemplates:
    def test_loads_json_files(self, tmp_path):
        import json
        template_data = {"title_template": "custom {topic}"}
        (tmp_path / "custom.json").write_text(
            json.dumps(template_data), encoding="utf-8"
        )
        gen = MetadataGenerator.__new__(MetadataGenerator)
        gen.template_dir = tmp_path
        gen.youtube_settings = {"category_id": "22", "default_language": "ja"}
        templates = gen._load_templates()
        assert "custom" in templates
        assert "default" in templates

    def test_skips_invalid_json(self, tmp_path):
        (tmp_path / "bad.json").write_text("not json", encoding="utf-8")
        gen = MetadataGenerator.__new__(MetadataGenerator)
        gen.template_dir = tmp_path
        gen.youtube_settings = {"category_id": "22", "default_language": "ja"}
        templates = gen._load_templates()
        assert "bad" not in templates
        assert "default" in templates

    def test_nonexistent_dir(self, tmp_path):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        gen.template_dir = tmp_path / "no_such_dir"
        gen.youtube_settings = {"category_id": "22", "default_language": "ja"}
        templates = gen._load_templates()
        assert "default" in templates


class TestGenerateTocString:
    def test_basic(self):
        gen = MetadataGenerator.__new__(MetadataGenerator)
        segments = [
            _make_segment(id=1, start_time=0, end_time=60, speaker="A", key_points=["AI"]),
            _make_segment(id=2, start_time=60, end_time=120, speaker="B", key_points=["ML"]),
        ]
        transcript = _make_transcript(segments=segments)
        toc = gen._generate_toc_string(transcript)
        assert isinstance(toc, str)

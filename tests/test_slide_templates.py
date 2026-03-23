"""
slide_templates / google_slides_client テンプレート統合テスト

カバー対象:
- LayoutType enum + from_content_hint
- SlideTemplateConfig.from_settings + is_template_mode
- SlideContent.from_dict + format_body_with_keypoints + format_subtitle
- GoogleSlidesClient テンプレート複製方式
- GoogleSlidesClient プログラマティック方式 (テキスト挿入)
- _extract_placeholders
- 三段フォールバック統合 (slide_generator)
"""
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch

from slides.slide_templates import (
    LayoutType,
    SlideContent,
    SlideTemplateConfig,
    PLACEHOLDER_TYPES,
)
from slides.google_slides_client import GoogleSlidesClient
from slides.slide_generator import SlideGenerator, SlideInfo, SlidesPackage
from notebook_lm.transcript_processor import TranscriptInfo, TranscriptSegment


# ---------------------------------------------------------------------------
# LayoutType
# ---------------------------------------------------------------------------

class TestLayoutType:
    def test_from_content_hint_known(self):
        assert LayoutType.from_content_hint("two_column") == LayoutType.TITLE_AND_TWO_COLUMNS
        assert LayoutType.from_content_hint("full_text") == LayoutType.TITLE_AND_BODY
        assert LayoutType.from_content_hint("title") == LayoutType.TITLE
        assert LayoutType.from_content_hint("section_header") == LayoutType.SECTION_HEADER
        assert LayoutType.from_content_hint("emphasis") == LayoutType.SECTION_HEADER
        assert LayoutType.from_content_hint("stats") == LayoutType.TITLE_AND_BODY
        assert LayoutType.from_content_hint("blank") == LayoutType.BLANK

    def test_from_content_hint_unknown_defaults(self):
        assert LayoutType.from_content_hint("unknown") == LayoutType.TITLE_AND_BODY
        assert LayoutType.from_content_hint("") == LayoutType.TITLE_AND_BODY

    def test_from_content_hint_case_insensitive(self):
        assert LayoutType.from_content_hint("Two_Column") == LayoutType.TITLE_AND_TWO_COLUMNS
        assert LayoutType.from_content_hint("TITLE") == LayoutType.TITLE

    def test_from_content_hint_hyphen_normalized(self):
        assert LayoutType.from_content_hint("two-column") == LayoutType.TITLE_AND_TWO_COLUMNS
        assert LayoutType.from_content_hint("section-header") == LayoutType.SECTION_HEADER

    def test_values_are_valid_predefined_layouts(self):
        """Google Slides API の predefinedLayout 値として有効であること"""
        valid_layouts = {
            "TITLE", "TITLE_AND_BODY", "TITLE_AND_TWO_COLUMNS",
            "TITLE_ONLY", "BLANK", "SECTION_HEADER", "ONE_COLUMN_TEXT",
        }
        for lt in LayoutType:
            assert lt.value in valid_layouts


# ---------------------------------------------------------------------------
# SlideTemplateConfig
# ---------------------------------------------------------------------------

class TestSlideTemplateConfig:
    def test_from_settings_with_template_id(self):
        s = {
            "template_presentation_id": "abc123",
            "default_layout": "TITLE_AND_BODY",
        }
        cfg = SlideTemplateConfig.from_settings(s)
        assert cfg.template_presentation_id == "abc123"
        assert cfg.is_template_mode is True
        assert cfg.default_layout == LayoutType.TITLE_AND_BODY

    def test_from_settings_without_template_id(self):
        s = {"template_presentation_id": "", "default_layout": "TITLE"}
        cfg = SlideTemplateConfig.from_settings(s)
        assert cfg.template_presentation_id is None
        assert cfg.is_template_mode is False
        assert cfg.default_layout == LayoutType.TITLE

    def test_from_settings_invalid_layout_defaults(self):
        s = {"default_layout": "INVALID_LAYOUT"}
        cfg = SlideTemplateConfig.from_settings(s)
        assert cfg.default_layout == LayoutType.TITLE_AND_BODY

    def test_from_settings_empty(self):
        cfg = SlideTemplateConfig.from_settings({})
        assert cfg.is_template_mode is False
        assert cfg.default_layout == LayoutType.TITLE_AND_BODY

    def test_placeholder_tags_default(self):
        cfg = SlideTemplateConfig()
        assert cfg.title_placeholder_tag == "{{TITLE}}"
        assert cfg.body_placeholder_tag == "{{BODY}}"
        assert cfg.speaker_placeholder_tag == "{{SPEAKER}}"
        assert cfg.keypoints_placeholder_tag == "{{KEYPOINTS}}"


# ---------------------------------------------------------------------------
# SlideContent
# ---------------------------------------------------------------------------

class TestSlideContent:
    def test_from_dict_basic(self):
        d = {
            "title": "Introduction",
            "text": "Hello world",
            "speakers": ["Host1", "Host2"],
            "key_points": ["Point A", "Point B"],
            "layout": "two_column",
        }
        sc = SlideContent.from_dict(d)
        assert sc.title == "Introduction"
        assert sc.body == "Hello world"
        assert sc.speaker == "Host1, Host2"
        assert sc.key_points == ["Point A", "Point B"]
        assert sc.layout == LayoutType.TITLE_AND_TWO_COLUMNS

    def test_from_dict_content_fallback(self):
        d = {"content": "Alt content", "layout_type": "title_and_body"}
        sc = SlideContent.from_dict(d)
        assert sc.body == "Alt content"
        assert sc.layout == LayoutType.TITLE_AND_BODY

    def test_from_dict_no_layout_uses_default(self):
        d = {"title": "T"}
        sc = SlideContent.from_dict(d, default_layout=LayoutType.SECTION_HEADER)
        assert sc.layout == LayoutType.SECTION_HEADER

    def test_from_dict_no_speakers(self):
        d = {"title": "T"}
        sc = SlideContent.from_dict(d)
        assert sc.speaker == ""

    def test_format_body_with_keypoints(self):
        sc = SlideContent(
            body="Main text",
            key_points=["KP1", "KP2"],
        )
        result = sc.format_body_with_keypoints()
        assert "Main text" in result
        assert "  KP1" in result
        assert "  KP2" in result

    def test_format_body_empty(self):
        sc = SlideContent()
        assert sc.format_body_with_keypoints() == ""

    def test_format_subtitle_with_speaker(self):
        sc = SlideContent(speaker="Host1")
        assert sc.format_subtitle() == "Host1"

    def test_format_subtitle_empty(self):
        sc = SlideContent()
        assert sc.format_subtitle() == ""


# ---------------------------------------------------------------------------
# GoogleSlidesClient._extract_placeholders
# ---------------------------------------------------------------------------

class TestExtractPlaceholders:
    def test_basic_extraction(self):
        slide_page = {
            "pageElements": [
                {
                    "objectId": "title_obj",
                    "shape": {"placeholder": {"type": "TITLE"}},
                },
                {
                    "objectId": "body_obj",
                    "shape": {"placeholder": {"type": "BODY"}},
                },
            ]
        }
        result = GoogleSlidesClient._extract_placeholders(slide_page)
        assert result["TITLE"] == "title_obj"
        assert result["BODY"] == "body_obj"

    def test_duplicate_type_gets_suffix(self):
        slide_page = {
            "pageElements": [
                {"objectId": "body1", "shape": {"placeholder": {"type": "BODY"}}},
                {"objectId": "body2", "shape": {"placeholder": {"type": "BODY"}}},
                {"objectId": "body3", "shape": {"placeholder": {"type": "BODY"}}},
            ]
        }
        result = GoogleSlidesClient._extract_placeholders(slide_page)
        assert result["BODY"] == "body1"
        assert result["BODY_2"] == "body2"
        assert result["BODY_3"] == "body3"

    def test_empty_page(self):
        assert GoogleSlidesClient._extract_placeholders({}) == {}
        assert GoogleSlidesClient._extract_placeholders({"pageElements": []}) == {}

    def test_non_placeholder_elements_ignored(self):
        slide_page = {
            "pageElements": [
                {"objectId": "img1", "shape": {}},
                {"objectId": "txt1", "shape": {"placeholder": {}}},
            ]
        }
        result = GoogleSlidesClient._extract_placeholders(slide_page)
        assert result == {}


# ---------------------------------------------------------------------------
# GoogleSlidesClient テンプレート複製方式
# ---------------------------------------------------------------------------

class TestTemplateMode:
    def test_copy_presentation_success(self):
        client = GoogleSlidesClient()
        mock_drive = MagicMock()
        mock_drive.files().copy().execute.return_value = {"id": "new_pres_id"}
        client._drive_service = mock_drive

        result = client.copy_presentation("template_123", "New Title")
        assert result == "new_pres_id"

    def test_copy_presentation_no_drive(self):
        client = GoogleSlidesClient()
        # _get_drive_service returns None
        result = client.copy_presentation("template_123", "Title")
        assert result is None

    def test_generate_from_template_no_config(self):
        """テンプレートID未設定時は None を返す"""
        client = GoogleSlidesClient(template_config=SlideTemplateConfig())
        result = client.generate_from_template([], "Title")
        assert result is None

    def test_generate_from_template_success(self):
        cfg = SlideTemplateConfig(template_presentation_id="tmpl_id")
        client = GoogleSlidesClient(template_config=cfg)

        # Mock copy + replace
        client.copy_presentation = MagicMock(return_value="copied_id")
        client.replace_template_placeholders = MagicMock(return_value=True)

        contents = [SlideContent(title="T1", body="B1")]
        result = client.generate_from_template(contents, "Title")

        assert result == "copied_id"
        client.copy_presentation.assert_called_once_with("tmpl_id", "Title")
        client.replace_template_placeholders.assert_called_once_with("copied_id", contents)

    def test_generate_from_template_copy_fails(self):
        cfg = SlideTemplateConfig(template_presentation_id="tmpl_id")
        client = GoogleSlidesClient(template_config=cfg)
        client.copy_presentation = MagicMock(return_value=None)

        result = client.generate_from_template([SlideContent()], "Title")
        assert result is None


# ---------------------------------------------------------------------------
# GoogleSlidesClient プログラマティック方式
# ---------------------------------------------------------------------------

class TestProgrammaticMode:
    def test_add_slides_with_content_empty(self):
        """空リストで呼んでもエラーにならない"""
        client = GoogleSlidesClient()
        mock_service = MagicMock()
        client._slides_service = mock_service
        result = client.add_slides_with_content("pres_id", [])
        assert result is True

    def test_add_slides_with_content_no_service(self):
        client = GoogleSlidesClient()
        result = client.add_slides_with_content("pres_id", [SlideContent(title="T")])
        assert result is False

    def test_add_slides_legacy_delegates(self):
        """旧 add_slides が add_slides_with_content に委譲する"""
        client = GoogleSlidesClient()
        client.add_slides_with_content = MagicMock(return_value=True)

        slides = [{"title": "T1", "text": "B1", "layout": "two_column"}]
        result = client.add_slides(  "pres_id", slides)

        assert result is True
        client.add_slides_with_content.assert_called_once()
        args = client.add_slides_with_content.call_args
        contents = args[0][1]
        assert len(contents) == 1
        assert contents[0].title == "T1"
        assert contents[0].layout == LayoutType.TITLE_AND_TWO_COLUMNS

    def test_generate_programmatic_success(self):
        client = GoogleSlidesClient()
        client.create_presentation = MagicMock(return_value="prog_pres_id")
        client.add_slides_with_content = MagicMock(return_value=True)

        contents = [SlideContent(title="T1")]
        result = client.generate_programmatic(contents, "Title")

        assert result == "prog_pres_id"
        client.add_slides_with_content.assert_called_once_with("prog_pres_id", contents)

    def test_generate_programmatic_create_fails(self):
        client = GoogleSlidesClient()
        client.create_presentation = MagicMock(return_value=None)

        result = client.generate_programmatic([SlideContent()], "Title")
        assert result is None


# ---------------------------------------------------------------------------
# replace_template_placeholders
# ---------------------------------------------------------------------------

class TestReplaceTemplatePlaceholders:
    def test_basic_replacement(self):
        client = GoogleSlidesClient()
        mock_service = MagicMock()
        # presentations().get() returns 2 slides
        mock_service.presentations().get().execute.return_value = {
            "slides": [
                {"objectId": "slide1"},
                {"objectId": "slide2"},
            ]
        }
        client._slides_service = mock_service

        contents = [
            SlideContent(title="Title 1", body="Body 1"),
            SlideContent(title="Title 2", body="Body 2", speaker="Host"),
        ]
        result = client.replace_template_placeholders("pres_id", contents)
        assert result is True

        # batchUpdate が呼ばれたことを確認
        batch_call = mock_service.presentations().batchUpdate
        batch_call.assert_called_once()
        call_args = batch_call.call_args
        requests = call_args[1]["body"]["requests"] if "body" in call_args[1] else call_args[0][0]
        # replaceAllText リクエストが含まれている
        assert any("replaceAllText" in r for r in requests)

    def test_excess_slides_deleted(self):
        """テンプレートのスライド数 > コンテンツ数の場合、余剰スライドを削除"""
        client = GoogleSlidesClient()
        mock_service = MagicMock()
        mock_service.presentations().get().execute.return_value = {
            "slides": [
                {"objectId": "slide1"},
                {"objectId": "slide2"},
                {"objectId": "slide3"},
            ]
        }
        client._slides_service = mock_service

        contents = [SlideContent(title="Only One")]
        result = client.replace_template_placeholders("pres_id", contents)
        assert result is True

        call_args = mock_service.presentations().batchUpdate.call_args
        body_requests = call_args[1]["body"]["requests"] if "body" in call_args[1] else []
        delete_requests = [r for r in body_requests if "deleteObject" in r]
        assert len(delete_requests) == 2  # slide2, slide3 を削除

    def test_no_service_returns_false(self):
        client = GoogleSlidesClient()
        result = client.replace_template_placeholders("pres_id", [])
        assert result is False


# ---------------------------------------------------------------------------
# SlideGenerator 三段フォールバック
# ---------------------------------------------------------------------------

def _mock_settings():
    s = MagicMock()
    s.SLIDES_SETTINGS = {
        "max_chars_per_slide": 200,
        "max_slides_per_batch": 20,
        "theme": "business",
        "prefer_gemini_slide_content": False,
        "template_presentation_id": "",
        "default_layout": "TITLE_AND_BODY",
    }
    s.SLIDES_DIR = Path("/tmp/test_slides")
    s.SLIDES_IMAGES_DIR = Path("/tmp/test_slides/images")
    return s


def _mock_settings_with_template():
    s = _mock_settings()
    s.SLIDES_SETTINGS["template_presentation_id"] = "template_abc"
    return s


def _make_transcript(title="Test", segments=2):
    segs = [
        TranscriptSegment(
            id=i, start_time=float(i * 30), end_time=float((i + 1) * 30),
            speaker="Host", text=f"Segment {i} content.",
            key_points=[f"point{i}"], slide_suggestion=f"Slide {i}",
            confidence_score=0.95,
        )
        for i in range(1, segments + 1)
    ]
    return TranscriptInfo(
        title=title, total_duration=float(segments * 30),
        segments=segs, accuracy_score=0.95,
        created_at=datetime.now(), source_audio_path="mock.mp3",
    )


class TestSlideGeneratorThreeFallback:
    @pytest.mark.asyncio
    @patch("slides.slide_generator.settings")
    @patch("slides.slide_generator.GoogleSlidesClient")
    async def test_template_mode_success(self, MockClient, mock_settings):
        """テンプレート複製方式が成功するパス"""
        mock_settings.SLIDES_SETTINGS = _mock_settings_with_template().SLIDES_SETTINGS
        mock_settings.SLIDES_DIR = Path("/tmp/test_slides")
        mock_settings.SLIDES_IMAGES_DIR = Path("/tmp/test_slides/images")

        client_instance = MockClient.return_value
        client_instance.generate_from_template.return_value = "tmpl_pres_id"
        client_instance.export_pptx.return_value = True
        client_instance.export_thumbnails.return_value = []

        gen = SlideGenerator()
        contents = [{"title": "S1", "text": "Body 1", "duration": 10.0}]

        result = await gen._generate_slides_with_google(contents, "Template Test")

        assert result.presentation_id == "tmpl_pres_id"
        assert result.total_slides == 1
        client_instance.generate_from_template.assert_called_once()

    @pytest.mark.asyncio
    @patch("slides.slide_generator.settings")
    @patch("slides.slide_generator.GoogleSlidesClient")
    async def test_template_fails_programmatic_succeeds(self, MockClient, mock_settings):
        """テンプレート失敗 -> プログラマティック成功"""
        mock_settings.SLIDES_SETTINGS = _mock_settings_with_template().SLIDES_SETTINGS
        mock_settings.SLIDES_DIR = Path("/tmp/test_slides")
        mock_settings.SLIDES_IMAGES_DIR = Path("/tmp/test_slides/images")

        client_instance = MockClient.return_value
        client_instance.generate_from_template.return_value = None
        client_instance.generate_programmatic.return_value = "prog_pres_id"
        client_instance.export_pptx.return_value = True
        client_instance.export_thumbnails.return_value = []

        gen = SlideGenerator()
        contents = [{"title": "S1", "text": "Body", "duration": 10.0}]

        result = await gen._generate_slides_with_google(contents, "Fallback Test")

        assert result.presentation_id == "prog_pres_id"
        client_instance.generate_from_template.assert_called_once()
        client_instance.generate_programmatic.assert_called_once()

    @pytest.mark.asyncio
    @patch("slides.slide_generator.settings")
    @patch("slides.slide_generator.GoogleSlidesClient")
    async def test_all_api_fail_mock_fallback(self, MockClient, mock_settings):
        """全API失敗 -> モックフォールバック"""
        mock_settings.SLIDES_SETTINGS = _mock_settings_with_template().SLIDES_SETTINGS
        mock_settings.SLIDES_DIR = Path("/tmp/test_slides")
        mock_settings.SLIDES_IMAGES_DIR = Path("/tmp/test_slides/images")

        client_instance = MockClient.return_value
        client_instance.generate_from_template.return_value = None
        client_instance.generate_programmatic.return_value = None

        gen = SlideGenerator()
        contents = [{"title": "S1", "text": "Body", "duration": 10.0}]

        result = await gen._generate_slides_with_google(contents, "Mock Test")

        assert result.presentation_id.startswith("mock_")
        assert result.total_slides == 1

    @pytest.mark.asyncio
    @patch("slides.slide_generator.settings")
    @patch("slides.slide_generator.GoogleSlidesClient")
    async def test_no_template_config_skips_template(self, MockClient, mock_settings):
        """テンプレートID未設定時はテンプレート方式をスキップ"""
        mock_settings.SLIDES_SETTINGS = _mock_settings().SLIDES_SETTINGS
        mock_settings.SLIDES_DIR = Path("/tmp/test_slides")
        mock_settings.SLIDES_IMAGES_DIR = Path("/tmp/test_slides/images")

        client_instance = MockClient.return_value
        client_instance.generate_programmatic.return_value = "prog_only_id"
        client_instance.export_pptx.return_value = True
        client_instance.export_thumbnails.return_value = []

        gen = SlideGenerator()
        contents = [{"title": "S1", "text": "Body", "duration": 10.0}]

        result = await gen._generate_slides_with_google(contents, "No Template")

        assert result.presentation_id == "prog_only_id"
        # テンプレート方式は呼ばれない (template_config.is_template_mode == False)
        client_instance.generate_from_template.assert_not_called()


# ---------------------------------------------------------------------------
# 既存テスト互換性: SlideInfo / SlidesPackage の後方互換
# ---------------------------------------------------------------------------

class TestBackwardCompatibility:
    def test_slide_info_layout_compat(self):
        info = SlideInfo(slide_id=1, title="T", content="C", layout="two_column")
        assert info.layout_type == "two_column"

    def test_slide_info_duration_compat(self):
        info = SlideInfo(slide_id=1, title="T", content="C", duration=42.0)
        assert info.estimated_duration == 42.0

    def test_slides_package_defaults(self):
        pkg = SlidesPackage(presentation_id="test")
        assert pkg.slides == []
        assert pkg.total_slides == 0


# ---------------------------------------------------------------------------
# PLACEHOLDER_TYPES 定義の整合性
# ---------------------------------------------------------------------------

class TestPlaceholderTypes:
    def test_all_layout_types_have_entry(self):
        for lt in LayoutType:
            assert lt in PLACEHOLDER_TYPES, f"{lt} missing from PLACEHOLDER_TYPES"

    def test_placeholder_types_are_lists(self):
        for lt, phs in PLACEHOLDER_TYPES.items():
            assert isinstance(phs, list), f"{lt}: expected list, got {type(phs)}"

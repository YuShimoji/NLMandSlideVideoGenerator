"""
slide_generator 拡張テスト — 未カバー行を網羅するユニットテスト

カバー対象:
- SlideInfo.__post_init__ (layout/duration compat): L36, L38
- SlidesPackage.__post_init__: L59
- authenticate(): L73-79
- generate_slides() bundle path: L113-114
- generate_slides() exception re-raise: L136-138
- _generate_slides_with_google() API path: L163-219
- _generate_slides_from_bundle(): L261-312
- create_slides_from_content(): L320-346
- _download_slides_file() pptx path + exception: L376-408
"""
import sys
import types
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest

from slides.slide_generator import SlideGenerator, SlideInfo, SlidesPackage
from notebook_lm.transcript_processor import TranscriptInfo, TranscriptSegment


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_transcript(title: str = "Test", segments: int = 2) -> TranscriptInfo:
    segs = [
        TranscriptSegment(
            id=i,
            start_time=float(i * 30),
            end_time=float((i + 1) * 30),
            speaker="Host",
            text=f"Segment {i} content.",
            key_points=[f"point{i}"],
            slide_suggestion=f"Slide {i}",
            confidence_score=0.95,
        )
        for i in range(1, segments + 1)
    ]
    return TranscriptInfo(
        title=title,
        total_duration=float(segments * 30),
        segments=segs,
        accuracy_score=0.95,
        created_at=datetime.now(),
        source_audio_path="mock.mp3",
    )


def _mock_settings():
    """settings のモックを返す。SlideGenerator.__init__ に必要な属性を持つ。"""
    s = MagicMock()
    s.SLIDES_SETTINGS = {
        "max_chars_per_slide": 200,
        "max_slides_per_batch": 20,
        "theme": "business",
        "prefer_gemini_slide_content": False,
    }
    s.SLIDES_DIR = Path("/tmp/test_slides")
    s.SLIDES_IMAGES_DIR = Path("/tmp/test_slides/images")
    return s


# ---------------------------------------------------------------------------
# SlideInfo.__post_init__  (L36, L38)
# ---------------------------------------------------------------------------

class TestSlideInfoCompat:
    def test_layout_compat_field(self):
        """旧 layout フィールドが layout_type へ反映される"""
        info = SlideInfo(
            slide_id=1,
            title="T",
            content="C",
            layout="two_column",
        )
        assert info.layout_type == "two_column"

    def test_duration_compat_field(self):
        """旧 duration フィールドが estimated_duration へ反映される"""
        info = SlideInfo(
            slide_id=1,
            title="T",
            content="C",
            duration=42.0,
        )
        assert info.estimated_duration == 42.0

    def test_new_fields_take_precedence(self):
        """layout_type / estimated_duration が既に設定されていれば上書きしない"""
        info = SlideInfo(
            slide_id=1,
            title="T",
            content="C",
            layout_type="custom",
            estimated_duration=99.0,
            layout="old_layout",
            duration=1.0,
        )
        assert info.layout_type == "custom"
        assert info.estimated_duration == 99.0

    def test_both_none(self):
        """旧フィールドも新フィールドも None のケース"""
        info = SlideInfo(slide_id=1, title="T", content="C")
        assert info.layout_type is None
        assert info.estimated_duration is None


# ---------------------------------------------------------------------------
# SlidesPackage.__post_init__  (L59)
# ---------------------------------------------------------------------------

class TestSlidesPackagePostInit:
    def test_slides_defaults_to_empty_list(self):
        """slides=None で初期化すると空リストになる"""
        pkg = SlidesPackage(presentation_id="test")
        assert pkg.slides == []

    def test_slides_preserved_when_given(self):
        slide = SlideInfo(slide_id=1, title="T", content="C")
        pkg = SlidesPackage(presentation_id="test", slides=[slide])
        assert len(pkg.slides) == 1
        assert pkg.slides[0].slide_id == 1


# ---------------------------------------------------------------------------
# authenticate()  (L73-79)
# ---------------------------------------------------------------------------

class TestAuthenticate:
    @pytest.mark.asyncio
    @patch("slides.slide_generator.settings", new_callable=_mock_settings)
    @patch("slides.slide_generator.GoogleSlidesClient")
    async def test_authenticate_available(self, MockClient, mock_settings):
        instance = MockClient.return_value
        instance.is_available.return_value = True

        gen = SlideGenerator()
        result = await gen.authenticate()

        assert result is True
        instance.is_available.assert_called_once()

    @pytest.mark.asyncio
    @patch("slides.slide_generator.settings", new_callable=_mock_settings)
    @patch("slides.slide_generator.GoogleSlidesClient")
    async def test_authenticate_not_available(self, MockClient, mock_settings):
        instance = MockClient.return_value
        instance.is_available.return_value = False

        gen = SlideGenerator()
        result = await gen.authenticate()

        assert result is False


# ---------------------------------------------------------------------------
# generate_slides() — bundle path  (L113-114)
# ---------------------------------------------------------------------------

class TestGenerateSlidesBundlePath:
    @pytest.mark.asyncio
    @patch("slides.slide_generator.settings")
    async def test_prefer_bundle_routes_to_bundle_generator(self, mock_settings):
        mock_settings.SLIDES_SETTINGS = {
            "max_chars_per_slide": 200,
            "max_slides_per_batch": 20,
            "theme": "business",
            "prefer_gemini_slide_content": True,
        }
        mock_settings.SLIDES_DIR = Path("/tmp/test_slides")
        mock_settings.SLIDES_IMAGES_DIR = Path("/tmp/test_slides/images")

        gen = SlideGenerator()

        expected_pkg = SlidesPackage(presentation_id="bundle_test", slides=[], total_slides=0)
        gen._generate_slides_from_bundle = AsyncMock(return_value=expected_pkg)

        transcript = _make_transcript()
        bundle = {
            "title": "Bundle Title",
            "slides": [
                {"title": "S1", "content": "C1", "duration": 10.0},
            ],
        }

        result = await gen.generate_slides(transcript, max_slides=10, script_bundle=bundle)

        gen._generate_slides_from_bundle.assert_awaited_once_with(bundle, 10)
        assert result.presentation_id == "bundle_test"


# ---------------------------------------------------------------------------
# generate_slides() — exception re-raise  (L136-138)
# ---------------------------------------------------------------------------

class TestGenerateSlidesExceptionReRaise:
    @pytest.mark.asyncio
    @patch("slides.slide_generator.settings")
    async def test_exception_is_reraised(self, mock_settings):
        mock_settings.SLIDES_SETTINGS = {
            "max_chars_per_slide": 200,
            "max_slides_per_batch": 20,
            "theme": "business",
            "prefer_gemini_slide_content": False,
        }
        mock_settings.SLIDES_DIR = Path("/tmp/test_slides")
        mock_settings.SLIDES_IMAGES_DIR = Path("/tmp/test_slides/images")

        gen = SlideGenerator()
        gen.content_splitter = MagicMock()
        gen.content_splitter.split_for_slides = AsyncMock(
            side_effect=RuntimeError("split failure")
        )

        transcript = _make_transcript()
        with pytest.raises(RuntimeError, match="split failure"):
            await gen.generate_slides(transcript, max_slides=5)


# ---------------------------------------------------------------------------
# _generate_slides_with_google() — API success path  (L163-219)
# ---------------------------------------------------------------------------

class TestGenerateSlidesWithGoogle:
    @pytest.mark.asyncio
    @patch("slides.slide_generator.settings")
    @patch("slides.slide_generator.GoogleSlidesClient")
    async def test_api_success_path(self, MockClient, mock_settings):
        mock_settings.SLIDES_SETTINGS = {
            "max_chars_per_slide": 200,
            "max_slides_per_batch": 20,
            "theme": "business",
            "prefer_gemini_slide_content": False,
            "template_presentation_id": "",
            "default_layout": "TITLE_AND_BODY",
        }
        mock_settings.SLIDES_DIR = Path("/tmp/test_slides")
        mock_settings.SLIDES_IMAGES_DIR = Path("/tmp/test_slides/images")

        client_instance = MockClient.return_value
        client_instance.generate_programmatic.return_value = "pres_abc123"
        client_instance.export_pptx.return_value = True
        client_instance.export_thumbnails.return_value = []

        gen = SlideGenerator()
        contents = [
            {"title": "Introduction", "text": "Hello world", "duration": 10.0, "layout": "title_and_content"},
            {"title": "Body", "text": "Main content", "duration": 20.0, "speakers": ["Host"]},
        ]

        result = await gen._generate_slides_with_google(contents, "Test Presentation")

        assert result.presentation_id == "pres_abc123"
        assert result.total_slides == 2
        assert result.slides[0].title == "Introduction"
        assert result.slides[0].content == "Hello world"
        assert result.slides[1].speakers == ["Host"]
        client_instance.generate_programmatic.assert_called_once()
        client_instance.export_pptx.assert_called_once()
        client_instance.export_thumbnails.assert_called_once()

    @pytest.mark.asyncio
    @patch("slides.slide_generator.settings")
    @patch("slides.slide_generator.GoogleSlidesClient")
    async def test_api_create_presentation_failure_falls_back_to_mock(self, MockClient, mock_settings):
        mock_settings.SLIDES_SETTINGS = {
            "max_chars_per_slide": 200,
            "max_slides_per_batch": 20,
            "theme": "business",
            "prefer_gemini_slide_content": False,
            "template_presentation_id": "",
            "default_layout": "TITLE_AND_BODY",
        }
        mock_settings.SLIDES_DIR = Path("/tmp/test_slides")
        mock_settings.SLIDES_IMAGES_DIR = Path("/tmp/test_slides/images")

        client_instance = MockClient.return_value
        client_instance.generate_programmatic.side_effect = Exception("API down")

        gen = SlideGenerator()
        contents = [{"title": "S1", "text": "content", "duration": 15.0}]

        result = await gen._generate_slides_with_google(contents, "Fallback Test")

        # generate_programmatic が例外 -> presentation_id が None -> モックフォールバック
        assert result.presentation_id.startswith("mock_")
        assert result.total_slides == 1
        assert result.slides[0].title == "S1"

    @pytest.mark.asyncio
    @patch("slides.slide_generator.settings")
    @patch("slides.slide_generator.GoogleSlidesClient")
    async def test_api_programmatic_returns_id_despite_internal_issues(self, MockClient, mock_settings):
        """generate_programmatic が ID を返せばスライド生成は続行される"""
        mock_settings.SLIDES_SETTINGS = {
            "max_chars_per_slide": 200,
            "max_slides_per_batch": 20,
            "theme": "business",
            "prefer_gemini_slide_content": False,
            "template_presentation_id": "",
            "default_layout": "TITLE_AND_BODY",
        }
        mock_settings.SLIDES_DIR = Path("/tmp/test_slides")
        mock_settings.SLIDES_IMAGES_DIR = Path("/tmp/test_slides/images")

        client_instance = MockClient.return_value
        client_instance.generate_programmatic.return_value = "pres_xyz"
        client_instance.export_pptx.return_value = True
        client_instance.export_thumbnails.return_value = []

        gen = SlideGenerator()
        contents = [{"title": "S1", "text": "c", "duration": 5.0}]

        result = await gen._generate_slides_with_google(contents, "Programmatic Test")

        assert result.presentation_id == "pres_xyz"
        assert result.total_slides == 1

    @pytest.mark.asyncio
    @patch("slides.slide_generator.settings")
    @patch("slides.slide_generator.GoogleSlidesClient")
    async def test_api_export_failures_do_not_raise(self, MockClient, mock_settings):
        """export_pptx / export_thumbnails 失敗でも例外伝播しない"""
        mock_settings.SLIDES_SETTINGS = {
            "max_chars_per_slide": 200,
            "max_slides_per_batch": 20,
            "theme": "business",
            "prefer_gemini_slide_content": False,
            "template_presentation_id": "",
            "default_layout": "TITLE_AND_BODY",
        }
        mock_settings.SLIDES_DIR = Path("/tmp/test_slides")
        mock_settings.SLIDES_IMAGES_DIR = Path("/tmp/test_slides/images")

        client_instance = MockClient.return_value
        client_instance.generate_programmatic.return_value = "pres_export_fail"
        client_instance.export_pptx.side_effect = ImportError("no pptx")
        client_instance.export_thumbnails.side_effect = RuntimeError("thumb fail")

        gen = SlideGenerator()
        contents = [{"title": "S1", "text": "c", "duration": 5.0}]

        result = await gen._generate_slides_with_google(contents, "Export Fail Test")
        assert result.presentation_id == "pres_export_fail"

    @pytest.mark.asyncio
    @patch("slides.slide_generator.settings")
    @patch("slides.slide_generator.GoogleSlidesClient")
    async def test_api_returns_none_falls_back(self, MockClient, mock_settings):
        """generate_programmatic が None を返すとモックフォールバック"""
        mock_settings.SLIDES_SETTINGS = {
            "max_chars_per_slide": 200,
            "max_slides_per_batch": 20,
            "theme": "business",
            "prefer_gemini_slide_content": False,
            "template_presentation_id": "",
            "default_layout": "TITLE_AND_BODY",
        }
        mock_settings.SLIDES_DIR = Path("/tmp/test_slides")
        mock_settings.SLIDES_IMAGES_DIR = Path("/tmp/test_slides/images")

        client_instance = MockClient.return_value
        client_instance.generate_programmatic.return_value = None

        gen = SlideGenerator()
        contents = [
            {"title": "S1", "text": "content1", "content": "alt_content", "duration": 10.0},
        ]

        result = await gen._generate_slides_with_google(contents, "None PID Test")
        assert result.presentation_id.startswith("mock_")
        # text フィールド優先、なければ content へフォールバック
        assert result.slides[0].content == "content1"


# ---------------------------------------------------------------------------
# _generate_slides_from_bundle()  (L261-312)
# ---------------------------------------------------------------------------

class TestGenerateSlidesFromBundle:
    @pytest.mark.asyncio
    @patch("slides.slide_generator.settings")
    async def test_basic_bundle(self, mock_settings):
        mock_settings.SLIDES_SETTINGS = {
            "max_chars_per_slide": 200,
            "max_slides_per_batch": 20,
            "theme": "business",
            "prefer_gemini_slide_content": False,
        }
        mock_settings.SLIDES_DIR = Path("/tmp/test_slides")
        mock_settings.SLIDES_IMAGES_DIR = Path("/tmp/test_slides/images")

        gen = SlideGenerator()
        gen._download_slides_file = AsyncMock()
        gen._save_slides_metadata = AsyncMock()

        bundle = {
            "title": "Bundle Presentation",
            "slides": [
                {"title": "Intro", "content": "Welcome", "layout": "two_column", "duration": 20.0, "image_suggestions": ["img1"]},
                {"title": "Body", "content": "Details", "images": ["img2", "img3"]},
            ],
        }

        result = await gen._generate_slides_from_bundle(bundle, max_slides=10)

        assert result.total_slides == 2
        assert result.slides[0].title == "Intro"
        assert result.slides[0].layout_type == "two_column"
        assert result.slides[0].estimated_duration == 20.0
        assert result.slides[0].image_suggestions == ["img1"]
        # images フォールバック
        assert result.slides[1].image_suggestions == ["img2", "img3"]
        assert result.title == "Bundle Presentation"
        assert result.presentation_id.startswith("notebooklm_")
        gen._download_slides_file.assert_awaited_once()
        gen._save_slides_metadata.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("slides.slide_generator.settings")
    async def test_bundle_max_slides_limit(self, mock_settings):
        mock_settings.SLIDES_SETTINGS = {
            "max_chars_per_slide": 200,
            "max_slides_per_batch": 20,
            "theme": "business",
            "prefer_gemini_slide_content": False,
        }
        mock_settings.SLIDES_DIR = Path("/tmp/test_slides")
        mock_settings.SLIDES_IMAGES_DIR = Path("/tmp/test_slides/images")

        gen = SlideGenerator()
        gen._download_slides_file = AsyncMock()
        gen._save_slides_metadata = AsyncMock()

        bundle = {
            "title": "Many Slides",
            "slides": [{"title": f"S{i}", "content": f"C{i}"} for i in range(20)],
        }

        result = await gen._generate_slides_from_bundle(bundle, max_slides=5)
        assert result.total_slides == 5

    @pytest.mark.asyncio
    @patch("slides.slide_generator.settings")
    async def test_bundle_segments_fallback(self, mock_settings):
        """slides が足りない場合に segments から補完される"""
        mock_settings.SLIDES_SETTINGS = {
            "max_chars_per_slide": 200,
            "max_slides_per_batch": 20,
            "theme": "business",
            "prefer_gemini_slide_content": False,
        }
        mock_settings.SLIDES_DIR = Path("/tmp/test_slides")
        mock_settings.SLIDES_IMAGES_DIR = Path("/tmp/test_slides/images")

        gen = SlideGenerator()
        gen._download_slides_file = AsyncMock()
        gen._save_slides_metadata = AsyncMock()

        bundle = {
            "title": "Sparse Bundle",
            "slides": [
                {"title": "Only Slide", "content": "Content"},
            ],
            "segments": [
                {"content": "Segment 1 content", "duration": 10.0},
                {"content": "Segment 2 content", "duration": 12.0},
                {"content": "Segment 3 content", "duration": 8.0},
            ],
        }

        result = await gen._generate_slides_from_bundle(bundle, max_slides=4)

        # 1 slide + 2 segments (segments[1:] up to max_slides=4)
        assert result.total_slides == 3
        assert result.slides[0].title == "Only Slide"
        assert result.slides[1].title == "セグメント 2"
        assert result.slides[1].content == "Segment 2 content"
        assert result.slides[2].estimated_duration == 8.0

    @pytest.mark.asyncio
    @patch("slides.slide_generator.settings")
    async def test_bundle_default_title(self, mock_settings):
        """title がバンドルに無い場合のデフォルト"""
        mock_settings.SLIDES_SETTINGS = {
            "max_chars_per_slide": 200,
            "max_slides_per_batch": 20,
            "theme": "business",
            "prefer_gemini_slide_content": False,
        }
        mock_settings.SLIDES_DIR = Path("/tmp/test_slides")
        mock_settings.SLIDES_IMAGES_DIR = Path("/tmp/test_slides/images")

        gen = SlideGenerator()
        gen._download_slides_file = AsyncMock()
        gen._save_slides_metadata = AsyncMock()

        bundle = {"slides": [{"title": "S1", "content": "C1"}]}

        result = await gen._generate_slides_from_bundle(bundle, max_slides=5)
        assert result.title == "NotebookLM Presentation"

    @pytest.mark.asyncio
    @patch("slides.slide_generator.settings")
    async def test_bundle_empty_slides(self, mock_settings):
        """slides が空で segments もない場合"""
        mock_settings.SLIDES_SETTINGS = {
            "max_chars_per_slide": 200,
            "max_slides_per_batch": 20,
            "theme": "business",
            "prefer_gemini_slide_content": False,
        }
        mock_settings.SLIDES_DIR = Path("/tmp/test_slides")
        mock_settings.SLIDES_IMAGES_DIR = Path("/tmp/test_slides/images")

        gen = SlideGenerator()
        gen._download_slides_file = AsyncMock()
        gen._save_slides_metadata = AsyncMock()

        bundle = {"slides": []}

        result = await gen._generate_slides_from_bundle(bundle, max_slides=10)
        assert result.total_slides == 0
        assert result.slides == []


# ---------------------------------------------------------------------------
# create_slides_from_content()  (L320-346)
# ---------------------------------------------------------------------------

class TestCreateSlidesFromContent:
    @pytest.mark.asyncio
    @patch("slides.slide_generator.settings")
    async def test_basic_creation(self, mock_settings):
        mock_settings.SLIDES_SETTINGS = {
            "max_chars_per_slide": 200,
            "max_slides_per_batch": 20,
            "theme": "business",
            "prefer_gemini_slide_content": False,
        }
        mock_settings.SLIDES_DIR = Path("/tmp/test_slides")
        mock_settings.SLIDES_IMAGES_DIR = Path("/tmp/test_slides/images")

        gen = SlideGenerator()
        gen._download_slides_file = AsyncMock()
        gen._save_slides_metadata = AsyncMock()

        contents: List[Dict[str, Any]] = [
            {
                "slide_id": 10,
                "title": "Custom Title",
                "content": "Custom content",
                "layout_type": "two_column",
                "duration": 25.0,
                "image_suggestions": ["img1"],
                "speakers": ["Alice"],
            },
            {
                "text": "Fallback text field",
                "layout": "title_only",
                "images": ["img2"],
            },
        ]

        result = await gen.create_slides_from_content(contents, "My Presentation")

        assert result.total_slides == 2
        assert result.title == "My Presentation"
        assert result.presentation_id.startswith("presentation_")
        # First slide: explicit fields
        assert result.slides[0].slide_id == 10
        assert result.slides[0].title == "Custom Title"
        assert result.slides[0].content == "Custom content"
        assert result.slides[0].layout_type == "two_column"
        assert result.slides[0].estimated_duration == 25.0
        assert result.slides[0].image_suggestions == ["img1"]
        assert result.slides[0].speakers == ["Alice"]
        # Second slide: fallback fields
        assert result.slides[1].slide_id == 2
        assert result.slides[1].content == "Fallback text field"
        assert result.slides[1].layout_type == "title_only"
        assert result.slides[1].image_suggestions == ["img2"]
        assert result.slides[1].estimated_duration == 15.0  # default

        gen._download_slides_file.assert_awaited_once()
        gen._save_slides_metadata.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("slides.slide_generator.settings")
    async def test_empty_content_list(self, mock_settings):
        mock_settings.SLIDES_SETTINGS = {
            "max_chars_per_slide": 200,
            "max_slides_per_batch": 20,
            "theme": "business",
            "prefer_gemini_slide_content": False,
        }
        mock_settings.SLIDES_DIR = Path("/tmp/test_slides")
        mock_settings.SLIDES_IMAGES_DIR = Path("/tmp/test_slides/images")

        gen = SlideGenerator()
        gen._download_slides_file = AsyncMock()
        gen._save_slides_metadata = AsyncMock()

        result = await gen.create_slides_from_content([], "Empty")
        assert result.total_slides == 0
        assert result.slides == []


# ---------------------------------------------------------------------------
# _download_slides_file()  (L376-408)
# ---------------------------------------------------------------------------

class TestDownloadSlidesFile:
    @pytest.mark.asyncio
    @patch("slides.slide_generator.settings")
    async def test_existing_file_skipped(self, mock_settings, tmp_path):
        """既存ファイルがある場合ダウンロードをスキップ"""
        mock_settings.SLIDES_SETTINGS = {
            "max_chars_per_slide": 200,
            "max_slides_per_batch": 20,
            "theme": "business",
            "prefer_gemini_slide_content": False,
        }
        mock_settings.SLIDES_DIR = tmp_path
        mock_settings.SLIDES_IMAGES_DIR = tmp_path / "images"

        gen = SlideGenerator()

        existing = tmp_path / "existing.pptx"
        existing.write_bytes(b"dummy pptx data")

        pkg = SlidesPackage(file_path=existing, presentation_id="test")

        await gen._download_slides_file(pkg)
        # ファイル内容が変わっていないことを確認
        assert existing.read_bytes() == b"dummy pptx data"

    @pytest.mark.asyncio
    @patch("slides.slide_generator.settings")
    async def test_pptx_import_error_creates_empty_file(self, mock_settings, tmp_path):
        """python-pptx が無い場合、空ファイルを作成"""
        mock_settings.SLIDES_SETTINGS = {
            "max_chars_per_slide": 200,
            "max_slides_per_batch": 20,
            "theme": "business",
            "prefer_gemini_slide_content": False,
        }
        mock_settings.SLIDES_DIR = tmp_path
        mock_settings.SLIDES_IMAGES_DIR = tmp_path / "images"

        gen = SlideGenerator()

        out_file = tmp_path / "no_pptx.pptx"
        pkg = SlidesPackage(
            file_path=out_file,
            presentation_id="test_nopptx",
            slides=[SlideInfo(slide_id=1, title="T", content="C")],
        )

        with patch.dict(sys.modules, {"pptx": None}):
            # pptx を import 不可にする
            import builtins
            original_import = builtins.__import__

            def mock_import(name, *args, **kwargs):
                if name == "pptx":
                    raise ImportError("No module named 'pptx'")
                return original_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=mock_import):
                await gen._download_slides_file(pkg)

        assert out_file.exists()
        assert out_file.read_bytes() == b""

    @pytest.mark.asyncio
    @patch("slides.slide_generator.settings")
    async def test_pptx_generation_success(self, mock_settings, tmp_path):
        """python-pptx が利用可能な場合の正常パス"""
        mock_settings.SLIDES_SETTINGS = {
            "max_chars_per_slide": 200,
            "max_slides_per_batch": 20,
            "theme": "business",
            "prefer_gemini_slide_content": False,
        }
        mock_settings.SLIDES_DIR = tmp_path
        mock_settings.SLIDES_IMAGES_DIR = tmp_path / "images"

        gen = SlideGenerator()

        out_file = tmp_path / "gen.pptx"
        slides = [
            SlideInfo(slide_id=1, title="Slide 1", content="Content 1"),
            SlideInfo(slide_id=2, title="Slide 2", content="Content 2"),
        ]
        pkg = SlidesPackage(
            file_path=out_file,
            presentation_id="test_gen",
            slides=slides,
        )

        # Mock the pptx module
        mock_placeholder_1 = MagicMock()
        mock_placeholders = MagicMock()
        mock_placeholders.__len__ = MagicMock(return_value=2)
        mock_placeholders.__getitem__ = MagicMock(return_value=mock_placeholder_1)

        mock_slide = MagicMock()
        mock_slide.shapes.title.text = ""
        mock_slide.shapes.placeholders = mock_placeholders

        mock_slide_layout = MagicMock()
        mock_prs = MagicMock()
        mock_prs.slide_layouts = [mock_slide_layout, mock_slide_layout]
        mock_prs.slides.add_slide.return_value = mock_slide

        mock_presentation_cls = MagicMock(return_value=mock_prs)

        with patch.dict(sys.modules, {"pptx": MagicMock(Presentation=mock_presentation_cls)}):
            # Override the import inside _download_slides_file
            import builtins
            original_import = builtins.__import__

            def mock_import(name, *args, **kwargs):
                if name == "pptx":
                    mod = MagicMock()
                    mod.Presentation = mock_presentation_cls
                    return mod
                return original_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=mock_import):
                await gen._download_slides_file(pkg)

        mock_prs.save.assert_called_once_with(str(out_file))

    @pytest.mark.asyncio
    @patch("slides.slide_generator.settings")
    async def test_pptx_generation_os_error(self, mock_settings, tmp_path):
        """PPTX生成中にOSErrorが発生した場合、空ファイルを作成"""
        mock_settings.SLIDES_SETTINGS = {
            "max_chars_per_slide": 200,
            "max_slides_per_batch": 20,
            "theme": "business",
            "prefer_gemini_slide_content": False,
        }
        mock_settings.SLIDES_DIR = tmp_path
        mock_settings.SLIDES_IMAGES_DIR = tmp_path / "images"

        gen = SlideGenerator()

        out_file = tmp_path / "oserr.pptx"
        pkg = SlidesPackage(
            file_path=out_file,
            presentation_id="test_oserr",
            slides=[SlideInfo(slide_id=1, title="T", content="C")],
        )

        mock_presentation_cls = MagicMock(side_effect=OSError("disk full"))

        import builtins
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "pptx":
                mod = MagicMock()
                mod.Presentation = mock_presentation_cls
                return mod
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            await gen._download_slides_file(pkg)

        assert out_file.exists()
        assert out_file.read_bytes() == b""

    @pytest.mark.asyncio
    @patch("slides.slide_generator.settings")
    async def test_pptx_generation_generic_exception(self, mock_settings, tmp_path):
        """PPTX生成中に汎用Exceptionが発生した場合、空ファイルを作成"""
        mock_settings.SLIDES_SETTINGS = {
            "max_chars_per_slide": 200,
            "max_slides_per_batch": 20,
            "theme": "business",
            "prefer_gemini_slide_content": False,
        }
        mock_settings.SLIDES_DIR = tmp_path
        mock_settings.SLIDES_IMAGES_DIR = tmp_path / "images"

        gen = SlideGenerator()

        out_file = tmp_path / "generic_err.pptx"
        pkg = SlidesPackage(
            file_path=out_file,
            presentation_id="test_generic_err",
            slides=[SlideInfo(slide_id=1, title="T", content="C")],
        )

        mock_presentation_cls = MagicMock(side_effect=Exception("unexpected"))

        import builtins
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "pptx":
                mod = MagicMock()
                mod.Presentation = mock_presentation_cls
                return mod
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            await gen._download_slides_file(pkg)

        assert out_file.exists()
        assert out_file.read_bytes() == b""

    @pytest.mark.asyncio
    @patch("slides.slide_generator.settings")
    async def test_file_path_none(self, mock_settings, tmp_path):
        """file_path が None の場合でもエラーにならない"""
        mock_settings.SLIDES_SETTINGS = {
            "max_chars_per_slide": 200,
            "max_slides_per_batch": 20,
            "theme": "business",
            "prefer_gemini_slide_content": False,
        }
        mock_settings.SLIDES_DIR = tmp_path
        mock_settings.SLIDES_IMAGES_DIR = tmp_path / "images"

        gen = SlideGenerator()
        pkg = SlidesPackage(file_path=None, presentation_id="test_none")

        # pptx import が失敗しても file_path=None なので空ファイル書き込みもスキップ
        import builtins
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "pptx":
                raise ImportError("no pptx")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            await gen._download_slides_file(pkg)

        # エラーなく完了すれば OK


# ---------------------------------------------------------------------------
# generate_slides() — full flow (non-bundle)  (covers L116-134)
# ---------------------------------------------------------------------------

class TestGenerateSlidesFullFlow:
    @pytest.mark.asyncio
    @patch("slides.slide_generator.settings")
    @patch("slides.slide_generator.GoogleSlidesClient")
    async def test_full_flow_without_bundle(self, MockClient, mock_settings):
        mock_settings.SLIDES_SETTINGS = {
            "max_chars_per_slide": 200,
            "max_slides_per_batch": 20,
            "theme": "business",
            "prefer_gemini_slide_content": False,
        }
        mock_settings.SLIDES_DIR = Path("/tmp/test_slides")
        mock_settings.SLIDES_IMAGES_DIR = Path("/tmp/test_slides/images")

        # GoogleSlidesClient はモックフォールバック
        client_instance = MockClient.return_value
        client_instance.create_presentation.return_value = None

        gen = SlideGenerator()
        gen.content_splitter = MagicMock()
        gen.content_splitter.split_for_slides = AsyncMock(return_value=[
            {"title": "Slide 1", "text": "Content 1", "duration": 15.0},
            {"title": "Slide 2", "text": "Content 2", "duration": 15.0},
        ])
        gen._download_slides_file = AsyncMock()
        gen._save_slides_metadata = AsyncMock()

        transcript = _make_transcript()

        result = await gen.generate_slides(transcript, max_slides=10)

        assert result.total_slides == 2
        assert result.presentation_id.startswith("mock_")
        gen.content_splitter.split_for_slides.assert_awaited_once()
        gen._download_slides_file.assert_awaited_once()
        gen._save_slides_metadata.assert_awaited_once()

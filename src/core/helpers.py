"""
ヘルパー関数
"""
from typing import Optional, Dict, Any
from config.settings import settings
from .utils.logger import logger
from .exceptions import PipelineError


def with_fallback(primary_func, fallback_func, *args, **kwargs):
    """
    フォールバック処理付き関数実行

    Args:
        primary_func: メイン関数
        fallback_func: フォールバック関数
        *args, **kwargs: 関数引数
    """
    try:
        return primary_func(*args, **kwargs)
    except (OSError, AttributeError, TypeError, ValueError, RuntimeError) as e:
        logger.warning(f"Primary function failed: {e}. Using fallback...")
        try:
            return fallback_func(*args, **kwargs)
        except (OSError, AttributeError, TypeError, ValueError, RuntimeError) as fallback_e:
            logger.error(f"Fallback also failed: {fallback_e}")
            raise PipelineError(
                f"Both primary and fallback failed: {e} -> {fallback_e}",
                recoverable=False
            )
        except Exception as fallback_e:
            logger.error(f"Fallback also failed: {fallback_e}")
            raise PipelineError(
                f"Both primary and fallback failed: {e} -> {fallback_e}",
                recoverable=False
            )
    except Exception as e:
        logger.warning(f"Primary function failed: {e}. Using fallback...")
        try:
            return fallback_func(*args, **kwargs)
        except (OSError, AttributeError, TypeError, ValueError, RuntimeError) as fallback_e:
            logger.error(f"Fallback also failed: {fallback_e}")
            raise PipelineError(
                f"Both primary and fallback failed: {e} -> {fallback_e}",
                recoverable=False
            )
        except Exception as fallback_e:
            logger.error(f"Fallback also failed: {fallback_e}")
            raise PipelineError(
                f"Both primary and fallback failed: {e} -> {fallback_e}",
                recoverable=False
            )


def build_default_pipeline():
    """設定に基づきモジュールコンポーネントを組み立てるヘルパー"""
    from .pipeline import ModularVideoPipeline
    # インポートはここで必要に応じて追加

    stage_modes = settings.PIPELINE_STAGE_MODES
    components = settings.PIPELINE_COMPONENTS

    script_provider = None
    voice_pipeline = None
    timeline_planner = None
    editing_backend = None
    platform_adapter = None
    thumbnail_generator = None

    if components.get("script_provider") == "gemini" and settings.GEMINI_API_KEY:
        try:
            from .providers.script.gemini_provider import GeminiScriptProvider
            script_provider = GeminiScriptProvider()
        except ValueError as err:
            logger.warning(f"GeminiScriptProviderの初期化に失敗しました: {err}")
    elif components.get("script_provider") == "notebooklm":
        try:
            from .providers.script.notebook_lm_provider import NotebookLMScriptProvider
            script_provider = NotebookLMScriptProvider()
        except ValueError as err:
            logger.warning(f"NotebookLMScriptProviderの初期化に失敗しました: {err}")

    if components.get("voice_pipeline") in {"tts", "gemini_tts"}:
        from .voice_pipelines.tts_voice_pipeline import TTSVoicePipeline
        voice_pipeline = TTSVoicePipeline()

    editing_backend_setting = components.get("editing_backend")

    if editing_backend_setting == "moviepy":
        from .timeline.basic_planner import BasicTimelinePlanner
        from .editing.moviepy_backend import MoviePyEditingBackend
        timeline_planner = BasicTimelinePlanner()
        editing_backend = MoviePyEditingBackend()
    elif editing_backend_setting == "ymm4":
        from .timeline.basic_planner import BasicTimelinePlanner
        from .editing.ymm4_backend import YMM4EditingBackend
        timeline_planner = BasicTimelinePlanner()
        editing_backend = YMM4EditingBackend()

    platform_adapter_setting = components.get("platform_adapter")
    if platform_adapter_setting == "youtube":
        from .platforms.youtube_adapter import YouTubePlatformAdapter
        platform_adapter = YouTubePlatformAdapter()
    elif platform_adapter_setting == "tiktok":
        from .platforms.tiktok_adapter import TikTokPlatformAdapter
        platform_adapter = TikTokPlatformAdapter()

    # サムネイル生成の初期化
    thumbnail_setting = components.get("thumbnail_generator", "ai")
    if thumbnail_setting == "ai":
        from .thumbnails import AIThumbnailGenerator
        thumbnail_generator = AIThumbnailGenerator()
    elif thumbnail_setting == "template":
        from .thumbnails.template_generator import TemplateThumbnailGenerator
        thumbnail_generator = TemplateThumbnailGenerator()

    pipeline = ModularVideoPipeline(
        script_provider=script_provider,
        voice_pipeline=voice_pipeline,
        timeline_planner=timeline_planner,
        editing_backend=editing_backend,
        platform_adapter=platform_adapter,
        thumbnail_generator=thumbnail_generator,
    )

    pipeline.stage_modes.update(stage_modes)

    return pipeline

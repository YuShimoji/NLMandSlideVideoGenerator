"""
ヘルパー関数
"""
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
    from .interfaces import IScriptProvider, IVoicePipeline, IEditingBackend, IPlatformAdapter, IThumbnailGenerator
    from typing import Optional
    # インポートはここで必要に応じて追加

    stage_modes = settings.PIPELINE_STAGE_MODES
    components = settings.PIPELINE_COMPONENTS

    script_provider: Optional[IScriptProvider] = None
    voice_pipeline: Optional[IVoicePipeline] = None
    timeline_planner = None
    editing_backend: Optional[IEditingBackend] = None
    platform_adapter: Optional[IPlatformAdapter] = None
    thumbnail_generator: Optional[IThumbnailGenerator] = None

    import os as _os
    script_provider_type = components.get("script_provider", "")
    has_llm_key = settings.GEMINI_API_KEY or _os.environ.get("LLM_API_KEY", "")
    if script_provider_type == "llm" or (script_provider_type == "gemini" and has_llm_key):
        try:
            from .providers.script.gemini_provider import GeminiScriptProvider
            from .llm_provider import create_llm_provider
            llm_provider = create_llm_provider()
            script_provider = GeminiScriptProvider(llm_provider=llm_provider)
        except ValueError as err:
            logger.warning(f"GeminiScriptProviderの初期化に失敗しました: {err}")
    elif script_provider_type == "notebooklm":
        try:
            from .providers.script.notebook_lm_provider import NotebookLMScriptProvider
            script_provider = NotebookLMScriptProvider()
        except ValueError as err:
            logger.warning(f"NotebookLMScriptProviderの初期化に失敗しました: {err}")

    editing_backend_setting = components.get("editing_backend")

    if editing_backend_setting == "ymm4":
        from .timeline.basic_planner import BasicTimelinePlanner
        from .editing.ymm4_backend import YMM4EditingBackend
        timeline_planner = BasicTimelinePlanner()
        editing_backend = YMM4EditingBackend()

    platform_adapter_setting = components.get("platform_adapter")
    if platform_adapter_setting == "youtube":
        from .platforms.youtube_adapter import YouTubePlatformAdapter
        platform_adapter = YouTubePlatformAdapter()

    # サムネイル: YMM4テンプレートで人間が作成 (DESIGN_FOUNDATIONS準拠)
    # PIL自動生成は廃止済み。thumbnail_generatorはNoneのまま。

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

"""
モジュラー動画生成パイプライン
- 依存性注入(DI)により各役割を差し替え可能
- 既存の実装をデフォルトとして使用
"""
from __future__ import annotations

from typing import List, Optional, Dict, Any, Callable

from config.settings import create_directories

from .interfaces import (
    ISourceCollector,
    IAudioGenerator,
    ITranscriptProcessor,
    ISlideGenerator,
    IUploader,
    IMetadataGenerator,
    IScriptProvider,
    IContentAdapter,
    IVoicePipeline,
    IAssetRegistry,
    ITimelinePlanner,
    IEditingBackend,
    IThumbnailGenerator,
    IPlatformAdapter,
    IPublishingQueue,
)
# 既存実装（デフォルトDI）
from notebook_lm.source_collector import SourceCollector
from notebook_lm.audio_generator import AudioGenerator, AudioInfo
from notebook_lm.transcript_processor import TranscriptProcessor
from slides.slide_generator import SlideGenerator
from youtube.uploader import YouTubeUploader, UploadResult
from youtube.metadata_generator import MetadataGenerator

# 追加統合（オプション）
from .adapters import ContentAdapterManager

from .utils.decorators import retry_on_failure
from .utils.logger import logger
from .exceptions import PipelineError
from .models import PipelineArtifacts
from .helpers import build_default_pipeline  # noqa: F401 (Re-exported for backwards compatibility)
from . import stage_runners as sr


class ModularVideoPipeline:
    """依存性注入可能な動画生成パイプライン"""

    def __init__(
        self,
        source_collector: Optional[ISourceCollector] = None,
        audio_generator: Optional[IAudioGenerator] = None,
        transcript_processor: Optional[ITranscriptProcessor] = None,
        slide_generator: Optional[ISlideGenerator] = None,
        uploader: Optional[IUploader] = None,
        metadata_generator: Optional[IMetadataGenerator] = None,
        script_provider: Optional[IScriptProvider] = None,
        content_adapter: Optional[IContentAdapter] = None,
        voice_pipeline: Optional[IVoicePipeline] = None,
        asset_registry: Optional[IAssetRegistry] = None,
        timeline_planner: Optional[ITimelinePlanner] = None,
        editing_backend: Optional[IEditingBackend] = None,
        thumbnail_generator: Optional[IThumbnailGenerator] = None,
        platform_adapter: Optional[IPlatformAdapter] = None,
        publishing_queue: Optional[IPublishingQueue] = None,
    ) -> None:
        # Stage1 legacy fallbacks
        self.source_collector = source_collector or SourceCollector()
        self.audio_generator = audio_generator or AudioGenerator()
        self.transcript_processor = transcript_processor or TranscriptProcessor()
        self.slide_generator = slide_generator or SlideGenerator()
        self.uploader = uploader or YouTubeUploader()
        self.metadata_generator = metadata_generator or MetadataGenerator()

        # Stage1 modular components (optional)
        self.script_provider = script_provider
        self.content_adapter_manager = ContentAdapterManager()
        self.content_adapter = content_adapter
        self.voice_pipeline = voice_pipeline
        self.asset_registry = asset_registry

        # Stage2 modular components
        self.timeline_planner = timeline_planner
        self.editing_backend = editing_backend
        self.thumbnail_generator = thumbnail_generator

        # Stage3 modular components
        self.platform_adapter = platform_adapter
        self.publishing_queue = publishing_queue

        # Operation modes per stage
        self.stage_modes = {
            "stage1": "auto",
            "stage2": "auto",
            "stage3": "auto",
        }

    async def run(
        self,
        topic: str,
        urls: Optional[List[str]] = None,
        quality: str = "1080p",
        private_upload: bool = True,
        upload: bool = True,
        stage_modes: Optional[Dict[str, str]] = None,
        user_preferences: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[[str, float, str], None]] = None,
        job_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        パイプライン実行
        Returns dict with results and artifacts paths
        """
        # ジョブID生成
        if job_id is None:
            import uuid
            job_id = str(uuid.uuid4())

        logger.info(f"モジュラーパイプライン開始: {topic} (Job ID: {job_id})")
        create_directories()

        if stage_modes:
            self.stage_modes.update(stage_modes)

        try:
            # Phase 1: ソース収集
            if progress_callback:
                progress_callback("ソース収集", 0.1, "関連ソースの収集を開始します...")
            try:
                sources = await self._collect_sources_with_retry(topic, urls)
                logger.info(f"ソース収集完了: {len(sources)}件")
                if progress_callback:
                    progress_callback("ソース収集", 0.1, f"ソース収集完了: {len(sources)}件")
            except (OSError, AttributeError, TypeError, ValueError, RuntimeError) as e:
                logger.error(f"ソース収集失敗 (recoverable): {e}")
                raise PipelineError(str(e), stage="sources", recoverable=True)
            except Exception as e:
                import traceback
                logger.error(f"ソース収集で予期せぬエラー: {e}\n{traceback.format_exc()}")
                raise PipelineError(str(e), stage="sources", recoverable=False)

            stage1_mode = self.stage_modes.get("stage1", "auto")
            stage2_mode = self.stage_modes.get("stage2", "auto")
            stage3_mode = self.stage_modes.get("stage3", "auto")

            audio_info: AudioInfo
            script_bundle: Optional[Dict[str, Any]] = None
            timeline_plan: Optional[Dict[str, Any]] = None
            registered_assets: Optional[Dict[str, Any]] = None
            editing_outputs: Optional[Dict[str, Any]] = None

            # Stage1: Script + Voice orchestration
            if self.script_provider and self.voice_pipeline:
                try:
                    if progress_callback:
                        progress_callback("スクリプト生成", 0.2, "AIによるスクリプト生成を開始します...")
                    logger.info(f"Stage1モード: {stage1_mode}")
                    raw_script = await self._generate_script_with_retry(
                        topic=topic,
                        sources=sources,
                        mode=stage1_mode,
                    )
                    script_bundle = await self._normalize_script_with_fallback(raw_script)
                    if progress_callback:
                        progress_callback("音声合成", 0.3, "テキスト-to-スピーチで音声を生成します...")
                    audio_info = await self._synthesize_audio_with_retry(
                        script=script_bundle or raw_script,
                        provider="none",
                    )
                    if self.asset_registry:
                        registered_assets = await self.asset_registry.register_assets(
                            {
                                "script": script_bundle or raw_script,
                                "audio": audio_info,
                                "sources": sources,
                            }
                        )
                except PipelineError:
                    raise
                except (OSError, AttributeError, TypeError, ValueError, RuntimeError) as e:
                    logger.error(f"Stage1処理失敗: {e}")
                    raise PipelineError(str(e), stage="script", recoverable=True)
                except Exception as e:
                    import traceback
                    logger.error(f"Stage1で予期せぬエラー: {e}\n{traceback.format_exc()}")
                    raise PipelineError(str(e), stage="script", recoverable=False)
            else:
                if progress_callback:
                    progress_callback("従来処理", 0.2, "従来の処理方式を使用します...")
                logger.info("Stage1カスタムプロバイダ未設定のため従来フローを使用")
                script_bundle, audio_info = await sr.run_legacy_stage1_with_fallback(topic, sources, self.audio_generator)

            logger.info(f"音声生成完了: {audio_info.file_path}")
            if progress_callback:
                progress_callback("音声生成", 0.4, f"音声生成完了: {audio_info.file_path}")

            # Phase 2: 文字起こし
            if progress_callback:
                progress_callback("文字起こし", 0.5, "音声から文字起こしを行います...")
            transcript = await self.transcript_processor.process_audio(audio_info)
            logger.info(f"文字起こし完了: {transcript.title}")
            if progress_callback:
                progress_callback("文字起こし", 0.5, f"文字起こし完了: {transcript.title}")

            # Phase 3: スライド生成
            if progress_callback:
                progress_callback("スライド生成", 0.6, "Google Slidesでプレゼンテーションを作成します...")
            slides_pkg = await self.slide_generator.generate_slides(transcript, script_bundle=script_bundle)
            logger.info(f"スライド生成完了: {slides_pkg.total_slides}枚")
            if progress_callback:
                progress_callback("スライド生成", 0.6, f"スライド生成完了: {slides_pkg.total_slides}枚")

            # Stage2: 映像タイムライン計画 & レンダリング
            video_info, thumbnail_path, timeline_plan, editing_outputs = await sr.run_stage2_video_render(
                audio_info=audio_info,
                slides_pkg=slides_pkg,
                transcript=transcript,
                quality=quality,
                script_bundle=script_bundle,
                user_preferences=user_preferences,
                stage2_mode=stage2_mode,
                timeline_planner=self.timeline_planner,
                editing_backend=self.editing_backend,
                thumbnail_generator=self.thumbnail_generator,
                progress_callback=progress_callback,
            )

            # Stage3: 投稿・配信
            upload_result: Optional[UploadResult] = None
            youtube_url: Optional[str] = None
            metadata: Optional[Dict[str, Any]] = None
            publishing_result: Optional[Dict[str, Any]] = None

            if upload:
                upload_result, youtube_url, metadata, publishing_result = (
                    await sr.run_stage3_upload(
                        video_info=video_info,
                        transcript=transcript,
                        thumbnail_path=thumbnail_path,
                        private_upload=private_upload,
                        stage3_mode=stage3_mode,
                        user_preferences=user_preferences,
                        metadata_generator=self.metadata_generator,
                        platform_adapter=self.platform_adapter,
                        publishing_queue=self.publishing_queue,
                        uploader=self.uploader,
                        progress_callback=progress_callback,
                    )
                )
            else:
                if progress_callback:
                    progress_callback("完了", 1.0, "アップロードをスキップしました")

            artifacts = PipelineArtifacts(
                sources=sources,
                audio=audio_info,
                transcript=transcript,
                slides=slides_pkg,
                video=video_info,
                upload=upload_result,
                script=script_bundle,
                timeline_plan=timeline_plan,
                assets=registered_assets,
                thumbnail_path=thumbnail_path,
                metadata=metadata,
                publishing_result=publishing_result,
                editing_outputs=editing_outputs,
            )

            if progress_callback:
                progress_callback("完了", 1.0, "パイプライン実行完了")

            return {
                "success": True,
                "youtube_url": youtube_url,
                "artifacts": artifacts,
                "job_id": job_id,
            }

        except PipelineError as e:
            logger.error(f"Pipeline error (Job {job_id}): {e}")
            raise

        except (OSError, AttributeError, TypeError, ValueError, RuntimeError) as e:
            logger.error(f"Unexpected error (Job {job_id}): {e}")
            raise PipelineError(str(e), recoverable=False)

        except Exception as e:
            logger.error(f"Unexpected error (Job {job_id}): {e}")
            raise PipelineError(str(e), recoverable=False)

    @retry_on_failure()
    async def _collect_sources_with_retry(self, topic: str, urls: Optional[List[str]] = None) -> List:
        """ソース収集（リトライ付き）"""
        return await self.source_collector.collect_sources(topic, urls)

    @retry_on_failure()
    async def _generate_script_with_retry(
        self,
        topic: str,
        sources: List,
        mode: str = "auto"
    ) -> Dict[str, Any]:
        """スクリプト生成（リトライ付き）"""
        if self.script_provider is not None:
            return await self.script_provider.generate_script(topic, sources, mode)
        raise PipelineError("script_provider is not configured", recoverable=False)

    async def _normalize_script_with_fallback(self, raw_script: Dict[str, Any]) -> Dict[str, Any]:
        """スクリプト正規化（フォールバック付き）"""
        if self.content_adapter_manager is not None:
            return await self.content_adapter_manager.normalize_script(raw_script, "notebooklm")
        return raw_script

    @retry_on_failure()
    async def _synthesize_audio_with_retry(
        self,
        script: Dict[str, Any],
        provider: str
    ) -> AudioInfo:
        """音声合成（リトライ付き）"""
        if self.voice_pipeline is not None:
            return await self.voice_pipeline.synthesize(script, provider)
        raise PipelineError("voice_pipeline is not configured", recoverable=False)

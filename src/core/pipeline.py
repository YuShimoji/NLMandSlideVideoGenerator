"""
モジュラー動画生成パイプライン
- 依存性注入(DI)により各役割を差し替え可能
- 既存の実装をデフォルトとして使用
"""
from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime
from typing import Protocol, List, Optional, Union, Dict, Any, Callable
from pathlib import Path

from config.settings import settings, create_directories

from .interfaces import (
    ISourceCollector,
    IAudioGenerator,
    ITranscriptProcessor,
    ISlideGenerator,
    IVideoComposer,
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
from .persistence import db_manager

# 既存実装（デフォルトDI）
from notebook_lm.source_collector import SourceCollector, SourceInfo
from notebook_lm.audio_generator import AudioGenerator, AudioInfo
from notebook_lm.transcript_processor import TranscriptProcessor, TranscriptInfo
from slides.slide_generator import SlideGenerator, SlidesPackage
from video_editor.video_composer import VideoComposer, VideoInfo
from youtube.uploader import YouTubeUploader, UploadResult
from youtube.metadata_generator import MetadataGenerator

# 追加統合（オプション）
from notebook_lm.gemini_integration import GeminiIntegration, ScriptInfo
from audio.tts_integration import TTSIntegration, TTSProvider, VoiceConfig
from .providers.script.gemini_provider import GeminiScriptProvider
from .providers.script.notebook_lm_provider import NotebookLMScriptProvider
from .voice_pipelines.tts_voice_pipeline import TTSVoicePipeline
from .timeline.basic_planner import BasicTimelinePlanner
from .thumbnails import AIThumbnailGenerator
from .thumbnails.template_generator import TemplateThumbnailGenerator
from .editing.moviepy_backend import MoviePyEditingBackend
from .editing.ymm4_backend import YMM4EditingBackend
from .platforms.youtube_adapter import YouTubePlatformAdapter
from .platforms.tiktok_adapter import TikTokPlatformAdapter
from .adapters import ContentAdapterManager

from .utils.decorators import retry_on_failure
from .utils.logger import logger
from .exceptions import PipelineError
from .models import PipelineArtifacts
from .helpers import with_fallback


class ModularVideoPipeline:
    """依存性注入可能な動画生成パイプライン"""

    def __init__(
        self,
        source_collector: Optional[ISourceCollector] = None,
        audio_generator: Optional[IAudioGenerator] = None,
        transcript_processor: Optional[ITranscriptProcessor] = None,
        slide_generator: Optional[ISlideGenerator] = None,
        video_composer: Optional[IVideoComposer] = None,
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
        self.video_composer = video_composer or VideoComposer()
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

        # 生成履歴の初期レコード作成
        db_manager.save_generation_record({
            'job_id': job_id,
            'topic': topic,
            'status': 'running',
            'created_at': datetime.now(),
            'metadata': {
                'quality': quality,
                'private_upload': private_upload,
                'upload': upload,
                'stage_modes': stage_modes or {},
                'user_preferences': user_preferences or {}
            }
        })

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
            except Exception as e:
                raise PipelineError(str(e), stage="sources", recoverable=True)

            stage1_mode = self.stage_modes.get("stage1", "auto")
            stage2_mode = self.stage_modes.get("stage2", "auto")
            stage3_mode = self.stage_modes.get("stage3", "auto")

            audio_info: AudioInfo
            script_bundle: Optional[Dict[str, Any]] = None
            timeline_plan: Optional[Dict[str, Any]] = None
            registered_assets: Optional[Dict[str, Any]] = None

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
                        provider=settings.TTS_SETTINGS.get("provider", "none"),
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
                except Exception as e:
                    raise PipelineError(str(e), stage="script", recoverable=True)
            else:
                if progress_callback:
                    progress_callback("従来処理", 0.2, "従来の処理方式を使用します...")
                logger.info("Stage1カスタムプロバイダ未設定のため従来フローを使用")
                script_bundle, audio_info = await self._run_legacy_stage1_with_fallback(topic, sources)

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
            thumbnail_path: Optional[Path] = None
            if self.timeline_planner and self.editing_backend:
                if progress_callback:
                    progress_callback("タイムライン計画", 0.7, "動画のタイムラインを計画します...")
                logger.info(f"Stage2モード: {stage2_mode}")
                timeline_plan = await self.timeline_planner.build_plan(
                    script=script_bundle or {"segments": transcript.segments},
                    audio=audio_info,
                    user_preferences=user_preferences,
                )
                if progress_callback:
                    progress_callback("動画レンダリング", 0.75, "MoviePyで動画をレンダリングします...")
                video_info = await self.editing_backend.render(
                    timeline_plan=timeline_plan,
                    audio=audio_info,
                    slides=slides_pkg,
                    transcript=transcript,
                    quality=quality,
                )
                if self.thumbnail_generator and (user_preferences and user_preferences.get("generate_thumbnail", False)):
                    try:
                        thumbnail_style = user_preferences.get("thumbnail_style", "modern")
                        thumbnail_info = await self.thumbnail_generator.generate(
                            video=video_info,
                            script=script_bundle or {"title": transcript.title},
                            slides=slides_pkg,
                            style=thumbnail_style
                        )
                        thumbnail_path = thumbnail_info.file_path
                        logger.info(f"サムネイル生成完了: {thumbnail_path}")
                    except Exception as thumb_err:
                        logger.warning(f"サムネイル生成に失敗しました: {thumb_err}")
                        thumbnail_path = None
            else:
                if progress_callback:
                    progress_callback("動画合成", 0.7, "MoviePyで動画を合成します...")
                logger.info("Stage2拡張未設定のため従来の VideoComposer を使用")
                video_info = await self.video_composer.compose_video(audio_info, slides_pkg, transcript, quality)

            logger.info(f"動画合成完了: {video_info.file_path}")
            if progress_callback:
                progress_callback("動画合成", 0.8, f"動画合成完了: {video_info.file_path}")

            # Stage3: 投稿・配信
            upload_result: Optional[UploadResult] = None
            youtube_url: Optional[str] = None
            metadata: Optional[Dict[str, Any]] = None
            publishing_result: Optional[Dict[str, Any]] = None

            if upload:
                if progress_callback:
                    progress_callback("アップロード準備", 0.9, "メタデータを生成します...")
                # メタデータ生成
                metadata = await self.metadata_generator.generate_metadata(transcript)
                metadata["privacy_status"] = "private" if private_upload else "public"
                metadata["language"] = settings.YOUTUBE_SETTINGS.get("default_language", "ja")

                if self.platform_adapter:
                    if progress_callback:
                        progress_callback("YouTubeアップロード", 0.95, "YouTubeに動画をアップロードします...")
                    logger.info(f"Stage3モード: {stage3_mode}")
                    package = {
                        "video": video_info,
                        "metadata": metadata,
                        "thumbnail": thumbnail_path,
                        "schedule": user_preferences.get("schedule") if user_preferences else None,
                    }
                    if self.publishing_queue:
                        queue_id = await self.publishing_queue.enqueue(
                            package,
                            schedule=package.get("schedule"),
                        )
                        logger.info(f"投稿キューに登録しました: {queue_id}")
                    publishing_result = await self.platform_adapter.publish(
                        package,
                        options={"mode": stage3_mode},
                    )
                    youtube_url = publishing_result.get("url") if publishing_result else None
                else:
                    if progress_callback:
                        progress_callback("YouTubeアップロード", 0.95, "YouTube APIでアップロードします...")
                    await self.uploader.authenticate()
                    upload_result = await self.uploader.upload_video(
                        video=video_info,
                        metadata=metadata,
                        thumbnail_path=thumbnail_path,
                    )
                    youtube_url = upload_result.video_url if upload_result else None
                    logger.success(f"アップロード完了: {youtube_url}")
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
            )

            if progress_callback:
                progress_callback("完了", 1.0, "パイプライン実行完了")

            # 成功時の更新
            db_manager.update_generation_status(job_id, 'completed')
            db_manager.save_generation_record({
                'job_id': job_id,
                'topic': topic,
                'status': 'completed',
                'completed_at': datetime.now(),
                'artifacts': {
                    'youtube_url': youtube_url,
                    'video_file': str(artifacts.video.file_path) if artifacts.video else None,
                    'audio_file': str(artifacts.audio.file_path) if artifacts.audio else None,
                    'script_file': None,
                }
            })

            return {
                "success": True,
                "youtube_url": youtube_url,
                "artifacts": artifacts,
                "job_id": job_id,
            }

        except PipelineError as e:
            logger.error(f"Pipeline error (Job {job_id}): {e}")
            db_manager.update_generation_status(job_id, 'failed', str(e))
            raise

        except Exception as e:
            logger.error(f"Unexpected error (Job {job_id}): {e}")
            db_manager.update_generation_status(job_id, 'failed', str(e))
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
        return await self.script_provider.generate_script(topic, sources, mode)

    async def _normalize_script_with_fallback(self, raw_script: Dict[str, Any]) -> Dict[str, Any]:
        """スクリプト正規化（フォールバック付き）"""
        if self.content_adapter_manager:
            return await self.content_adapter_manager.normalize_script(raw_script, "notebooklm")
        return raw_script

    @retry_on_failure()
    async def _synthesize_audio_with_retry(
        self,
        script: Dict[str, Any],
        provider: str
    ) -> AudioInfo:
        """音声合成（リトライ付き）"""
        return await self.voice_pipeline.synthesize(script, provider)

    async def _run_legacy_stage1_with_fallback(
        self,
        topic: str,
        sources: List
    ) -> tuple[Optional[Dict[str, Any]], AudioInfo]:
        """従来 Stage1 処理（フォールバック付き）"""
        try:
            return await self._run_legacy_stage1(topic, sources)
        except Exception as e:
            logger.warning(f"Legacy Stage1 failed: {e}. Using minimal fallback...")
            # 最小限のフォールバック
            audio_info = await self.audio_generator.generate_audio(sources)
            return None, audio_info

    async def _run_legacy_stage1(
        self,
        topic: str,
        sources: List[SourceInfo],
    ) -> tuple[Optional[Dict[str, Any]], AudioInfo]:
        """従来のGemini+TTSまたはNotebookLMモックを使用したStage1処理"""

        script_bundle: Optional[Dict[str, Any]] = None

        if settings.GEMINI_API_KEY and settings.TTS_SETTINGS.get("provider", "none") != "none":
            logger.info("Gemini + TTS による音声生成パスを使用します")
            try:
                gemini = GeminiIntegration(api_key=settings.GEMINI_API_KEY)
                sources_payload = [
                    {
                        "url": getattr(s, "url", ""),
                        "title": getattr(s, "title", ""),
                        "content_preview": getattr(s, "content_preview", ""),
                        "relevance_score": getattr(s, "relevance_score", 0.0),
                        "reliability_score": getattr(s, "reliability_score", 0.0),
                    }
                    for s in sources
                ]
                language = settings.YOUTUBE_SETTINGS.get("default_language", "ja")
                script_info: ScriptInfo = await gemini.generate_script_from_sources(
                    sources=sources_payload,
                    topic=topic,
                    target_duration=300.0,
                    language=language,
                )

                settings.SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                script_path = settings.SCRIPTS_DIR / f"script_{timestamp}.json"
                with open(script_path, "w", encoding="utf-8") as f:
                    f.write(script_info.content)
                logger.info(f"スクリプト保存: {script_path}")

                try:
                    script_bundle = json.loads(script_info.content)
                except json.JSONDecodeError:
                    logger.warning("Gemini スクリプトをJSONとして解析できませんでした。生テキストを保持します。")
                    script_bundle = {"title": script_info.title, "content": script_info.content}

                if script_bundle and "segments" in script_bundle:
                    tts_text = "\n\n".join(seg.get("content", "") for seg in script_bundle.get("segments", []))
                else:
                    tts_text = script_info.content

                api_keys = {
                    "elevenlabs": settings.TTS_SETTINGS.get("elevenlabs", {}).get("api_key", ""),
                    "openai": settings.OPENAI_API_KEY,
                    "azure_speech": settings.TTS_SETTINGS.get("azure", {}).get("key", ""),
                    "azure_region": settings.TTS_SETTINGS.get("azure", {}).get("region", ""),
                    "google_cloud": settings.TTS_SETTINGS.get("google_cloud", {}).get("api_key", ""),
                }
                tts = TTSIntegration(api_keys)
                audio_output = settings.AUDIO_DIR / f"tts_{timestamp}.mp3"
                voice_cfg = VoiceConfig(
                    voice_id=settings.TTS_SETTINGS.get("elevenlabs", {}).get("voice_id", "default"),
                    language=language,
                    gender="female",
                    age_range="adult",
                    accent="japanese" if language == "ja" else "",
                    quality="high",
                )
                tts_audio = await tts.generate_audio(tts_text, audio_output, voice_cfg)
                audio_info = AudioInfo(
                    file_path=tts_audio.file_path,
                    duration=tts_audio.duration,
                    quality_score=tts_audio.quality_score,
                    sample_rate=tts_audio.sample_rate,
                    file_size=tts_audio.file_size,
                    language=language,
                    channels=getattr(tts_audio, "channels", 2),
                )
                return script_bundle, audio_info
            except Exception as exc:
                logger.warning(f"Gemini/TTS パスでエラーが発生したため従来モックにフォールバックします: {exc}")

        # フォールバック: 既存AudioGeneratorのみ
        audio_info = await self.audio_generator.generate_audio(sources)
        return script_bundle, audio_info

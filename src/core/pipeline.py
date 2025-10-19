"""
モジュラー動画生成パイプライン
- 依存性注入(DI)により各役割を差し替え可能
- 既存の実装をデフォルトとして使用
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

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
from .voice_pipelines.tts_voice_pipeline import TTSVoicePipeline
from .timeline.basic_planner import BasicTimelinePlanner
from .editing.moviepy_backend import MoviePyEditingBackend
from .editing.ymm4_backend import YMM4EditingBackend


class SimpleLogger:
    def info(self, msg): print(f"[INFO] {msg}")
    def success(self, msg): print(f"[SUCCESS] {msg}")
    def warning(self, msg): print(f"[WARNING] {msg}")
    def error(self, msg): print(f"[ERROR] {msg}")


logger = SimpleLogger()


@dataclass
class PipelineArtifacts:
    sources: List
    audio: AudioInfo
    transcript: TranscriptInfo
    slides: SlidesPackage
    video: VideoInfo
    upload: Optional[UploadResult]
    script: Optional[Dict[str, Any]] = None
    timeline_plan: Optional[Dict[str, Any]] = None
    assets: Optional[Dict[str, Any]] = None
    thumbnail_path: Optional[Path] = None
    metadata: Optional[Dict[str, Any]] = None
    publishing_result: Optional[Dict[str, Any]] = None


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
    ) -> Dict[str, Any]:
        """
        パイプライン実行
        Returns dict with results and artifacts paths
        """
        logger.info(f"モジュラーパイプライン開始: {topic}")
        create_directories()

        if stage_modes:
            self.stage_modes.update(stage_modes)

        # Phase 1: ソース収集
        sources = await self.source_collector.collect_sources(topic, urls)
        logger.info(f"ソース収集完了: {len(sources)}件")

        stage1_mode = self.stage_modes.get("stage1", "auto")
        stage2_mode = self.stage_modes.get("stage2", "auto")
        stage3_mode = self.stage_modes.get("stage3", "auto")

        audio_info: AudioInfo
        script_bundle: Optional[Dict[str, Any]] = None
        timeline_plan: Optional[Dict[str, Any]] = None
        registered_assets: Optional[Dict[str, Any]] = None

        # Stage1: Script + Voice orchestration
        if self.script_provider and self.voice_pipeline:
            logger.info(f"Stage1モード: {stage1_mode}")
            raw_script = await self.script_provider.generate_script(
                topic=topic,
                sources=sources,
                mode=stage1_mode,
            )
            script_bundle = await self.content_adapter.normalize_script(raw_script) if self.content_adapter else raw_script
            audio_info = await self.voice_pipeline.synthesize(
                script=script_bundle or raw_script,
                preferred_provider=settings.TTS_SETTINGS.get("provider", "none"),
            )
            if self.asset_registry:
                registered_assets = await self.asset_registry.register_assets(
                    {
                        "script": script_bundle or raw_script,
                        "audio": audio_info,
                        "sources": sources,
                    }
                )
        else:
            logger.info("Stage1カスタムプロバイダ未設定のため従来フローを使用")
            script_bundle, audio_info = await self._run_legacy_stage1(topic, sources)

        logger.info(f"音声生成完了: {audio_info.file_path}")

        # Phase 2: 文字起こし
        transcript = await self.transcript_processor.process_audio(audio_info)
        logger.info(f"文字起こし完了: {transcript.title}")

        # Phase 3: スライド生成
        slides_pkg = await self.slide_generator.generate_slides(transcript)
        logger.info(f"スライド生成完了: {slides_pkg.total_slides}枚")

        # Stage2: 映像タイムライン計画 & レンダリング
        thumbnail_path: Optional[Path] = None
        if self.timeline_planner and self.editing_backend:
            logger.info(f"Stage2モード: {stage2_mode}")
            timeline_plan = await self.timeline_planner.build_plan(
                script=script_bundle or {"segments": transcript.segments},
                audio=audio_info,
                user_preferences=user_preferences,
            )
            video_info = await self.editing_backend.render(
                timeline_plan=timeline_plan,
                audio=audio_info,
                slides=slides_pkg,
                transcript=transcript,
                quality=quality,
            )
            if self.thumbnail_generator:
                try:
                    thumbnail_path = await self.thumbnail_generator.generate_thumbnail(
                        timeline_plan=timeline_plan,
                        script=script_bundle or {"title": transcript.title},
                        assets=registered_assets or {},
                    )
                except Exception as thumb_err:
                    logger.warning(f"サムネイル生成に失敗しました: {thumb_err}")
                    thumbnail_path = None
        else:
            logger.info("Stage2拡張未設定のため従来の VideoComposer を使用")
            video_info = await self.video_composer.compose_video(audio_info, slides_pkg, transcript, quality)

        logger.info(f"動画合成完了: {video_info.file_path}")

        # Stage3: 投稿・配信
        upload_result: Optional[UploadResult] = None
        youtube_url: Optional[str] = None
        metadata: Optional[Dict[str, Any]] = None
        publishing_result: Optional[Dict[str, Any]] = None

        if upload:
            # メタデータ生成
            metadata = await self.metadata_generator.generate_metadata(transcript)
            metadata["privacy_status"] = "private" if private_upload else "public"
            metadata["language"] = settings.YOUTUBE_SETTINGS.get("default_language", "ja")

            if self.platform_adapter:
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
                await self.uploader.authenticate()
                upload_result = await self.uploader.upload_video(
                    video=video_info,
                    metadata=metadata,
                    thumbnail_path=thumbnail_path,
                )
                youtube_url = upload_result.video_url if upload_result else None
                logger.success(f"アップロード完了: {youtube_url}")
        else:
            logger.info("アップロードをスキップしました")

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

        return {
            "success": True,
            "youtube_url": youtube_url,
            "artifacts": artifacts,
        }

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


def build_default_pipeline() -> ModularVideoPipeline:
    """設定に基づきモジュールコンポーネントを組み立てるヘルパー"""

    stage_modes = settings.PIPELINE_STAGE_MODES
    components = settings.PIPELINE_COMPONENTS

    script_provider = None
    voice_pipeline = None
    timeline_planner = None
    editing_backend = None

    if components.get("script_provider") == "gemini" and settings.GEMINI_API_KEY:
        try:
            script_provider = GeminiScriptProvider()
        except ValueError as err:
            logger.warning(f"GeminiScriptProviderの初期化に失敗しました: {err}")

    if components.get("voice_pipeline") in {"tts", "gemini_tts"}:
        voice_pipeline = TTSVoicePipeline()

    editing_backend_setting = components.get("editing_backend")

    if editing_backend_setting == "moviepy":
        timeline_planner = BasicTimelinePlanner()
        editing_backend = MoviePyEditingBackend()
    elif editing_backend_setting == "ymm4":
        timeline_planner = BasicTimelinePlanner()
        editing_backend = YMM4EditingBackend()

    pipeline = ModularVideoPipeline(
        script_provider=script_provider,
        voice_pipeline=voice_pipeline,
        timeline_planner=timeline_planner,
        editing_backend=editing_backend,
    )

    pipeline.stage_modes.update(stage_modes)

    return pipeline

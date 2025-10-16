"""
モジュラー動画生成パイプライン
- 依存性注入(DI)により各役割を差し替え可能
- 既存の実装をデフォルトとして使用
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
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
    ) -> None:
        self.source_collector = source_collector or SourceCollector()
        self.audio_generator = audio_generator or AudioGenerator()
        self.transcript_processor = transcript_processor or TranscriptProcessor()
        self.slide_generator = slide_generator or SlideGenerator()
        self.video_composer = video_composer or VideoComposer()
        self.uploader = uploader or YouTubeUploader()
        self.metadata_generator = metadata_generator or MetadataGenerator()

    async def run(
        self,
        topic: str,
        urls: Optional[List[str]] = None,
        quality: str = "1080p",
        private_upload: bool = True,
        upload: bool = True,
    ) -> Dict[str, Any]:
        """
        パイプライン実行
        Returns dict with results and artifacts paths
        """
        logger.info(f"モジュラーパイプライン開始: {topic}")
        create_directories()

        # Phase 1: ソース収集
        sources = await self.source_collector.collect_sources(topic, urls)
        logger.info(f"ソース収集完了: {len(sources)}件")

        # Phase 2: 音声生成（Gemini+TTS が設定されていれば優先）
        audio_info: AudioInfo
        script_path = None
        if settings.GEMINI_API_KEY and settings.TTS_SETTINGS.get("provider", "none") != "none":
            logger.info("Gemini + TTS による音声生成パスを使用します")
            # Gemini でスクリプト生成
            try:
                gemini = GeminiIntegration(api_key=settings.GEMINI_API_KEY)
                # SourceInfo -> dict
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
                # スクリプトを保存
                import json as _json
                from datetime import datetime as _dt
                settings.SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
                ts = _dt.now().strftime("%Y%m%d_%H%M%S")
                script_path = settings.SCRIPTS_DIR / f"script_{ts}.json"
                with open(script_path, "w", encoding="utf-8") as f:
                    f.write(script_info.content)
                logger.info(f"スクリプト保存: {script_path}")
                # TTS 用にテキスト整形（セグメントの content を結合）
                try:
                    content_obj = _json.loads(script_info.content)
                    if isinstance(content_obj, dict) and "segments" in content_obj:
                        tts_text = "\n\n".join(seg.get("content", "") for seg in content_obj.get("segments", []))
                    else:
                        tts_text = script_info.content
                except Exception:
                    tts_text = script_info.content
                # TTS 統合
                api_keys = {
                    "elevenlabs": settings.TTS_SETTINGS.get("elevenlabs", {}).get("api_key", ""),
                    "openai": settings.OPENAI_API_KEY,
                    "azure_speech": settings.TTS_SETTINGS.get("azure", {}).get("key", ""),
                    "azure_region": settings.TTS_SETTINGS.get("azure", {}).get("region", ""),
                }
                tts = TTSIntegration(api_keys)
                # 音声ファイルパス
                audio_output = settings.AUDIO_DIR / f"tts_{ts}.mp3"
                # Voice 設定（簡易）
                voice_id = settings.TTS_SETTINGS.get("elevenlabs", {}).get("voice_id", "default")
                voice_cfg = VoiceConfig(
                    voice_id=voice_id,
                    language=language,
                    gender="female",
                    age_range="adult",
                    accent="japanese" if language == "ja" else "",
                    quality="high",
                )
                tts_audio = await tts.generate_audio(tts_text, audio_output, voice_cfg)
                # 既存 AudioInfo 型に正規化
                audio_info = AudioInfo(
                    file_path=tts_audio.file_path,
                    duration=tts_audio.duration,
                    quality_score=tts_audio.quality_score,
                    sample_rate=tts_audio.sample_rate,
                    file_size=tts_audio.file_size,
                    language=language,
                    channels=getattr(tts_audio, "channels", 2),
                )
                logger.info(f"音声生成完了(TTS): {audio_info.file_path}")
            except Exception as e:
                logger.warning(f"Gemini/TTS パスでエラーが発生したためフォールバックします: {e}")
                audio_info = await self.audio_generator.generate_audio(sources)
        else:
            audio_info = await self.audio_generator.generate_audio(sources)
        logger.info(f"音声生成完了: {audio_info.file_path}")

        # Phase 3: 文字起こし
        transcript = await self.transcript_processor.process_audio(audio_info)
        logger.info(f"文字起こし完了: {transcript.title}")

        # Phase 4: スライド生成
        slides_pkg = await self.slide_generator.generate_slides(transcript)
        logger.info(f"スライド生成完了: {slides_pkg.total_slides}枚")

        # Phase 5: 動画合成
        video_info = await self.video_composer.compose_video(audio_info, slides_pkg, transcript, quality)
        logger.info(f"動画合成完了: {video_info.file_path}")

        upload_result: Optional[UploadResult] = None
        youtube_url: Optional[str] = None

        if upload:
            # メタデータ生成
            metadata = await self.metadata_generator.generate_metadata(transcript)
            metadata["privacy_status"] = "private" if private_upload else "public"
            metadata["language"] = settings.YOUTUBE_SETTINGS.get("default_language", "ja")

            await self.uploader.authenticate()
            upload_result = await self.uploader.upload_video(
                video=video_info,
                metadata=metadata,
                thumbnail_path=None,
            )
            youtube_url = upload_result.video_url
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
        )

        return {
            "success": True,
            "youtube_url": youtube_url,
            "artifacts": artifacts,
        }

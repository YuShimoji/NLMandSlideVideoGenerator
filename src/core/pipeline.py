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
from notebook_lm.transcript_processor import TranscriptProcessor, TranscriptInfo, TranscriptSegment
from notebook_lm.csv_transcript_loader import CsvTranscriptLoader
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
from .helpers import with_fallback, build_default_pipeline


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
                editing_extras: Dict[str, Any] = {"export_outputs": {}}
                video_info = await self.editing_backend.render(
                    timeline_plan=timeline_plan,
                    audio=audio_info,
                    slides=slides_pkg,
                    transcript=transcript,
                    quality=quality,
                    extras=editing_extras,
                )
                editing_outputs = editing_extras.get("export_outputs") or None
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
                editing_outputs=editing_outputs,
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

    def _expand_segment_into_slides(
        self,
        segment: TranscriptSegment,
        start_slide_id: int,
    ) -> List[Dict[str, Any]]:
        """CSV 1行を1枚または複数サブスライドに展開"""

        text = (segment.text or "").strip()
        text_length = len(text)
        segment_duration = max(float(segment.end_time - segment.start_time), 0.1)

        slides_settings = settings.SLIDES_SETTINGS
        auto_split = slides_settings.get("auto_split_long_lines", False)
        threshold = int(slides_settings.get("long_line_char_threshold", 9999))
        target_chars = int(slides_settings.get("long_line_target_chars_per_subslide", threshold))
        max_subslides = max(int(slides_settings.get("long_line_max_subslides", 1)), 1)
        min_duration = float(slides_settings.get("min_subslide_duration", 0.5))

        should_split = (
            auto_split
            and max_subslides > 1
            and target_chars > 0
            and text_length >= threshold
        )

        if should_split:
            chunks = self._split_text_for_subslides(text, target_chars, max_subslides)
        else:
            chunks = [text]

        durations = self._allocate_subslide_durations(
            total_duration=segment_duration,
            chunks=chunks,
            min_duration=min_duration,
        )

        total_subslides = len(chunks)
        slides: List[Dict[str, Any]] = []
        for idx, chunk in enumerate(chunks):
            slides.append(
                self._build_slide_dict(
                    segment=segment,
                    slide_id=start_slide_id + idx,
                    text=chunk,
                    duration=durations[idx],
                    sub_index=idx,
                    sub_total=total_subslides,
                )
            )
        return slides

    def _split_text_for_subslides(
        self,
        text: str,
        target_chars: int,
        max_subslides: int,
    ) -> List[str]:
        """句読点優先で長文を複数スライド用テキストに分割"""

        normalized = (text or "").strip()
        if not normalized:
            return [""]

        chunks: List[str] = []
        remaining = normalized

        while remaining and len(chunks) < max_subslides - 1:
            if len(remaining) <= target_chars:
                break

            split_index = self._find_split_index(remaining, target_chars)
            chunk = remaining[:split_index].strip()
            if not chunk:
                chunk = remaining[:target_chars]
                split_index = len(chunk)

            chunks.append(chunk)
            remaining = remaining[split_index:].lstrip()

        if remaining:
            chunks.append(remaining)

        return chunks[:max_subslides]

    def _find_split_index(self, text: str, preferred_length: int) -> int:
        if len(text) <= preferred_length:
            return len(text)

        search_window = min(len(text), preferred_length + 40)
        slice_text = text[:search_window]

        punctuation_patterns = ["。", "！", "？", "!", "?", "、", ",", " ", "\n"]
        for pattern in punctuation_patterns:
            idx = slice_text.rfind(pattern, 0, search_window)
            if idx != -1 and idx >= int(preferred_length * 0.6):
                return idx + 1

        return preferred_length

    def _allocate_subslide_durations(
        self,
        total_duration: float,
        chunks: List[str],
        min_duration: float,
    ) -> List[float]:
        if total_duration <= 0:
            total_duration = 0.1 * len(chunks)

        total_chars = sum(max(len(chunk.strip()), 1) for chunk in chunks)
        total_chars = max(total_chars, 1)

        remaining_duration = total_duration
        remaining_chars = total_chars
        durations: List[float] = []

        for idx, chunk in enumerate(chunks):
            chunk_chars = max(len(chunk.strip()), 1)
            slots_left = len(chunks) - idx - 1

            ratio = chunk_chars / remaining_chars if remaining_chars else 0
            duration = total_duration * ratio if ratio > 0 else remaining_duration / max(slots_left + 1, 1)
            duration = max(duration, min_duration)

            max_allowed = remaining_duration - (slots_left * min_duration)
            if max_allowed > 0:
                duration = min(duration, max_allowed)

            durations.append(duration)
            remaining_duration -= duration
            remaining_chars -= chunk_chars

        total_assigned = sum(durations)
        diff = total_duration - total_assigned
        if durations:
            durations[-1] += diff
            if durations[-1] < min_duration:
                deficit = min_duration - durations[-1]
                durations[-1] = min_duration
                for i in range(len(durations) - 2, -1, -1):
                    available = durations[i] - min_duration
                    if available <= 0:
                        continue
                    take = min(available, deficit)
                    durations[i] -= take
                    deficit -= take
                    if deficit <= 0:
                        break

        return durations

    def _build_slide_dict(
        self,
        segment: TranscriptSegment,
        slide_id: int,
        text: str,
        duration: float,
        sub_index: int,
        sub_total: int,
    ) -> Dict[str, Any]:
        base_title = getattr(segment, "slide_suggestion", None) or (segment.text[:30] if segment.text else f"Segment {segment.id}")
        if sub_total > 1 and sub_index > 0:
            title = f"{base_title}（続き {sub_index + 1}/{sub_total}）"
        else:
            title = base_title

        return {
            "slide_id": slide_id,
            "title": title,
            "text": text,
            "key_points": getattr(segment, "key_points", []),
            "duration": max(duration, 0.1),
            "source_segments": [segment.id],
            "speakers": [segment.speaker] if getattr(segment, "speaker", None) else [],
            "subslide_index": sub_index,
            "subslide_count": sub_total,
            "is_continued": sub_total > 1 and sub_index > 0,
        }

    def _build_slides_payload(
        self,
        segment_payloads: List[Dict[str, Any]],
        csv_path: Path,
    ) -> Dict[str, Any]:
        video_resolution = settings.VIDEO_SETTINGS.get("resolution", (1920, 1080))
        auto_split = settings.SLIDES_SETTINGS.get("auto_split_long_lines", False)

        payload_segments: List[Dict[str, Any]] = []
        for payload in segment_payloads:
            segment = payload.get("segment")
            slides = payload.get("slides", [])
            audio_file: Optional[Path] = payload.get("audio_file")

            if not segment:
                continue

            converted_slides: List[Dict[str, Any]] = []
            for idx, slide in enumerate(slides):
                converted_slides.append(
                    {
                        "slide_id": slide.get("slide_id"),
                        "order": slide.get("subslide_index", idx),
                        "count": slide.get("subslide_count", len(slides)),
                        "title": slide.get("title"),
                        "text": slide.get("text"),
                        "duration": float(slide.get("duration", 0.0) or 0.0),
                        "is_continued": bool(slide.get("is_continued", False)),
                    }
                )

            payload_segments.append(
                {
                    "segment_id": getattr(segment, "id", None),
                    "speaker": getattr(segment, "speaker", ""),
                    "start_time": float(getattr(segment, "start_time", 0.0) or 0.0),
                    "end_time": float(getattr(segment, "end_time", 0.0) or 0.0),
                    "text": getattr(segment, "text", ""),
                    "audio_file": str(audio_file) if audio_file else None,
                    "subslides": converted_slides,
                }
            )

        return {
            "meta": {
                "source_csv": str(csv_path),
                "generated_at": datetime.now().isoformat(),
                "auto_split": auto_split,
                "video_resolution": list(video_resolution),
                "total_segments": len(payload_segments),
            },
            "segments": payload_segments,
        }

    async def run_csv_timeline(
        self,
        csv_path: Path,
        audio_dir: Path,
        topic: Optional[str] = None,
        quality: str = "1080p",
        private_upload: bool = True,
        upload: bool = False,
        stage_modes: Optional[Dict[str, str]] = None,
        user_preferences: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[[str, float, str], None]] = None,
        job_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """CSVタイムライン(P10)から動画生成を行う専用パス

        - SourceCollector / AudioGenerator / TranscriptProcessor をスキップし、
          ユーザー提供の CSV + 行ごと音声から TranscriptInfo / AudioInfo を構築する。
        - 以降のスライド生成・動画合成・アップロード処理は既存の run() と同じフローを利用する。
        """

        import wave

        def _find_audio_files(directory: Path) -> list[Path]:
            # 複数の音声ファイル形式に対応
            patterns = ["*.wav", "*.mp3", "*.m4a", "*.aac", "*.flac", "*.ogg"]
            files: list[Path] = []
            for pat in patterns:
                files.extend(sorted(directory.glob(pat)))
            # 重複を除去してソート
            unique_files = sorted(set(files))
            logger.info(f"音声ファイル検索結果: {len(unique_files)}個見つかりました (dir={directory})")
            for f in unique_files[:10]:  # 最初の10個を表示
                logger.info(f"  - {f.name}")
            if len(unique_files) > 10:
                logger.info(f"  ... 他 {len(unique_files) - 10} 個")
            return unique_files

        def _build_audio_segments(audio_files: list[Path]) -> list[AudioInfo]:
            segments: list[AudioInfo] = []
            for path in audio_files:
                try:
                    # WAVファイルの場合
                    if path.suffix.lower() == ".wav":
                        with wave.open(str(path), "rb") as wf:
                            frames = wf.getnframes()
                            framerate = wf.getframerate() or 1
                            duration = frames / float(framerate)
                    else:
                        # 他の音声ファイル形式の場合、簡易的にファイルサイズベースで推定
                        # TODO: ffmpegやmutagen等のライブラリで正確なdurationを取得
                        file_size = path.stat().st_size
                        # 簡易推定: 一般的な音声ファイルのビットレートを仮定 (128kbps = 16000 bytes/sec)
                        estimated_duration = file_size / 16000.0
                        duration = max(estimated_duration, 1.0)  # 最低1秒
                        logger.info(f"{path.name}: WAV以外のためdurationを推定 ({duration:.1f}秒)")

                    segments.append(AudioInfo(file_path=path, duration=duration))
                except Exception as e:
                    logger.warning(f"音声ファイルの解析に失敗しました: {path} ({e})")
                    # エラーが発生しても処理を継続し、デフォルトのdurationを使用
                    segments.append(AudioInfo(file_path=path, duration=1.0))
            return segments

        def _combine_wav_files(input_files: list[Path], output_path: Path) -> float:
            if not input_files:
                raise ValueError("入力 WAV がありません")

            output_path.parent.mkdir(parents=True, exist_ok=True)

            total_frames = 0
            params = None

            for path in input_files:
                with wave.open(str(path), "rb") as wf:
                    if params is None:
                        params = wf.getparams()
                    else:
                        if wf.getparams()[:3] != params[:3]:
                            raise RuntimeError(f"WAV フォーマットが一致しません: {path}")
                    total_frames += wf.getnframes()

            assert params is not None

            with wave.open(str(output_path), "wb") as out_wf:
                out_wf.setparams(params)
                for path in input_files:
                    with wave.open(str(path), "rb") as in_wf:
                        frames = in_wf.readframes(in_wf.getnframes())
                        out_wf.writeframes(frames)

            framerate = params.framerate or 1
            duration = total_frames / float(framerate)
            return duration

        csv_path = csv_path.expanduser().resolve()
        audio_dir = audio_dir.expanduser().resolve()

        if job_id is None:
            import uuid
            job_id = str(uuid.uuid4())

        if not csv_path.exists():
            raise FileNotFoundError(f"CSVファイルが見つかりません: {csv_path}")
        if not audio_dir.exists():
            raise FileNotFoundError(f"音声ディレクトリが見つかりません: {audio_dir}")

        topic = topic or csv_path.stem

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
                'user_preferences': user_preferences or {},
                'mode': 'csv_timeline',
                'csv_path': str(csv_path),
                'audio_dir': str(audio_dir),
            }
        })

        logger.info(f"CSVタイムラインパイプライン開始: {csv_path} (Job ID: {job_id})")
        create_directories()

        if stage_modes:
            self.stage_modes.update(stage_modes)

        stage2_mode = self.stage_modes.get("stage2", "auto")
        stage3_mode = self.stage_modes.get("stage3", "auto")

        try:
            if progress_callback:
                progress_callback("CSV読み込み", 0.1, "CSVと行ごとの音声からタイムラインを構築します...")

            audio_files = _find_audio_files(audio_dir)
            if not audio_files:
                # ディレクトリの内容を確認してデバッグ情報を提供
                all_files = list(audio_dir.glob("*"))
                logger.error(f"音声ファイルが見つかりません (dir={audio_dir})")
                logger.error(f"ディレクトリ内の全ファイル ({len(all_files)}個):")
                for f in sorted(all_files)[:20]:  # 最初の20個を表示
                    logger.error(f"  - {f.name} ({f.stat().st_size} bytes)")
                if len(all_files) > 20:
                    logger.error(f"  ... 他 {len(all_files) - 20} 個")
                logger.error("対応している拡張子: .wav, .mp3, .m4a, .aac, .flac, .ogg")
                logger.error("TTSバッチスクリプトを使用した場合は、正しい --audio-dir を指定してください")
                raise RuntimeError(f"音声ファイルが見つかりません (dir={audio_dir})")

            audio_segments = _build_audio_segments(audio_files)

            loader = CsvTranscriptLoader()
            transcript = await loader.load_from_csv(csv_path, audio_segments=audio_segments)

            combined_audio_path = settings.AUDIO_DIR / f"{csv_path.stem}_combined.wav"
            total_duration = _combine_wav_files(audio_files, combined_audio_path)
            audio_info = AudioInfo(
                file_path=combined_audio_path,
                duration=total_duration,
                quality_score=1.0,
                sample_rate=44100,
                file_size=combined_audio_path.stat().st_size if combined_audio_path.exists() else 0,
                language=settings.YOUTUBE_SETTINGS.get("default_audio_language", "ja"),
                channels=2,
            )

            logger.info(f"CSVタイムラインから TranscriptInfo / AudioInfo を構築しました: {transcript.title}")

            if progress_callback:
                progress_callback("スライド生成", 0.4, "CSVタイムラインからスライドを生成します...")

            # CSVタイムラインモードでは「1行=1スライド」を基本とし、
            # 各スライドの表示時間を対応するセグメント duration に合わせる
            slide_contents: list[dict[str, Any]] = []
            segment_payloads: List[Dict[str, Any]] = []
            next_slide_id = 1
            for idx, seg in enumerate(transcript.segments):
                segment_slides = self._expand_segment_into_slides(seg, next_slide_id)
                slide_contents.extend(segment_slides)
                next_slide_id += len(segment_slides)

                audio_file = audio_files[idx] if idx < len(audio_files) else None
                segment_payloads.append(
                    {
                        "segment": seg,
                        "slides": segment_slides,
                        "audio_file": audio_file,
                    }
                )

            slides_payload = self._build_slides_payload(
                segment_payloads=segment_payloads,
                csv_path=csv_path,
            )

            editing_extras: Dict[str, Any] = {
                "slides_payload": slides_payload,
                "csv_path": str(csv_path),
                "audio_files": [str(path) for path in audio_files],
                "combined_audio_path": str(combined_audio_path),
                "export_outputs": {},
            }

            slides_pkg = await self.slide_generator.create_slides_from_content(
                slides_content=slide_contents,
                presentation_title=transcript.title,
            )
            logger.info(
                "スライド生成完了 (CSVタイムライン): %s枚"
                % getattr(slides_pkg, "total_slides", len(slide_contents))
            )

            thumbnail_path: Optional[Path] = None
            timeline_plan: Optional[Dict[str, Any]] = None
            registered_assets: Optional[Dict[str, Any]] = None
            editing_outputs: Optional[Dict[str, Any]] = None

            if self.timeline_planner and self.editing_backend:
                if progress_callback:
                    progress_callback("タイムライン計画", 0.6, "動画のタイムラインを計画します...")
                logger.info(f"Stage2モード: {stage2_mode}")
                timeline_plan = await self.timeline_planner.build_plan(
                    script={"segments": transcript.segments},
                    audio=audio_info,
                    user_preferences=user_preferences,
                )
                if progress_callback:
                    progress_callback("動画レンダリング", 0.7, "MoviePyで動画をレンダリングします...")
                video_info = await self.editing_backend.render(
                    timeline_plan=timeline_plan,
                    audio=audio_info,
                    slides=slides_pkg,
                    transcript=transcript,
                    quality=quality,
                    extras=editing_extras,
                )
                editing_outputs = editing_extras.get("export_outputs") or None
            else:
                if progress_callback:
                    progress_callback("動画合成", 0.7, "MoviePyで動画を合成します...")
                logger.info("Stage2拡張未設定のため従来の VideoComposer を使用 (CSVタイムライン)")
                video_info = await self.video_composer.compose_video(audio_info, slides_pkg, transcript, quality)

            logger.info(f"動画合成完了: {video_info.file_path}")
            if progress_callback:
                progress_callback("動画合成", 0.8, f"動画合成完了: {video_info.file_path}")

            upload_result: Optional[UploadResult] = None
            youtube_url: Optional[str] = None
            metadata: Optional[Dict[str, Any]] = None
            publishing_result: Optional[Dict[str, Any]] = None

            if upload:
                if progress_callback:
                    progress_callback("アップロード準備", 0.9, "メタデータを生成します...")
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
                sources=[],
                audio=audio_info,
                transcript=transcript,
                slides=slides_pkg,
                video=video_info,
                upload=upload_result,
                script=None,
                timeline_plan=timeline_plan,
                assets=registered_assets,
                thumbnail_path=thumbnail_path,
                metadata=metadata,
                publishing_result=publishing_result,
                slides_payload=slides_payload,
                editing_outputs=editing_outputs,
            )

            if progress_callback:
                progress_callback("完了", 1.0, "CSVタイムラインパイプライン実行完了")

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
            logger.error(f"Pipeline error (CSV Job {job_id}): {e}")
            db_manager.update_generation_status(job_id, 'failed', str(e))
            raise

        except Exception as e:
            logger.error(f"Unexpected error (CSV Job {job_id}): {e}")
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

                # Geminiスライド情報の生成（任意）
                prefer_gemini = settings.SLIDES_SETTINGS.get("prefer_gemini_slide_content", False)
                logger.info(f"Geminiスライド生成設定: prefer_gemini_slide_content={prefer_gemini}")
                try:
                    max_slides = settings.SLIDES_SETTINGS.get("max_slides_per_batch", 20)
                    logger.info(f"Geminiスライド生成開始: max_slides={max_slides}")
                    gemini_slides = await gemini.generate_slide_content(
                        script_info=script_info,
                        max_slides=max_slides,
                    )

                    if gemini_slides:
                        logger.info(f"Geminiスライド生成成功: {len(gemini_slides)}枚")
                        slide_payload = []
                        for slide in gemini_slides:
                            slide_payload.append(
                                {
                                    "title": slide.get("title", f"スライド {slide.get('slide_number', len(slide_payload) + 1)}"),
                                    "content": slide.get("content", ""),
                                    "layout": slide.get("layout", "title_and_content"),
                                    "duration": slide.get("duration", 15.0),
                                    "image_suggestions": slide.get("image_suggestions", []),
                                }
                            )
                        script_bundle.setdefault("slides", slide_payload)
                        logger.info(f"script_bundle にスライド情報を追加: {len(slide_payload)}枚")
                    else:
                        logger.warning("Geminiスライド生成結果が空でした")
                except Exception as slide_err:
                    logger.warning(f"Geminiスライド生成でエラーが発生しました（フォールバック継続）: {slide_err}")

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

    # =========================================================================
    # Stage2/Stage3 共通ヘルパーメソッド（run() と run_csv_timeline() の重複コード削減）
    # =========================================================================

    async def _run_stage2_video_render(
        self,
        audio_info: AudioInfo,
        slides_pkg: SlidesPackage,
        transcript: TranscriptInfo,
        quality: str,
        script_bundle: Optional[Dict[str, Any]],
        user_preferences: Optional[Dict[str, Any]],
        stage2_mode: str,
        editing_extras: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[[str, float, str], None]] = None,
    ) -> tuple[VideoInfo, Optional[Path], Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Stage2: 動画レンダリング処理の共通ロジック

        Returns:
            tuple: (video_info, thumbnail_path, timeline_plan, editing_outputs)
        """
        thumbnail_path: Optional[Path] = None
        timeline_plan: Optional[Dict[str, Any]] = None
        editing_outputs: Optional[Dict[str, Any]] = None

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

            if editing_extras is None:
                editing_extras = {"export_outputs": {}}

            video_info = await self.editing_backend.render(
                timeline_plan=timeline_plan,
                audio=audio_info,
                slides=slides_pkg,
                transcript=transcript,
                quality=quality,
                extras=editing_extras,
            )
            editing_outputs = editing_extras.get("export_outputs") or None

            # サムネイル生成（オプション）
            if self.thumbnail_generator and user_preferences and user_preferences.get("generate_thumbnail", False):
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

        return video_info, thumbnail_path, timeline_plan, editing_outputs

    async def _run_stage3_upload(
        self,
        video_info: VideoInfo,
        transcript: TranscriptInfo,
        thumbnail_path: Optional[Path],
        private_upload: bool,
        stage3_mode: str,
        user_preferences: Optional[Dict[str, Any]],
        progress_callback: Optional[Callable[[str, float, str], None]] = None,
    ) -> tuple[Optional[UploadResult], Optional[str], Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Stage3: アップロード処理の共通ロジック

        Returns:
            tuple: (upload_result, youtube_url, metadata, publishing_result)
        """
        if progress_callback:
            progress_callback("アップロード準備", 0.9, "メタデータを生成します...")

        metadata = await self.metadata_generator.generate_metadata(transcript)
        metadata["privacy_status"] = "private" if private_upload else "public"
        metadata["language"] = settings.YOUTUBE_SETTINGS.get("default_language", "ja")

        upload_result: Optional[UploadResult] = None
        youtube_url: Optional[str] = None
        publishing_result: Optional[Dict[str, Any]] = None

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

        return upload_result, youtube_url, metadata, publishing_result

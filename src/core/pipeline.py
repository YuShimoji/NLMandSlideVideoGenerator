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
from . import slide_builder as sb
from . import stage_runners as sr
from .csv_audio_utils import find_audio_files, build_audio_segments, combine_wav_files


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
                    except (OSError, AttributeError, TypeError, ValueError, RuntimeError) as thumb_err:
                        logger.warning(f"サムネイル生成に失敗しました（本編は続行）: {thumb_err}")
                        thumbnail_path = None
                    except Exception as thumb_err:
                        import traceback
                        logger.warning(f"サムネイル生成で予期せぬエラー（本編は続行）: {thumb_err}\n{traceback.format_exc()}")
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
            try:
                db_manager.update_generation_status(job_id, 'completed')
            except (OSError, AttributeError, TypeError, ValueError, RuntimeError) as e:
                logger.debug(f"DB更新失敗: {e}")
            except Exception as e:
                import traceback
                logger.debug(f"DB更新失敗 (Unexpected): {e}\n{traceback.format_exc()}")

            try:
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
            except (OSError, AttributeError, TypeError, ValueError, RuntimeError) as e:
                logger.debug(f"DB生成記録失敗: {e}")
            except Exception as e:
                import traceback
                logger.debug(f"DB生成記録失敗 (Unexpected): {e}\n{traceback.format_exc()}")

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

        except (OSError, AttributeError, TypeError, ValueError, RuntimeError) as e:
            logger.error(f"Unexpected error (Job {job_id}): {e}")
            db_manager.update_generation_status(job_id, 'failed', str(e))
            raise PipelineError(str(e), recoverable=False)

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
        return sb.expand_segment_into_slides(segment, start_slide_id)

    def _split_text_for_subslides(
        self,
        text: str,
        target_chars: int,
        max_subslides: int,
    ) -> List[str]:
        """句読点優先で長文を複数スライド用テキストに分割"""
        return sb.split_text_for_subslides(text, target_chars, max_subslides)

    def _find_split_index(self, text: str, preferred_length: int) -> int:
        return sb.find_split_index(text, preferred_length)

    def _allocate_subslide_durations(
        self,
        total_duration: float,
        chunks: List[str],
        min_duration: float,
    ) -> List[float]:
        return sb.allocate_subslide_durations(total_duration, chunks, min_duration)

    def _build_slide_dict(
        self,
        segment: TranscriptSegment,
        slide_id: int,
        text: str,
        duration: float,
        sub_index: int,
        sub_total: int,
    ) -> Dict[str, Any]:
        return sb.build_slide_dict(segment, slide_id, text, duration, sub_index, sub_total)

    def _build_slides_payload(
        self,
        segment_payloads: List[Dict[str, Any]],
        csv_path: Path,
    ) -> Dict[str, Any]:
        return sb.build_slides_payload(segment_payloads, csv_path)

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

        csv_path = csv_path.expanduser().resolve()
        audio_dir = audio_dir.expanduser().resolve()

        if job_id is None:
            import uuid
            job_id = str(uuid.uuid4())

        if not csv_path.exists():
            raise FileNotFoundError(f"CSVファイルが見つかりません: {csv_path}")
        if not audio_dir.exists():
            raise FileNotFoundError(f"音声ディレクトリが見つかりません: {audio_dir}")
        if not audio_dir.is_dir():
            raise NotADirectoryError(f"音声ディレクトリではありません: {audio_dir}")

        topic = topic or csv_path.stem

        try:
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
        except (OSError, AttributeError, TypeError, ValueError, RuntimeError) as e:
            logger.debug(f"DB保存失敗（開始レコード、処理は継続）: {e}")
        except Exception as e:
            logger.debug(f"DB保存失敗（開始レコード、処理は継続）: {e}")

        logger.info(f"CSVタイムラインパイプライン開始: {csv_path} (Job ID: {job_id})")
        create_directories()

        if stage_modes:
            self.stage_modes.update(stage_modes)

        stage2_mode = self.stage_modes.get("stage2", "auto")
        stage3_mode = self.stage_modes.get("stage3", "auto")

        try:
            if progress_callback:
                progress_callback("CSV読み込み", 0.1, "CSVと行ごとの音声からタイムラインを構築します...")

            audio_files = find_audio_files(audio_dir)
            if not audio_files:
                # ディレクトリの内容を確認してデバッグ情報を提供
                all_files = list(audio_dir.glob("*"))
                logger.error(f"音声ファイルが見つかりません (dir={audio_dir})")
                logger.error(f"ディレクトリ内の全ファイル ({len(all_files)}個):")
                for f in sorted(all_files)[:20]:
                    logger.error(f"  - {f.name} ({f.stat().st_size} bytes)")
                if len(all_files) > 20:
                    logger.error(f"  ... 他 {len(all_files) - 20} 個")
                
                logger.error("対応フォーマット: WAV (.wav) のみ")
                logger.error("TTSバッチスクリプト (tts_batch_softalk_aquestalk.py) で 001.wav, 002.wav, ... を生成してください")
                raise RuntimeError(f"WAVファイルが見つかりません (dir={audio_dir})")

            audio_segments = build_audio_segments(audio_files)

            loader = CsvTranscriptLoader()
            transcript = await loader.load_from_csv(csv_path, audio_segments=audio_segments)

            combined_audio_path = settings.AUDIO_DIR / f"{csv_path.stem}_{job_id}_combined.wav"
            total_duration = combine_wav_files(audio_files, combined_audio_path)
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

            # BGM自動検出 (bgm.mp3 or bgm.wav)
            bgm_path = None
            for ext in [".mp3", ".wav"]:
                candidate = audio_dir / f"bgm{ext}"
                if candidate.exists():
                    bgm_path = candidate
                    logger.info(f"BGMを検出しました: {bgm_path}")
                    break

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
                
                # BGMがあればextrasに追加
                if bgm_path:
                    editing_extras["bgm_path"] = str(bgm_path)

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
                video_info = await self.video_composer.compose_video(
                    audio_info, slides_pkg, transcript, quality, bgm_path=bgm_path
                )

            logger.info(f"動画合成完了: {video_info.file_path}")
            if progress_callback:
                progress_callback("動画合成", 0.8, f"動画合成完了: {video_info.file_path}")

            # サムネイル生成
            if progress_callback:
                progress_callback("サムネイル生成", 0.82, "サムネイルを生成します...")
            try:
                first_slide_path = None
                if slide_contents and len(slide_contents) > 0:
                    # 最初のスライド画像を探す
                    slide_images_dir = settings.VIDEOS_DIR
                    first_slide_candidate = slide_images_dir / "slide_001.png"
                    if first_slide_candidate.exists():
                        first_slide_path = first_slide_candidate
                
                thumbnail_path = await self.video_composer.generate_thumbnail(
                    title=transcript.title,
                    first_slide_path=first_slide_path,
                )
                if thumbnail_path:
                    logger.info(f"サムネイル生成完了: {thumbnail_path}")
            except (OSError, AttributeError, TypeError, ValueError, RuntimeError) as e:
                logger.warning(f"サムネイル生成に失敗しました: {e}")
            except Exception as e:
                logger.warning(f"サムネイル生成に失敗しました: {e}")

            upload_result: Optional[UploadResult] = None
            youtube_url: Optional[str] = None
            metadata: Optional[Dict[str, Any]] = None
            publishing_result: Optional[Dict[str, Any]] = None

            if upload:
                upload_result, youtube_url, metadata, publishing_result = (
                    await self._run_stage3_upload(
                        video_info=video_info,
                        transcript=transcript,
                        thumbnail_path=thumbnail_path,
                        private_upload=private_upload,
                        stage3_mode=stage3_mode,
                        user_preferences=user_preferences,
                        progress_callback=progress_callback,
                    )
                )
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
            try:
                db_manager.update_generation_status(job_id, 'failed', str(e))
            except (OSError, AttributeError, TypeError, ValueError, RuntimeError) as db_e:
                logger.debug(f"DB更新失敗（失敗ステータス、処理は継続）: {db_e}")
            except Exception as db_e:
                logger.debug(f"DB更新失敗（失敗ステータス、処理は継続）: {db_e}")
            raise

        except (OSError, AttributeError, TypeError, ValueError, RuntimeError) as e:
            logger.error(f"Unexpected error (CSV Job {job_id}): {e}")
            try:
                db_manager.update_generation_status(job_id, 'failed', str(e))
            except (OSError, AttributeError, TypeError, ValueError, RuntimeError) as db_e:
                logger.debug(f"DB更新失敗（失敗ステータス、処理は継続）: {db_e}")
            except Exception as db_e:
                logger.debug(f"DB更新失敗（失敗ステータス、処理は継続）: {db_e}")
            raise PipelineError(str(e), recoverable=False)

        except Exception as e:
            logger.error(f"Unexpected error (CSV Job {job_id}): {e}")
            try:
                db_manager.update_generation_status(job_id, 'failed', str(e))
            except (OSError, AttributeError, TypeError, ValueError, RuntimeError) as db_e:
                logger.debug(f"DB更新失敗（失敗ステータス、処理は継続）: {db_e}")
            except Exception as db_e:
                logger.debug(f"DB更新失敗（失敗ステータス、処理は継続）: {db_e}")
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
        return await sr.run_legacy_stage1_with_fallback(topic, sources, self.audio_generator)

    async def _run_legacy_stage1(
        self,
        topic: str,
        sources: List[SourceInfo],
    ) -> tuple[Optional[Dict[str, Any]], AudioInfo]:
        """従来のGemini+TTSまたはNotebookLMモックを使用したStage1処理"""
        return await sr.run_legacy_stage1(topic, sources, self.audio_generator)

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
        """Stage2: 動画レンダリング処理の共通ロジック"""
        return await sr.run_stage2_video_render(
            audio_info, slides_pkg, transcript, quality,
            script_bundle, user_preferences, stage2_mode,
            timeline_planner=self.timeline_planner,
            editing_backend=self.editing_backend,
            thumbnail_generator=self.thumbnail_generator,
            video_composer=self.video_composer,
            editing_extras=editing_extras,
            progress_callback=progress_callback,
        )

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
        """Stage3: アップロード処理の共通ロジック"""
        return await sr.run_stage3_upload(
            video_info, transcript, thumbnail_path,
            private_upload, stage3_mode, user_preferences,
            metadata_generator=self.metadata_generator,
            platform_adapter=self.platform_adapter,
            publishing_queue=self.publishing_queue,
            uploader=self.uploader,
            progress_callback=progress_callback,
        )

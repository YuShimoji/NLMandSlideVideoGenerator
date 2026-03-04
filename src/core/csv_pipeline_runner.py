"""CSVタイムラインパイプライン実行関数

ModularVideoPipeline.run_csv_timeline のロジックを
スタンドアロン関数として抽出。pipeline.py から分離。
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from pathlib import Path

from config.settings import settings, create_directories

from .utils.logger import logger
from .exceptions import PipelineError
from .models import PipelineArtifacts
from .persistence import db_manager

from notebook_lm.audio_generator import AudioInfo
from notebook_lm.transcript_processor import TranscriptInfo
from notebook_lm.csv_transcript_loader import CsvTranscriptLoader
from slides.slide_generator import SlidesPackage
from video_editor.video_composer import VideoInfo
from youtube.uploader import UploadResult

from .interfaces import (
    ISlideGenerator,
    IVideoComposer,
    ITimelinePlanner,
    IEditingBackend,
    IMetadataGenerator,
    IPlatformAdapter,
    IPublishingQueue,
    IUploader,
)
from . import slide_builder as sb
from . import stage_runners as sr
from .csv_audio_utils import find_audio_files, build_audio_segments, combine_wav_files


async def run_csv_timeline(
    csv_path: Path,
    audio_dir: Path,
    *,
    slide_generator: ISlideGenerator,
    video_composer: IVideoComposer,
    metadata_generator: IMetadataGenerator,
    uploader: IUploader,
    timeline_planner: Optional[ITimelinePlanner] = None,
    editing_backend: Optional[IEditingBackend] = None,
    platform_adapter: Optional[IPlatformAdapter] = None,
    publishing_queue: Optional[IPublishingQueue] = None,
    stage_modes: Optional[Dict[str, str]] = None,
    topic: Optional[str] = None,
    quality: str = "1080p",
    private_upload: bool = True,
    upload: bool = False,
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
        job_id = str(uuid.uuid4())

    if not csv_path.exists():
        raise FileNotFoundError(f"CSVファイルが見つかりません: {csv_path}")
    if not audio_dir.exists():
        raise FileNotFoundError(f"音声ディレクトリが見つかりません: {audio_dir}")
    if not audio_dir.is_dir():
        raise NotADirectoryError(f"音声ディレクトリではありません: {audio_dir}")

    topic = topic or csv_path.stem

    resolved_modes = {"stage1": "auto", "stage2": "auto", "stage3": "auto"}
    if stage_modes:
        resolved_modes.update(stage_modes)
    stage2_mode = resolved_modes.get("stage2", "auto")
    stage3_mode = resolved_modes.get("stage3", "auto")

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

    try:
        if progress_callback:
            progress_callback("CSV読み込み", 0.1, "CSVと行ごとの音声からタイムラインを構築します...")

        audio_files = find_audio_files(audio_dir)
        if not audio_files:
            all_files = list(audio_dir.glob("*"))
            logger.error(f"音声ファイルが見つかりません (dir={audio_dir})")
            logger.error(f"ディレクトリ内の全ファイル ({len(all_files)}個):")
            for f in sorted(all_files)[:20]:
                logger.error(f"  - {f.name} ({f.stat().st_size} bytes)")
            if len(all_files) > 20:
                logger.error(f"  ... 他 {len(all_files) - 20} 個")
            logger.error("対応フォーマット: WAV (.wav) のみ")
            logger.error("ヒント: 事前にYMM4や他のツールでWAVファイル（001.wav, 002.wav, ...）を準備してください")
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

        slide_contents: list[dict[str, Any]] = []
        segment_payloads: List[Dict[str, Any]] = []
        next_slide_id = 1
        for idx, seg in enumerate(transcript.segments):
            segment_slides = sb.expand_segment_into_slides(seg, next_slide_id)
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

        slides_payload = sb.build_slides_payload(
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

        slides_pkg = await slide_generator.create_slides_from_content(
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

        if timeline_planner and editing_backend:
            if progress_callback:
                progress_callback("タイムライン計画", 0.6, "動画のタイムラインを計画します...")
            logger.info(f"Stage2モード: {stage2_mode}")
            timeline_plan = await timeline_planner.build_plan(
                script={"segments": transcript.segments},
                audio=audio_info,
                user_preferences=user_preferences,
            )
            if progress_callback:
                progress_callback("動画レンダリング", 0.7, "MoviePyで動画をレンダリングします...")

            if bgm_path:
                editing_extras["bgm_path"] = str(bgm_path)

            video_info = await editing_backend.render(
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
            video_info = await video_composer.compose_video(
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
                slide_images_dir = settings.VIDEOS_DIR
                first_slide_candidate = slide_images_dir / "slide_001.png"
                if first_slide_candidate.exists():
                    first_slide_path = first_slide_candidate

            thumbnail_path = await video_composer.generate_thumbnail(
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
                await sr.run_stage3_upload(
                    video_info=video_info,
                    transcript=transcript,
                    thumbnail_path=thumbnail_path,
                    private_upload=private_upload,
                    stage3_mode=stage3_mode,
                    user_preferences=user_preferences,
                    metadata_generator=metadata_generator,
                    platform_adapter=platform_adapter,
                    publishing_queue=publishing_queue,
                    uploader=uploader,
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

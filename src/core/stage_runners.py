"""パイプラインステージ実行関数

ModularVideoPipeline の各ステージ実行ロジックを関数として抽出。
pipeline.py から分離。
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from pathlib import Path

from config.settings import settings
from .utils.logger import logger
from .llm_provider import create_llm_provider

from notebook_lm.source_collector import SourceInfo
from notebook_lm.audio_generator import AudioInfo
from notebook_lm.transcript_processor import TranscriptInfo
from notebook_lm.gemini_integration import GeminiIntegration, ScriptInfo
from slides.slide_generator import SlidesPackage
from video_editor.models import VideoInfo
from youtube.uploader import UploadResult

from .interfaces import (
    IAudioGenerator,
    ITimelinePlanner,
    IEditingBackend,
    IMetadataGenerator,
    IPlatformAdapter,
    IPublishingQueue,
    IUploader,
    ThumbnailGeneratorProtocol,
)
from .segment_duration_validator import validate_segments, adjust_segments


async def run_legacy_stage1(
    topic: str,
    sources: List[SourceInfo],
    audio_generator: IAudioGenerator,
) -> tuple[Optional[Dict[str, Any]], AudioInfo]:
    """従来のGemini+TTSまたはNotebookLMモックを使用したStage1処理"""

    script_bundle: Optional[Dict[str, Any]] = None

    # LLM プロバイダー生成 (LLM_PROVIDER env var で切替可能)
    llm_api_key = settings.GEMINI_API_KEY or os.environ.get("LLM_API_KEY", "")
    if llm_api_key:
        logger.info("LLM によるスクリプト・スライド生成パスを使用します")
        try:
            llm_provider = create_llm_provider(api_key=llm_api_key)
            gemini = GeminiIntegration(api_key=llm_api_key, llm_provider=llm_provider)
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

            # SP-044: セグメント粒度検証 + 自動調整
            if isinstance(script_bundle, dict) and "segments" in script_bundle:
                segments = script_bundle["segments"]
                validation = validate_segments(segments, 300.0)
                logger.info(f"SP-044 検証: {validation.message}")
                if not validation.is_ok:
                    logger.warning(f"SP-044 セグメント検証: {validation.status} - {validation.message}")
                    adjusted = await adjust_segments(segments, validation, topic=topic)
                    if adjusted is not segments:
                        script_bundle["segments"] = adjusted
                        logger.info(f"SP-044 自動調整適用: {len(segments)}→{len(adjusted)}セグメント")

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
                    slide_payload: List[Dict[str, Any]] = []
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
                    if script_bundle:
                        script_bundle.setdefault("slides", slide_payload)
                    logger.info(f"script_bundle にスライド情報を追加: {len(slide_payload)}枚")
                else:
                    logger.warning("Geminiスライド生成結果が空でした")
            except (OSError, AttributeError, TypeError, ValueError, RuntimeError) as slide_err:
                logger.warning(f"Geminiスライド生成でエラーが発生しました（フォールバック継続）: {slide_err}")
            except Exception as slide_err:
                logger.warning(f"Geminiスライド生成でエラーが発生しました（フォールバック継続）: {slide_err}")

        except (OSError, AttributeError, TypeError, ValueError, RuntimeError) as exc:
            logger.warning(f"Gemini パスでエラーが発生したため従来モックにフォールバックします: {exc}")
        except Exception as exc:
            logger.warning(f"Gemini パスでエラーが発生したため従来モックにフォールバックします: {exc}")

    # フォールバック: 既存AudioGeneratorのみ
    audio_info = await audio_generator.generate_audio(sources)
    return script_bundle, audio_info


async def run_legacy_stage1_with_fallback(
    topic: str,
    sources: List[SourceInfo],
    audio_generator: IAudioGenerator,
) -> tuple[Optional[Dict[str, Any]], AudioInfo]:
    """従来 Stage1 処理（フォールバック付き）"""
    try:
        return await run_legacy_stage1(topic, sources, audio_generator)
    except (OSError, AttributeError, TypeError, ValueError, RuntimeError) as e:
        logger.warning(f"Legacy Stage1 failed: {e}. Using minimal fallback...")
        audio_info = await audio_generator.generate_audio(sources)
        return None, audio_info
    except Exception as e:
        logger.warning(f"Legacy Stage1 failed: {e}. Using minimal fallback...")
        audio_info = await audio_generator.generate_audio(sources)
        return None, audio_info


async def run_stage2_video_render(
    audio_info: AudioInfo,
    slides_pkg: SlidesPackage,
    transcript: TranscriptInfo,
    quality: str,
    script_bundle: Optional[Dict[str, Any]],
    user_preferences: Optional[Dict[str, Any]],
    stage2_mode: str,
    *,
    timeline_planner: Optional[ITimelinePlanner] = None,
    editing_backend: Optional[IEditingBackend] = None,
    thumbnail_generator: Optional[ThumbnailGeneratorProtocol] = None,
    editing_extras: Optional[Dict[str, Any]] = None,
    progress_callback: Optional[Callable[[str, float, str], None]] = None,
) -> tuple[VideoInfo, Optional[Path], Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Stage2: 動画レンダリング処理

    Returns:
        tuple: (video_info, thumbnail_path, timeline_plan, editing_outputs)
    """
    thumbnail_path: Optional[Path] = None
    timeline_plan: Optional[Dict[str, Any]] = None
    editing_outputs: Optional[Dict[str, Any]] = None

    if timeline_planner and editing_backend:
        if progress_callback:
            progress_callback("タイムライン計画", 0.7, "動画のタイムラインを計画します...")
        logger.info(f"Stage2モード: {stage2_mode}")

        timeline_plan = await timeline_planner.build_plan(
            script=script_bundle or {"segments": transcript.segments},
            audio=audio_info,
            user_preferences=user_preferences,
        )

        if progress_callback:
            progress_callback("動画レンダリング", 0.75, "動画をレンダリングします...")

        if editing_extras is None:
            editing_extras = {"export_outputs": {}}
        video_info = await editing_backend.render(
            timeline_plan=timeline_plan,
            audio=audio_info,
            slides=slides_pkg,
            transcript=transcript,
            quality=quality,
            extras=editing_extras,
        )
        editing_outputs = editing_extras.get("export_outputs") or None

        # サムネイル生成（オプション）
        if thumbnail_generator and user_preferences and user_preferences.get("generate_thumbnail", False):
            try:
                thumbnail_style = user_preferences.get("thumbnail_style", "modern")
                thumbnail_info = await thumbnail_generator.generate(
                    video=video_info,
                    script=script_bundle or {"title": transcript.title},
                    slides=slides_pkg,
                    style=thumbnail_style
                )
                thumbnail_path = thumbnail_info.file_path
                logger.info(f"サムネイル生成完了: {thumbnail_path}")
            except (OSError, AttributeError, TypeError, ValueError, RuntimeError) as thumb_err:
                logger.warning(f"サムネイル生成に失敗しました: {thumb_err}")
                thumbnail_path = None
            except Exception as thumb_err:
                logger.warning(f"サムネイル生成に失敗しました: {thumb_err}")
                thumbnail_path = None
    else:
        raise ValueError(
            "timeline_planner and editing_backend are required. "
            "VideoComposer (Path B) has been removed; use YMM4 editing backend."
        )

    logger.info(f"動画合成完了: {video_info.file_path}")
    if progress_callback:
        progress_callback("動画合成", 0.8, f"動画合成完了: {video_info.file_path}")

    return video_info, thumbnail_path, timeline_plan, editing_outputs


async def run_stage3_upload(
    video_info: VideoInfo,
    transcript: TranscriptInfo,
    thumbnail_path: Optional[Path],
    private_upload: bool,
    stage3_mode: str,
    user_preferences: Optional[Dict[str, Any]],
    *,
    metadata_generator: IMetadataGenerator,
    platform_adapter: Optional[IPlatformAdapter] = None,
    publishing_queue: Optional[IPublishingQueue] = None,
    uploader: Optional[IUploader] = None,
    progress_callback: Optional[Callable[[str, float, str], None]] = None,
) -> tuple[Optional[UploadResult], Optional[str], Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Stage3: アップロード処理

    Returns:
        tuple: (upload_result, youtube_url, metadata, publishing_result)
    """
    if progress_callback:
        progress_callback("アップロード準備", 0.9, "メタデータを生成します...")

    metadata = await metadata_generator.generate_metadata(transcript)
    metadata["privacy_status"] = "private" if private_upload else "public"
    metadata["language"] = settings.YOUTUBE_SETTINGS.get("default_language", "ja")

    upload_result: Optional[UploadResult] = None
    youtube_url: Optional[str] = None
    publishing_result: Optional[Dict[str, Any]] = None

    if platform_adapter:
        if progress_callback:
            progress_callback("YouTubeアップロード", 0.95, "YouTubeに動画をアップロードします...")
        logger.info(f"Stage3モード: {stage3_mode}")

        package = {
            "video": video_info,
            "metadata": metadata,
            "thumbnail": thumbnail_path,
            "schedule": user_preferences.get("schedule") if user_preferences else None,
        }

        if publishing_queue:
            queue_id = await publishing_queue.enqueue(
                package,
                schedule=package.get("schedule"),
            )
            logger.info(f"投稿キューに登録しました: {queue_id}")

        publishing_result = await platform_adapter.publish(
            package,
            options={"mode": stage3_mode},
        )
        youtube_url = publishing_result.get("url") if publishing_result else None
    else:
        if progress_callback:
            progress_callback("YouTubeアップロード", 0.95, "YouTube APIでアップロードします...")
        if uploader is None:
            raise ValueError("uploader is required when platform_adapter is not provided")
        await uploader.authenticate()
        upload_result = await uploader.upload_video(
            video=video_info,
            metadata=metadata,
            thumbnail_path=thumbnail_path,
        )
        youtube_url = upload_result.video_url if upload_result else None
        logger.success(f"アップロード完了: {youtube_url}")

    return upload_result, youtube_url, metadata, publishing_result

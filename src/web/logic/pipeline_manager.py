"""
Pipeline execution logic for web application
"""
import asyncio
from typing import Optional, Dict, Any, Callable

from src.core.pipeline import build_default_pipeline


async def run_pipeline_async(
    topic: str,
    urls: Optional[list] = None,
    quality: str = "1080p",
    private_upload: bool = True,
    upload: bool = True,
    stage_modes: Optional[Dict[str, str]] = None,
    user_preferences: Optional[Dict[str, Any]] = None,
    progress_callback: Optional[Callable[[str, float, str], None]] = None,
    job_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    非同期でパイプラインを実行

    Args:
        topic: 動画トピック
        urls: 追加URLリスト
        quality: 動画品質
        private_upload: プライベートアップロード
        upload: YouTubeアップロード
        stage_modes: ステージモード設定
        user_preferences: ユーザー設定
        progress_callback: プログレスコールバック
        job_id: ジョブID

    Returns:
        パイプライン実行結果
    """
    try:
        # Build pipeline
        pipeline = build_default_pipeline()

        # Execute pipeline
        result = await pipeline.run(
            topic=topic,
            urls=urls,
            quality=quality,
            private_upload=private_upload,
            upload=upload,
            stage_modes=stage_modes,
            user_preferences=user_preferences,
            progress_callback=progress_callback,
            job_id=job_id,
        )

        return result

    except Exception as e:
        raise Exception(f"パイプライン実行失敗: {str(e)}")


async def get_pipeline_status(job_id: str) -> Dict[str, Any]:
    """
    パイプライン実行状態を取得

    Args:
        job_id: ジョブID

    Returns:
        実行状態
    """
    # TODO: Implement full status tracking with real-time updates (B1-1)
    # Currently uses db_manager for basic status lookup
    try:
        from core.persistence import db_manager
        record = db_manager.get_generation_record(job_id)
        if record:
            return {
                "status": record.get("status", "unknown"),
                "job_id": job_id,
                "topic": record.get("topic", ""),
                "created_at": record.get("created_at"),
                "completed_at": record.get("completed_at"),
                "error": record.get("error_message"),
                "artifacts": record.get("artifacts"),
            }
        return {"status": "not_found", "job_id": job_id}
    except Exception:
        return {"status": "unknown", "job_id": job_id}


# In-memory cancellation flags (simple implementation)
_cancellation_flags: Dict[str, bool] = {}


async def cancel_pipeline(job_id: str) -> bool:
    """
    パイプライン実行をキャンセル

    Args:
        job_id: ジョブID

    Returns:
        キャンセル成功フラグ
    """
    # TODO: Implement full cancellation logic with async task management (B1-2)
    # Currently sets a flag that can be checked by long-running operations
    try:
        from core.persistence import db_manager
        _cancellation_flags[job_id] = True
        db_manager.update_generation_status(job_id, "cancelled", "User requested cancellation")
        return True
    except Exception:
        return False


def is_cancelled(job_id: str) -> bool:
    """キャンセルフラグを確認"""
    return _cancellation_flags.get(job_id, False)


def clear_cancellation_flag(job_id: str) -> None:
    """キャンセルフラグをクリア"""
    _cancellation_flags.pop(job_id, None)

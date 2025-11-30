"""
Pipeline execution logic for web application

ジョブ管理機能を提供:
- 非同期パイプライン実行
- リアルタイム進捗追跡
- キャンセル機能
- ステータス管理
"""
import asyncio
import uuid
from typing import Optional, Dict, Any, Callable, Set
from datetime import datetime

from src.core.pipeline import build_default_pipeline


# アクティブなジョブを追跡
_active_jobs: Dict[str, asyncio.Task] = {}
_job_progress: Dict[str, Dict[str, Any]] = {}


def generate_job_id() -> str:
    """ユニークなジョブIDを生成"""
    return f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"


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
        job_id: ジョブID（省略時は自動生成）

    Returns:
        パイプライン実行結果
    """
    # ジョブIDを生成
    if not job_id:
        job_id = generate_job_id()
    
    # 進捗追跡を初期化
    _job_progress[job_id] = {
        "status": "running",
        "progress": 0.0,
        "stage": "initializing",
        "message": "パイプライン初期化中...",
        "started_at": datetime.now().isoformat(),
    }
    
    # 進捗コールバックをラップしてDB更新も行う
    def wrapped_progress_callback(stage: str, progress: float, message: str):
        _job_progress[job_id] = {
            "status": "running",
            "progress": progress,
            "stage": stage,
            "message": message,
            "updated_at": datetime.now().isoformat(),
        }
        
        # DBにも保存
        try:
            from core.persistence import db_manager
            db_manager.update_generation_progress(job_id, progress, stage, message)
        except Exception:
            pass  # DB更新失敗は無視
        
        # 元のコールバックも呼び出し
        if progress_callback:
            progress_callback(stage, progress, message)
    
    try:
        # キャンセルチェック
        if is_cancelled(job_id):
            raise asyncio.CancelledError("Job cancelled before start")
        
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
            progress_callback=wrapped_progress_callback,
            job_id=job_id,
        )
        
        # 完了を記録
        _job_progress[job_id] = {
            "status": "completed",
            "progress": 1.0,
            "stage": "completed",
            "message": "パイプライン完了",
            "completed_at": datetime.now().isoformat(),
        }

        return result

    except asyncio.CancelledError:
        _job_progress[job_id] = {
            "status": "cancelled",
            "progress": _job_progress.get(job_id, {}).get("progress", 0.0),
            "stage": "cancelled",
            "message": "ユーザーによりキャンセルされました",
            "cancelled_at": datetime.now().isoformat(),
        }
        raise
    except Exception as e:
        _job_progress[job_id] = {
            "status": "failed",
            "progress": _job_progress.get(job_id, {}).get("progress", 0.0),
            "stage": "error",
            "message": str(e),
            "failed_at": datetime.now().isoformat(),
        }
        raise Exception(f"パイプライン実行失敗: {str(e)}")
    finally:
        # クリーンアップ
        _active_jobs.pop(job_id, None)
        clear_cancellation_flag(job_id)


async def get_pipeline_status(job_id: str) -> Dict[str, Any]:
    """
    パイプライン実行状態を取得（リアルタイム進捗対応）

    Args:
        job_id: ジョブID

    Returns:
        実行状態（進捗情報を含む）
    """
    # まずメモリ内の進捗情報を確認（リアルタイム）
    if job_id in _job_progress:
        progress_info = _job_progress[job_id]
        return {
            "status": progress_info.get("status", "unknown"),
            "job_id": job_id,
            "progress": progress_info.get("progress", 0.0),
            "stage": progress_info.get("stage", ""),
            "message": progress_info.get("message", ""),
            "is_active": job_id in _active_jobs,
            **{k: v for k, v in progress_info.items() 
               if k not in ["status", "progress", "stage", "message"]},
        }
    
    # DBから履歴を取得
    try:
        from core.persistence import db_manager
        record = db_manager.get_generation_record(job_id)
        if record:
            metadata = record.get("metadata", {}) or {}
            return {
                "status": record.get("status", "unknown"),
                "job_id": job_id,
                "topic": record.get("topic", ""),
                "progress": metadata.get("progress", 0.0),
                "stage": metadata.get("current_stage", ""),
                "message": metadata.get("progress_message", ""),
                "created_at": record.get("created_at"),
                "completed_at": record.get("completed_at"),
                "duration": record.get("duration"),
                "error": record.get("error_message"),
                "artifacts": record.get("artifacts"),
                "is_active": False,
            }
        return {"status": "not_found", "job_id": job_id, "is_active": False}
    except Exception as e:
        return {"status": "unknown", "job_id": job_id, "error": str(e), "is_active": False}


def get_active_jobs() -> Dict[str, Dict[str, Any]]:
    """アクティブなジョブ一覧を取得"""
    return {
        job_id: {
            **_job_progress.get(job_id, {}),
            "is_active": True,
        }
        for job_id in _active_jobs.keys()
    }


def list_recent_jobs(limit: int = 20) -> list:
    """最近のジョブ一覧を取得"""
    try:
        from core.persistence import db_manager
        records = db_manager.get_generation_history(limit=limit)
        return records
    except Exception:
        return []


# In-memory cancellation flags
_cancellation_flags: Dict[str, bool] = {}


async def cancel_pipeline(job_id: str) -> bool:
    """
    パイプライン実行をキャンセル

    Args:
        job_id: ジョブID

    Returns:
        キャンセル成功フラグ
    """
    try:
        # キャンセルフラグを設定
        _cancellation_flags[job_id] = True
        
        # アクティブなタスクがあればキャンセル
        if job_id in _active_jobs:
            task = _active_jobs[job_id]
            if not task.done():
                task.cancel()
        
        # 進捗情報を更新
        if job_id in _job_progress:
            _job_progress[job_id]["status"] = "cancelling"
            _job_progress[job_id]["message"] = "キャンセル処理中..."
        
        # DBステータスを更新
        from core.persistence import db_manager
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


async def start_pipeline_task(
    topic: str,
    **kwargs
) -> str:
    """
    パイプラインをバックグラウンドタスクとして開始

    Args:
        topic: 動画トピック
        **kwargs: run_pipeline_async に渡す追加引数

    Returns:
        ジョブID
    """
    job_id = kwargs.pop("job_id", None) or generate_job_id()
    
    # タスクを作成
    task = asyncio.create_task(
        run_pipeline_async(topic=topic, job_id=job_id, **kwargs)
    )
    
    # アクティブジョブに登録
    _active_jobs[job_id] = task
    
    return job_id

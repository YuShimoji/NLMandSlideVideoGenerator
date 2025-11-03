"""
運用・監視 API サーバー
FastAPI ベースの運用ダッシュボードと監視機能
"""
import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, PlainTextResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
from pathlib import Path
import uvicorn

from config.settings import settings
from core.pipeline import build_default_pipeline

# Prometheus メトリクス（オプション）
try:
    from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    # モックメトリクス
    class MockMetric:
        def inc(self, value=1): pass
        def observe(self, value): pass
        def set(self, value): pass
        def labels(self, *args, **kwargs):
            return self

    Counter = Histogram = Gauge = lambda *args, **kwargs: MockMetric()

# メトリクス定義
REQUEST_COUNT = Counter('api_requests_total', 'Total API requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('api_request_duration_seconds', 'API request duration', ['method', 'endpoint'])
ACTIVE_PIPELINES = Gauge('active_pipelines', 'Number of active pipelines')
VIDEO_GENERATION_COUNT = Counter('video_generations_total', 'Total video generations', ['status'])
SYSTEM_HEALTH = Gauge('system_health', 'System health status (0=unhealthy, 1=healthy)')

logger = logging.getLogger(__name__)


class OperationalAPIServer:
    """運用・監視 API サーバー"""

    def __init__(self):
        self.app = FastAPI(
            title="NLMandSlideVideoGenerator Operational API",
            description="運用・監視 API for video generation system",
            version="1.0.0"
        )

        # テンプレート設定
        self.templates_dir = Path(__file__).parent / "templates"
        self.templates_dir.mkdir(exist_ok=True)
        self.templates = Jinja2Templates(directory=str(self.templates_dir))

        # スタティックファイル設定
        self.static_dir = Path(__file__).parent / "static"
        self.static_dir.mkdir(exist_ok=True)
        self.app.mount("/static", StaticFiles(directory=str(self.static_dir)), name="static")

        self.setup_middleware()
        self.setup_routes()
        self.setup_metrics()

        # システム状態
        self.system_status = {
            "healthy": True,
            "last_health_check": datetime.now(),
            "active_jobs": {},
            "recent_logs": [],
            "performance_stats": {}
        }

    def setup_middleware(self):
        """ミドルウェア設定"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # 本番では制限する
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def setup_routes(self):
        """ルート設定"""

        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard(request: Request):
            """Web ダッシュボード"""
            self._increment_request_count(method="GET", endpoint="/", status="200")

            # システム状態を取得
            status = await self.get_dashboard_data()

            return self.templates.TemplateResponse("dashboard.html", {
                "request": request,
                **status
            })

        @self.app.get("/jobs/{job_id}", response_class=HTMLResponse)
        async def job_detail(request: Request, job_id: str):
            """ジョブ詳細ページ"""
            self._increment_request_count(method="GET", endpoint="/jobs/{job_id}", status="200")

            # ジョブ情報を取得
            job_info = await self.get_job_detail(job_id)
            if not job_info:
                raise HTTPException(status_code=404, detail="Job not found")

            return self.templates.TemplateResponse("job_detail.html", {
                "request": request,
                "job": job_info
            })

        @self.app.get("/health")
        async def health_check():
            """ヘルスチェックエンドポイント"""
            self._increment_request_count(method="GET", endpoint="/health", status="200")

            health_status = await self.perform_health_check()
            status_code = 200 if health_status["healthy"] else 503

            self._increment_request_count(method="GET", endpoint="/health", status=str(status_code))
            return JSONResponse(content=health_status, status_code=status_code)

        @self.app.get("/metrics")
        async def metrics():
            """Prometheus メトリクスエンドポイント"""
            if PROMETHEUS_AVAILABLE:
                return PlainTextResponse(
                    generate_latest(),
                    media_type=CONTENT_TYPE_LATEST
                )
            else:
                return PlainTextResponse("# Prometheus not available\n")

        @self.app.get("/status")
        async def system_status():
            """システム状態取得"""
            self._increment_request_count(method="GET", endpoint="/status", status="200")

            return {
                "timestamp": datetime.now().isoformat(),
                "system_health": self.system_status["healthy"],
                "active_jobs_count": len(self.system_status["active_jobs"]),
                "performance_stats": self.system_status["performance_stats"],
                "recent_activity": self.system_status["recent_logs"][-10:]  # 最新10件
            }

        @self.app.get("/jobs")
        async def list_jobs():
            """ジョブ一覧"""
            self._increment_request_count(method="GET", endpoint="/jobs", status="200")

            return {
                "active_jobs": self.system_status["active_jobs"],
                "total_active": len(self.system_status["active_jobs"])
            }

        @self.app.get("/logs")
        async def get_logs(limit: int = 100):
            """最新ログ取得"""
            self._increment_request_count(method="GET", endpoint="/logs", status="200")

            return {
                "logs": self.system_status["recent_logs"][-limit:],
                "total_lines": len(self.system_status["recent_logs"])
            }

        @self.app.post("/jobs/{job_id}/cancel")
        async def cancel_job(job_id: str):
            """ジョブキャンセル"""
            self._increment_request_count(method="POST", endpoint="/jobs/{job_id}/cancel", status="200")

            if job_id in self.system_status["active_jobs"]:
                # 実際のキャンセル処理（モック）
                self.system_status["active_jobs"].pop(job_id, None)
                self.log_activity(f"Job {job_id} cancelled")
                return {"status": "cancelled", "job_id": job_id}
            else:
                raise HTTPException(status_code=404, detail="Job not found")

        @self.app.get("/config")
        async def get_config():
            """設定情報取得（機密情報除く）"""
            self._increment_request_count(method="GET", endpoint="/config", status="200")

            # 機密情報を除去
            safe_config = {
                "APP_NAME": settings.APP_NAME,
                "VERSION": settings.VERSION,
                "DEBUG": settings.DEBUG,
                "PIPELINE_COMPONENTS": settings.PIPELINE_COMPONENTS,
                "YOUTUBE_SETTINGS": {
                    "privacy_status": settings.YOUTUBE_SETTINGS.get("privacy_status"),
                    "default_language": settings.YOUTUBE_SETTINGS.get("default_language")
                }
            }
            return safe_config

        @self.app.post("/maintenance/cleanup")
        async def cleanup_old_files(background_tasks: BackgroundTasks, days: int = 7):
            """古いファイルのクリーンアップ"""
            self._increment_request_count(method="POST", endpoint="/maintenance/cleanup", status="200")

            background_tasks.add_task(self.perform_cleanup, days)
            self.log_activity(f"Cleanup task scheduled for files older than {days} days")
            return {"status": "scheduled", "cleanup_days": days}

    def setup_metrics(self):
        """メトリクス初期化"""
        if PROMETHEUS_AVAILABLE:
            logger.info("Prometheus metrics initialized")
        else:
            logger.warning("Prometheus not available, using mock metrics")

        # システムヘルスを初期化
        SYSTEM_HEALTH.set(1)

    def _increment_request_count(self, method: str, endpoint: str, status: str):
        """API リクエストカウントを安全に増加"""
        try:
            REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
        except AttributeError:
            # MockMetric の場合はそのまま inc 可能
            REQUEST_COUNT.inc()

    async def perform_health_check(self) -> Dict[str, Any]:
        """ヘルスチェック実行"""
        checks = {
            "database": await self.check_database(),
            "file_system": await self.check_file_system(),
            "api_keys": await self.check_api_keys(),
            "pipeline": await self.check_pipeline()
        }

        healthy = all(check["status"] == "healthy" for check in checks.values())

        self.system_status["healthy"] = healthy
        self.system_status["last_health_check"] = datetime.now()

        SYSTEM_HEALTH.set(1 if healthy else 0)

        return {
            "healthy": healthy,
            "timestamp": datetime.now().isoformat(),
            "checks": checks
        }

    async def check_database(self) -> Dict[str, Any]:
        """データベース接続チェック"""
        # SQLite や他の DB があればチェック
        # 現在はファイルシステムベースなのでスキップ
        return {"status": "healthy", "message": "File-based storage"}

    async def check_file_system(self) -> Dict[str, Any]:
        """ファイルシステムチェック"""
        try:
            # 必要なディレクトリが存在するかチェック
            required_dirs = [
                settings.DATA_DIR,
                settings.VIDEOS_DIR,
                settings.AUDIO_DIR,
                settings.SLIDES_DIR
            ]

            for dir_path in required_dirs:
                if not dir_path.exists():
                    return {"status": "unhealthy", "message": f"Missing directory: {dir_path}"}

            # 書き込み権限チェック
            test_file = settings.DATA_DIR / ".health_check"
            test_file.write_text("test")
            test_file.unlink()

            return {"status": "healthy", "message": "File system OK"}

        except Exception as e:
            return {"status": "unhealthy", "message": f"File system error: {e}"}

    async def check_api_keys(self) -> Dict[str, Any]:
        """API キー設定チェック"""
        required_keys = []

        if settings.PIPELINE_COMPONENTS.get("script_provider") == "gemini":
            required_keys.append(("GEMINI_API_KEY", settings.GEMINI_API_KEY))

        if settings.TTS_SETTINGS.get("provider") and settings.TTS_SETTINGS["provider"] != "none":
            required_keys.append(("TTS settings", bool(settings.TTS_SETTINGS)))

        missing_keys = [key for key, value in required_keys if not value]

        if missing_keys:
            return {"status": "warning", "message": f"Missing API keys: {missing_keys}"}
        else:
            return {"status": "healthy", "message": "API keys configured"}

    async def check_pipeline(self) -> Dict[str, Any]:
        """パイプライン初期化チェック"""
        try:
            pipeline = build_default_pipeline()
            return {"status": "healthy", "message": "Pipeline initialized successfully"}
        except Exception as e:
            return {"status": "unhealthy", "message": f"Pipeline initialization failed: {e}"}

    async def perform_cleanup(self, days: int):
        """古いファイルのクリーンアップ"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            cleaned_files = []

            # クリーンアップ対象ディレクトリ
            cleanup_dirs = [
                settings.VIDEOS_DIR,
                settings.AUDIO_DIR,
                settings.SLIDES_DIR,
                settings.SCRIPTS_DIR
            ]

            for dir_path in cleanup_dirs:
                if dir_path.exists():
                    for file_path in dir_path.glob("*"):
                        if file_path.is_file() and file_path.stat().st_mtime < cutoff_date.timestamp():
                            file_path.unlink()
                            cleaned_files.append(str(file_path))

            self.log_activity(f"Cleanup completed: {len(cleaned_files)} files removed")
            logger.info(f"Cleanup completed: {len(cleaned_files)} files removed")

        except Exception as e:
            self.log_activity(f"Cleanup failed: {e}")
            logger.error(f"Cleanup failed: {e}")

    def log_activity(self, message: str):
        """アクティビティログ記録"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "level": "info"
        }

        self.system_status["recent_logs"].append(log_entry)

        # ログを制限（最新1000件）
        if len(self.system_status["recent_logs"]) > 1000:
            self.system_status["recent_logs"] = self.system_status["recent_logs"][-1000:]

    def update_performance_stats(self, stats: Dict[str, Any]):
        """パフォーマンス統計更新"""
        self.system_status["performance_stats"].update(stats)

    async def get_dashboard_data(self) -> Dict[str, Any]:
        """ダッシュボード表示用のデータを取得"""
        from core.persistence import db_manager

        # システム状態
        health = await self.perform_health_check()

        # 最近のジョブ
        recent_jobs = db_manager.get_generation_history(limit=10)

        # 統計情報
        all_jobs = db_manager.get_generation_history(limit=1000)
        stats = {
            "total_jobs": len(all_jobs),
            "successful_jobs": len([j for j in all_jobs if j.get('status') == 'completed']),
            "failed_jobs": len([j for j in all_jobs if j.get('status') == 'failed']),
            "running_jobs": len([j for j in all_jobs if j.get('status') == 'running'])
        }

        return {
            "system_health": health,
            "recent_jobs": recent_jobs,
            "stats": stats,
            "timestamp": datetime.now().isoformat()
        }

    async def get_job_detail(self, job_id: str) -> Optional[Dict[str, Any]]:
        """ジョブ詳細情報を取得"""
        from core.persistence import db_manager

        # ジョブ履歴から検索
        jobs = db_manager.get_generation_history(limit=1000)
        for job in jobs:
            if job.get('job_id') == job_id:
                # JSON フィールドをパース
                if isinstance(job.get('artifacts'), str):
                    job['artifacts'] = json.loads(job['artifacts'])
                if isinstance(job.get('metadata'), str):
                    job['metadata'] = json.loads(job['metadata'])
                return job

        return None

# サーバーインスタンスと FastAPI アプリをエクスポート
server = OperationalAPIServer()
app = server.app


if __name__ == "__main__":
    # 開発サーバー起動
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

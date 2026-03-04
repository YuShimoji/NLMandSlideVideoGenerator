"""
データ永続化モジュール
生成履歴・設定・バックアップ機能
"""
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from contextlib import contextmanager

from config.settings import settings
from ..utils.logger import logger


class DatabaseManager:
    """データベースマネージャー"""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or settings.DATA_DIR / "database.db"
        self.db_path.parent.mkdir(exist_ok=True)
        self._init_database()

    def _init_database(self):
        """データベース初期化"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 生成履歴テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS generation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT UNIQUE,
                    topic TEXT,
                    status TEXT,
                    created_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    duration REAL,
                    artifacts TEXT,  -- JSON
                    error_message TEXT,
                    metadata TEXT   -- JSON
                )
            ''')

            # バッチジョブテーブル (バッチ処理システム用)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS batch_jobs (
                    job_id TEXT PRIMARY KEY,
                    config TEXT NOT NULL,  -- JSON serialized CSVJobConfig
                    status TEXT NOT NULL,  -- pending/running/completed/failed/retrying/cancelled
                    created_at TIMESTAMP NOT NULL,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    output_path TEXT,
                    youtube_url TEXT,
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    progress REAL DEFAULT 0.0,
                    metadata TEXT  -- JSON
                )
            ''')

            # バッチジョブのインデックス
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_batch_jobs_status
                ON batch_jobs(status)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_batch_jobs_created_at
                ON batch_jobs(created_at DESC)
            ''')

            # 設定履歴テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS config_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT,
                    value TEXT,  -- JSON
                    changed_at TIMESTAMP,
                    changed_by TEXT
                )
            ''')

            # バックアップテーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS backups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    backup_type TEXT,
                    file_path TEXT,
                    created_at TIMESTAMP,
                    size INTEGER,
                    checksum TEXT
                )
            ''')

            conn.commit()
            logger.info("Database initialized")

    @contextmanager
    def _get_connection(self):
        """データベース接続コンテキストマネージャー"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def save_generation_record(self, record: Dict[str, Any]) -> int:
        """生成履歴を保存"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO generation_history
                (job_id, topic, status, created_at, completed_at, duration, artifacts, error_message, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                record.get('job_id'),
                record.get('topic'),
                record.get('status'),
                record.get('created_at'),
                record.get('completed_at'),
                record.get('duration'),
                json.dumps(record.get('artifacts', {}), ensure_ascii=False),
                record.get('error_message'),
                json.dumps(record.get('metadata', {}), ensure_ascii=False)
            ))

            conn.commit()
            return cursor.lastrowid

    def get_generation_history(self, limit: int = 50, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """生成履歴を取得"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM generation_history"
            params = []

            if status:
                query += " WHERE status = ?"
                params.append(status)

            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [dict(row) for row in rows]

    def get_generation_record(self, job_id: str) -> Optional[Dict[str, Any]]:
        """特定のジョブIDの生成履歴を取得"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM generation_history WHERE job_id = ?",
                (job_id,)
            )
            row = cursor.fetchone()
            if row:
                record = dict(row)
                # JSON フィールドをパース
                if record.get('artifacts'):
                    try:
                        record['artifacts'] = json.loads(record['artifacts'])
                    except (json.JSONDecodeError, TypeError):
                        pass
                if record.get('metadata'):
                    try:
                        record['metadata'] = json.loads(record['metadata'])
                    except (json.JSONDecodeError, TypeError):
                        pass
                return record
            return None

    def update_generation_progress(
        self,
        job_id: str,
        progress: float,
        stage: str,
        message: str = ""
    ):
        """生成進捗を更新"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # メタデータを更新
            cursor.execute(
                "SELECT metadata FROM generation_history WHERE job_id = ?",
                (job_id,)
            )
            row = cursor.fetchone()
            if row:
                try:
                    metadata = json.loads(row['metadata'] or '{}')
                except (json.JSONDecodeError, TypeError):
                    metadata = {}
                
                metadata['progress'] = progress
                metadata['current_stage'] = stage
                metadata['progress_message'] = message
                metadata['last_updated'] = datetime.now().isoformat()
                
                cursor.execute(
                    "UPDATE generation_history SET metadata = ? WHERE job_id = ?",
                    (json.dumps(metadata, ensure_ascii=False), job_id)
                )
                conn.commit()

    def update_generation_status(self, job_id: str, status: str, error_message: Optional[str] = None):
        """生成ステータスを更新"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            if status == 'completed':
                cursor.execute('''
                    UPDATE generation_history
                    SET status = ?, completed_at = ?, duration = (
                        SELECT (julianday(?) - julianday(created_at)) * 86400.0
                        FROM generation_history
                        WHERE job_id = ?
                    )
                    WHERE job_id = ?
                ''', (status, datetime.now(), datetime.now(), job_id, job_id))
            else:
                cursor.execute('''
                    UPDATE generation_history
                    SET status = ?, error_message = ?
                    WHERE job_id = ?
                ''', (status, error_message, job_id))

            conn.commit()

    # Batch job operations
    def save_batch_job(self, job_result: Any) -> None:
        """バッチジョブを保存または更新

        Args:
            job_result: JobResult instance from batch.models
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO batch_jobs
                (job_id, config, status, created_at, started_at, completed_at,
                 output_path, youtube_url, error_message, retry_count, progress, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                job_result.job_id,
                json.dumps(job_result.config.to_dict(), ensure_ascii=False),
                job_result.status.value,
                job_result.created_at.isoformat(),
                job_result.started_at.isoformat() if job_result.started_at else None,
                job_result.completed_at.isoformat() if job_result.completed_at else None,
                str(job_result.output_path) if job_result.output_path else None,
                job_result.youtube_url,
                job_result.error_message,
                job_result.retry_count,
                job_result.progress,
                json.dumps(job_result.metadata, ensure_ascii=False),
            ))

            conn.commit()

    def get_batch_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """バッチジョブを取得

        Args:
            job_id: Job ID

        Returns:
            Job data as dict, or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM batch_jobs WHERE job_id = ?",
                (job_id,)
            )
            row = cursor.fetchone()
            if row:
                record = dict(row)
                # Parse JSON fields
                if record.get('config'):
                    try:
                        record['config'] = json.loads(record['config'])
                    except (json.JSONDecodeError, TypeError):
                        pass
                if record.get('metadata'):
                    try:
                        record['metadata'] = json.loads(record['metadata'])
                    except (json.JSONDecodeError, TypeError):
                        record['metadata'] = {}
                return record
            return None

    def get_batch_jobs(
        self,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "created_at DESC"
    ) -> List[Dict[str, Any]]:
        """バッチジョブの一覧を取得

        Args:
            status: Filter by status (optional)
            limit: Maximum number of jobs to return
            offset: Number of jobs to skip
            order_by: SQL ORDER BY clause

        Returns:
            List of job data as dicts
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM batch_jobs"
            params = []

            if status:
                query += " WHERE status = ?"
                params.append(status)

            query += f" ORDER BY {order_by} LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)
            rows = cursor.fetchall()

            result = []
            for row in rows:
                record = dict(row)
                # Parse JSON fields
                if record.get('config'):
                    try:
                        record['config'] = json.loads(record['config'])
                    except (json.JSONDecodeError, TypeError):
                        pass
                if record.get('metadata'):
                    try:
                        record['metadata'] = json.loads(record['metadata'])
                    except (json.JSONDecodeError, TypeError):
                        record['metadata'] = {}
                result.append(record)

            return result

    def update_batch_job_status(
        self,
        job_id: str,
        status: str,
        error_message: Optional[str] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None
    ) -> None:
        """バッチジョブのステータスを更新

        Args:
            job_id: Job ID
            status: New status
            error_message: Error message (optional)
            started_at: Start time (optional)
            completed_at: Completion time (optional)
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            updates = ["status = ?"]
            params = [status]

            if error_message is not None:
                updates.append("error_message = ?")
                params.append(error_message)

            if started_at is not None:
                updates.append("started_at = ?")
                params.append(started_at.isoformat())

            if completed_at is not None:
                updates.append("completed_at = ?")
                params.append(completed_at.isoformat())

            params.append(job_id)

            query = f"UPDATE batch_jobs SET {', '.join(updates)} WHERE job_id = ?"
            cursor.execute(query, params)

            conn.commit()

    def update_batch_job_progress(
        self,
        job_id: str,
        progress: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """バッチジョブの進捗を更新

        Args:
            job_id: Job ID
            progress: Progress percentage (0.0-100.0)
            metadata: Additional metadata (optional)
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            if metadata is not None:
                cursor.execute('''
                    UPDATE batch_jobs
                    SET progress = ?, metadata = ?
                    WHERE job_id = ?
                ''', (progress, json.dumps(metadata, ensure_ascii=False), job_id))
            else:
                cursor.execute('''
                    UPDATE batch_jobs
                    SET progress = ?
                    WHERE job_id = ?
                ''', (progress, job_id))

            conn.commit()

    def increment_batch_job_retry(self, job_id: str) -> int:
        """バッチジョブのリトライカウントを増加

        Args:
            job_id: Job ID

        Returns:
            New retry count
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE batch_jobs
                SET retry_count = retry_count + 1, status = 'retrying'
                WHERE job_id = ?
            ''', (job_id,))

            cursor.execute(
                "SELECT retry_count FROM batch_jobs WHERE job_id = ?",
                (job_id,)
            )
            row = cursor.fetchone()

            conn.commit()

            return row['retry_count'] if row else 0

    def delete_batch_job(self, job_id: str) -> bool:
        """バッチジョブを削除

        Args:
            job_id: Job ID

        Returns:
            True if deleted, False if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("DELETE FROM batch_jobs WHERE job_id = ?", (job_id,))
            deleted = cursor.rowcount > 0

            conn.commit()

            return deleted

    def get_batch_summary(self) -> Dict[str, Any]:
        """バッチジョブの統計サマリーを取得

        Returns:
            Summary statistics with counts per status
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT
                    COUNT(*) as total_jobs,
                    COALESCE(SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END), 0) as completed,
                    COALESCE(SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END), 0) as failed,
                    COALESCE(SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END), 0) as running,
                    COALESCE(SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END), 0) as pending,
                    COALESCE(SUM(CASE WHEN status = 'retrying' THEN 1 ELSE 0 END), 0) as retrying,
                    COALESCE(SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END), 0) as cancelled
                FROM batch_jobs
            ''')

            row = cursor.fetchone()
            return dict(row) if row else {
                'total_jobs': 0,
                'completed': 0,
                'failed': 0,
                'running': 0,
                'pending': 0,
                'retrying': 0,
                'cancelled': 0,
            }

    def save_config_change(self, key: str, value: Any, changed_by: str = "system"):
        """設定変更を保存"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO config_history (key, value, changed_at, changed_by)
                VALUES (?, ?, ?, ?)
            ''', (key, json.dumps(value, ensure_ascii=False), datetime.now(), changed_by))

            conn.commit()

    def get_config_history(self, key: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """設定変更履歴を取得"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM config_history"
            params = []

            if key:
                query += " WHERE key = ?"
                params.append(key)

            query += " ORDER BY changed_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            # JSON をパース
            result = []
            for row in rows:
                record = dict(row)
                record['value'] = json.loads(record['value'])
                result.append(record)

            return result

    def record_backup(self, backup_type: str, file_path: Path, checksum: Optional[str] = None) -> int:
        """バックアップを記録"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO backups (backup_type, file_path, created_at, size, checksum)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                backup_type,
                str(file_path),
                datetime.now(),
                file_path.stat().st_size if file_path.exists() else 0,
                checksum
            ))

            conn.commit()
            return cursor.lastrowid

    def get_backups(self, backup_type: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """バックアップ履歴を取得"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM backups"
            params = []

            if backup_type:
                query += " WHERE backup_type = ?"
                params.append(backup_type)

            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [dict(row) for row in rows]

    def cleanup_old_records(self, days: int = 90):
        """古いレコードを削除"""
        cutoff_date = datetime.now() - timedelta(days=days)

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 古い生成履歴を削除
            cursor.execute(
                "DELETE FROM generation_history WHERE created_at < ?",
                (cutoff_date,)
            )

            # 古い設定履歴を削除（最新10件は残す）
            cursor.execute('''
                DELETE FROM config_history
                WHERE id NOT IN (
                    SELECT id FROM config_history
                    ORDER BY changed_at DESC
                    LIMIT 10
                )
            ''')

            conn.commit()

            deleted_count = cursor.rowcount
            logger.info(f"Cleaned up {deleted_count} old database records")


class BackupManager:
    """バックアップマネージャー"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.backup_dir = settings.DATA_DIR / "backups"
        self.backup_dir.mkdir(exist_ok=True)

    def create_backup(self, backup_type: str, source_dirs: List[Path]) -> Path:
        """バックアップを作成"""
        import zipfile

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_{backup_type}_{timestamp}.zip"
        backup_path = self.backup_dir / backup_filename

        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for source_dir in source_dirs:
                if source_dir.exists():
                    for file_path in source_dir.rglob('*'):
                        if file_path.is_file():
                            # 相対パスで保存
                            arcname = file_path.relative_to(source_dir.parent)
                            zipf.write(file_path, arcname)

        # チェックサム計算（簡易）
        import hashlib
        checksum = hashlib.md5(backup_path.read_bytes()).hexdigest()

        # DB に記録
        self.db.record_backup(backup_type, backup_path, checksum)

        logger.info(f"Backup created: {backup_path}")
        return backup_path

    def create_full_backup(self) -> Path:
        """フルバックアップを作成"""
        source_dirs = [
            settings.VIDEOS_DIR,
            settings.AUDIO_DIR,
            settings.SLIDES_DIR,
            settings.SCRIPTS_DIR,
            settings.THUMBNAILS_DIR,
            settings.DATA_DIR / "database.db"  # DB ファイルも含む
        ]
        return self.create_backup("full", source_dirs)

    def create_config_backup(self) -> Path:
        """設定のみのバックアップ"""
        # 設定ファイルが存在する場合
        config_files = [
            Path("config/settings.py"),
            Path("config/.env") if Path("config/.env").exists() else None,
        ]
        config_files = [f for f in config_files if f and f.exists()]

        source_dirs = [Path("config")] if config_files else []
        return self.create_backup("config", source_dirs)

    def cleanup_old_backups(self, days: int = 30):
        """古いバックアップを削除"""
        cutoff_date = datetime.now() - timedelta(days=days)

        for backup_file in self.backup_dir.glob("*.zip"):
            if backup_file.stat().st_mtime < cutoff_date.timestamp():
                backup_file.unlink()
                logger.info(f"Deleted old backup: {backup_file}")


# グローバルインスタンス
db_manager = DatabaseManager()
backup_manager = BackupManager(db_manager)

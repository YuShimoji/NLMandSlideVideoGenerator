"""
データ永続化モジュール
生成履歴・設定・バックアップ機能
"""
import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from contextlib import contextmanager

from config.settings import settings

logger = logging.getLogger(__name__)


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

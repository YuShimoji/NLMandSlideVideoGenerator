"""
ProductionLine: 動画制作ラインの状態管理モデル (SP-053)

各制作ラインのPhase 0-7の進捗を追跡し、JSONで永続化する。
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class LineStatus(str, Enum):
    """制作ラインの状態"""
    DRAFT = "draft"              # 下書き (トピック入力のみ)
    SELECTING = "selecting"      # バッチ選定中 (AI評価待ち)
    STRUCTURING = "structuring"  # Phase 2-5 自動処理中
    PRODUCING = "producing"      # Phase 6 YMM4制作中
    REVIEWING = "reviewing"      # Phase 7 公開前レビュー中
    PUBLISHING = "publishing"    # YouTube公開処理中
    DONE = "done"                # 公開完了
    FAILED = "failed"            # エラーで停止
    CANCELLED = "cancelled"      # キャンセル


@dataclass
class ProductionLine:
    """1本の動画制作ラインを表すデータモデル"""

    line_id: str = ""
    topic: str = ""
    created_at: str = ""          # ISO format
    updated_at: str = ""          # ISO format
    status: str = "draft"         # LineStatus value
    current_phase: int = 0        # 0-7

    # Phase 0-1: NLM
    source_urls: list[str] = field(default_factory=list)
    source_texts: list[str] = field(default_factory=list)
    audio_path: str = ""
    transcript_path: str = ""

    # Phase 2-3: 構造化
    script_json_path: str = ""
    segment_count: int = 0
    estimated_duration: float = 0.0  # 秒
    speaker_names: list[str] = field(default_factory=list)

    # Phase 4-5: スライド+CSV
    slides_dir: str = ""
    images_dir: str = ""
    csv_path: str = ""
    metadata_path: str = ""
    image_count: int = 0

    # Phase 6: YMM4
    ymm4_project_path: str = ""
    mp4_path: str = ""

    # Phase 7: 公開
    thumbnail_path: str = ""
    youtube_url: str = ""
    youtube_video_id: str = ""

    # AI評価
    ai_score: float = 0.0        # 0-5
    ai_comment: str = ""
    go_decision: bool | None = None

    # メタ
    topic_dir: str = ""           # data/topics/{topic_id}/
    error_log: list[str] = field(default_factory=list)
    phase_timestamps: dict[str, str] = field(default_factory=dict)  # {"phase_0_start": "ISO", ...}

    @staticmethod
    def create(topic: str, base_dir: str = "data/topics") -> ProductionLine:
        """新規制作ラインを作成する"""
        now = datetime.now().isoformat()
        line_id = uuid.uuid4().hex[:12]
        topic_slug = _slugify(topic)[:40]
        topic_id = f"{datetime.now().strftime('%Y%m%d')}_{topic_slug}_{line_id[:6]}"
        topic_dir = str(Path(base_dir) / topic_id)

        return ProductionLine(
            line_id=line_id,
            topic=topic,
            created_at=now,
            updated_at=now,
            status=LineStatus.DRAFT.value,
            current_phase=0,
            topic_dir=topic_dir,
        )

    def advance_phase(self, phase: int) -> None:
        """フェーズを進める"""
        self.current_phase = phase
        now = datetime.now().isoformat()
        self.updated_at = now
        self.phase_timestamps[f"phase_{phase}_start"] = now

    def complete_phase(self, phase: int) -> None:
        """フェーズ完了を記録する"""
        now = datetime.now().isoformat()
        self.updated_at = now
        self.phase_timestamps[f"phase_{phase}_end"] = now

    def set_status(self, status: LineStatus) -> None:
        """ステータスを変更する"""
        self.status = status.value
        self.updated_at = datetime.now().isoformat()

    def add_error(self, message: str) -> None:
        """エラーを記録する"""
        timestamp = datetime.now().isoformat()
        self.error_log.append(f"[{timestamp}] {message}")
        self.updated_at = timestamp

    def to_dict(self) -> dict[str, Any]:
        """辞書に変換する"""
        return asdict(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> ProductionLine:
        """辞書から復元する"""
        known_fields = {f.name for f in ProductionLine.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return ProductionLine(**filtered)

    @property
    def display_status(self) -> str:
        """表示用ステータス文字列"""
        status_map = {
            "draft": "下書き",
            "selecting": "選定中",
            "structuring": "構造化中",
            "producing": "YMM4制作中",
            "reviewing": "レビュー中",
            "publishing": "公開処理中",
            "done": "完了",
            "failed": "エラー",
            "cancelled": "キャンセル",
        }
        return status_map.get(self.status, self.status)

    @property
    def phase_column(self) -> str:
        """プロダクションボードの列名"""
        if self.status in ("done", "cancelled", "failed"):
            return self.status
        if self.current_phase <= 1:
            return "nlm"
        if self.current_phase <= 5:
            return "structuring"
        if self.current_phase == 6:
            return "producing"
        return "publishing"


class ProductionLineStore:
    """ProductionLineのJSON永続化ストア"""

    def __init__(self, store_path: str | Path = "data/production_lines.json"):
        self._path = Path(store_path)
        self._lines: dict[str, ProductionLine] = {}
        self._load()

    def _load(self) -> None:
        """JSONファイルから読み込む"""
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                for item in data.get("lines", []):
                    line = ProductionLine.from_dict(item)
                    self._lines[line.line_id] = line
            except (json.JSONDecodeError, KeyError):
                self._lines = {}

    def save(self) -> None:
        """JSONファイルに書き出す"""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": 1,
            "updated_at": datetime.now().isoformat(),
            "lines": [line.to_dict() for line in self._lines.values()],
        }
        self._path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def add(self, line: ProductionLine) -> None:
        """ラインを追加して保存する"""
        self._lines[line.line_id] = line
        self.save()

    def get(self, line_id: str) -> ProductionLine | None:
        """IDでラインを取得する"""
        return self._lines.get(line_id)

    def update(self, line: ProductionLine) -> None:
        """ラインを更新して保存する"""
        line.updated_at = datetime.now().isoformat()
        self._lines[line.line_id] = line
        self.save()

    def delete(self, line_id: str) -> bool:
        """ラインを削除して保存する"""
        if line_id in self._lines:
            del self._lines[line_id]
            self.save()
            return True
        return False

    def list_all(self) -> list[ProductionLine]:
        """全ラインを作成日時降順で返す"""
        return sorted(
            self._lines.values(),
            key=lambda x: x.created_at,
            reverse=True,
        )

    def list_by_status(self, status: LineStatus) -> list[ProductionLine]:
        """ステータスで絞り込む"""
        return [l for l in self.list_all() if l.status == status.value]

    def list_by_column(self, column: str) -> list[ProductionLine]:
        """プロダクションボードの列で絞り込む"""
        return [l for l in self.list_all() if l.phase_column == column]

    def count_by_status(self) -> dict[str, int]:
        """ステータス別件数"""
        counts: dict[str, int] = {}
        for line in self._lines.values():
            counts[line.status] = counts.get(line.status, 0) + 1
        return counts


def _slugify(text: str) -> str:
    """トピック名をファイルシステム安全な文字列に変換する"""
    import re
    # 英数字・ひらがな・カタカナ・漢字以外をアンダースコアに
    slug = re.sub(r'[^\w\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', '_', text)
    slug = re.sub(r'_+', '_', slug).strip('_')
    return slug.lower() if slug else "untitled"

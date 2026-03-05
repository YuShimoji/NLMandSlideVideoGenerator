"""
リサーチ関連のデータモデル
"""
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any
from datetime import datetime
from .source_collector import SourceInfo

@dataclass
class ResearchPackage:
    """収集資料パッケージ"""
    package_id: str
    topic: str
    created_at: str
    sources: List[SourceInfo] = field(default_factory=list)
    summary: str = ""
    review_status: str = "pending"

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換 (JSON保存用)"""
        data = asdict(self)
        # SourceInfoは dataclass なので asdict で再帰的に変換される
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResearchPackage':
        """辞書形式から復元"""
        sources_data = data.pop('sources', [])
        sources = [SourceInfo(**s) for s in sources_data]
        return cls(sources=sources, **data)

@dataclass
class AlignmentReport:
    """台本と資料の整合性レポート"""
    report_id: str
    package_id: str
    analysis: List[Dict[str, Any]] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換 (JSON保存用)"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AlignmentReport':
        """辞書形式から復元"""
        return cls(**data)

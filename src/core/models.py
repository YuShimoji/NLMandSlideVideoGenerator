"""
データモデル
"""
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Any


@dataclass
class PipelineArtifacts:
    sources: List
    audio: Any  # AudioInfo
    transcript: Any  # TranscriptInfo
    slides: Any  # SlidesPackage
    video: Any  # VideoInfo
    upload: Optional[Any]  # UploadResult
    script: Optional[Dict[str, Any]] = None
    timeline_plan: Optional[Dict[str, Any]] = None
    assets: Optional[Dict[str, Any]] = None
    thumbnail_path: Optional[Path] = None
    metadata: Optional[Dict[str, Any]] = None
    publishing_result: Optional[Dict[str, Any]] = None

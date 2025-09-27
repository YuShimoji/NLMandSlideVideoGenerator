"""
コアインターフェイス定義
既存モジュール群（source/audio/transcript/slides/video/youtube/metadata）に対する疎結合なProtocolを提供
"""
from __future__ import annotations

from typing import Protocol, List, Optional, Union, Dict, Any
from pathlib import Path

# 既存のデータ型を再利用
from notebook_lm.source_collector import SourceInfo
from notebook_lm.audio_generator import AudioInfo
from notebook_lm.transcript_processor import TranscriptInfo
from slides.slide_generator import SlidesPackage
from video_editor.video_composer import VideoInfo
from youtube.uploader import UploadResult, UploadMetadata


class ISourceCollector(Protocol):
    async def collect_sources(self, topic: str, urls: Optional[List[str]] = None) -> List[SourceInfo]:
        ...


class IAudioGenerator(Protocol):
    async def generate_audio(self, sources: List[SourceInfo]) -> AudioInfo:
        ...


class ITranscriptProcessor(Protocol):
    async def process_audio(self, audio_info: AudioInfo) -> TranscriptInfo:
        ...


class ISlideGenerator(Protocol):
    async def generate_slides(self, transcript: TranscriptInfo, max_slides: int = 20) -> SlidesPackage:
        ...


class IVideoComposer(Protocol):
    async def compose_video(
        self,
        audio_file: AudioInfo,
        slides_file: SlidesPackage,
        transcript: TranscriptInfo,
        quality: str = "1080p"
    ) -> VideoInfo:
        ...


class IUploader(Protocol):
    async def authenticate(self) -> bool:
        ...

    async def upload_video(
        self,
        video: Union[Path, Any],
        metadata: Union[UploadMetadata, Dict[str, Any]],
        thumbnail_path: Optional[Path] = None,
    ) -> UploadResult:
        ...


class IMetadataGenerator(Protocol):
    async def generate_metadata(self, transcript: TranscriptInfo) -> Dict[str, Any]:
        ...

"""
コアインターフェイス定義
既存モジュール群（source/audio/transcript/slides/video/youtube/metadata）に対する疎結合なProtocolを提供
"""
from __future__ import annotations

from typing import Protocol, List, Optional, Union, Dict, Any, TYPE_CHECKING, runtime_checkable
from pathlib import Path

if TYPE_CHECKING:
    # 型チェック専用のインポート（実行時には評価しない）
    from notebook_lm.source_collector import SourceInfo
    from notebook_lm.audio_generator import AudioInfo
    from notebook_lm.transcript_processor import TranscriptInfo
    from slides.slide_generator import SlidesPackage
    from video_editor.video_composer import VideoInfo
    from youtube.uploader import UploadResult, UploadMetadata


@runtime_checkable
class IScriptProvider(Protocol):
    async def generate_script(
        self,
        topic: str,
        sources: List[SourceInfo],
        mode: str = "auto",
    ) -> Dict[str, Any]:
        """台本生成/取得。NotebookLM, Gemini, 手動入力などを抽象化"""


class IContentAdapter(Protocol):
    async def normalize_script(self, raw_script: Dict[str, Any]) -> Dict[str, Any]:
        """NotebookLM DeepDiveなど固有フォーマットを内部スキーマへ変換"""


@runtime_checkable
class IVoicePipeline(Protocol):
    async def synthesize(
        self,
        script: Dict[str, Any],
        preferred_provider: Optional[str] = None,
    ) -> AudioInfo:
        """TTS/収録音声を統一フォーマットで返す"""


class IAssetRegistry(Protocol):
    async def register_assets(
        self,
        artifacts: Dict[str, Any],
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """素材とメタデータを記録し再利用可能にする"""


class ITimelinePlanner(Protocol):
    async def build_plan(
        self,
        script: Dict[str, Any],
        audio: AudioInfo,
        user_preferences: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """セグメント・時間配分・エフェクト指示を計画"""


@runtime_checkable
class IEditingBackend(Protocol):
    async def render(
        self,
        timeline_plan: Dict[str, Any],
        audio: AudioInfo,
        slides: SlidesPackage,
        transcript: TranscriptInfo,
        quality: str = "1080p",
    ) -> VideoInfo:
        """MoviePy/YMM4など各レンダラーの共通インターフェイス"""


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


class IThumbnailGenerator(Protocol):
    async def generate_thumbnail(
        self,
        timeline_plan: Dict[str, Any],
        script: Dict[str, Any],
        assets: Dict[str, Any],
    ) -> Path:
        """サムネイルテンプレート適用を抽象化"""


@runtime_checkable
class IPlatformAdapter(Protocol):
    async def publish(
        self,
        package: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """YouTube/TikTok等、プラットフォーム固有ロジックを抽象化"""


class IPublishingQueue(Protocol):
    async def enqueue(
        self,
        package: Dict[str, Any],
        schedule: Optional[str] = None,
    ) -> str:
        """予約投稿や承認待ちキューに投入"""


class ThumbnailGeneratorProtocol(Protocol):
    """サムネイル自動生成プロトコル"""

    async def generate(
        self,
        video: "VideoInfo",
        script: Dict[str, Any],
        slides: "SlidesPackage",
        style: str = "modern"
    ) -> "ThumbnailInfo":
        """
        動画、スクリプト、スライド情報からサムネイルを自動生成

        Args:
            video: 動画情報
            script: スクリプトデータ
            slides: スライドパッケージ
            style: サムネイルスタイル ('modern', 'classic', 'gaming', 'educational')

        Returns:
            ThumbnailInfo: 生成されたサムネイル情報
        """


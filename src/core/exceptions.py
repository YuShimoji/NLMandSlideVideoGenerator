"""
パイプライン例外階層

PipelineError
├── ScriptGenerationError   - スクリプト生成失敗
├── AudioGenerationError    - 音声生成失敗
├── SlideGenerationError    - スライド生成失敗
├── VideoCompositionError   - 動画合成/レンダリング失敗
├── UploadError             - アップロード失敗
│   └── QuotaExceededError  - API quota超過
├── APIAuthenticationError  - API認証失敗
└── ConfigurationError      - 設定/環境の問題
"""
from typing import Optional


class PipelineError(Exception):
    """パイプラインエラー基底クラス"""

    def __init__(self, message: str, stage: Optional[str] = None, recoverable: bool = False, user_message: Optional[str] = None):
        super().__init__(message)
        self.stage = stage
        self.recoverable = recoverable
        self.user_message = user_message or self._generate_user_message(message, stage)

    def _generate_user_message(self, message: str, stage: Optional[str]) -> str:
        """ユーザーフレンドリーなエラーメッセージ生成"""
        base_messages = {
            "sources": "ソース収集でエラーが発生しました。URLやネットワーク接続を確認してください。",
            "script": "スクリプト生成でエラーが発生しました。トピックを確認してください。",
            "voice": "音声生成でエラーが発生しました。音声設定を確認してください。",
            "slides": "スライド生成でエラーが発生しました。Google Slides API を確認してください。",
            "video": "動画合成でエラーが発生しました。YMM4 の設定を確認してください。",
            "upload": "動画アップロードでエラーが発生しました。YouTube API を確認してください。",
        }

        if stage and stage in base_messages:
            return base_messages[stage]
        return "処理中にエラーが発生しました。しばらく経ってから再度お試しください。"


class ScriptGenerationError(PipelineError):
    """スクリプト生成に関するエラー"""
    def __init__(self, message: str, recoverable: bool = True, user_message: Optional[str] = None):
        super().__init__(message, stage="script", recoverable=recoverable, user_message=user_message)


class AudioGenerationError(PipelineError):
    """音声生成処理に関するエラー"""
    def __init__(self, message: str, recoverable: bool = True, user_message: Optional[str] = None):
        super().__init__(message, stage="voice", recoverable=recoverable, user_message=user_message)


class SlideGenerationError(PipelineError):
    """スライド生成に関するエラー"""
    def __init__(self, message: str, recoverable: bool = True, user_message: Optional[str] = None):
        super().__init__(message, stage="slides", recoverable=recoverable, user_message=user_message)


class VideoCompositionError(PipelineError):
    """動画合成/レンダリングに関するエラー"""
    def __init__(self, message: str, recoverable: bool = False, user_message: Optional[str] = None):
        super().__init__(message, stage="video", recoverable=recoverable, user_message=user_message)


class UploadError(PipelineError):
    """アップロード処理に関するエラー"""
    def __init__(self, message: str, recoverable: bool = True, user_message: Optional[str] = None):
        super().__init__(message, stage="upload", recoverable=recoverable, user_message=user_message)


class QuotaExceededError(UploadError):
    """API quota超過エラー"""
    def __init__(self, message: str, user_message: Optional[str] = None):
        super().__init__(
            message,
            recoverable=False,
            user_message=user_message or "APIの利用制限に達しました。しばらく時間をおいて再度お試しください。",
        )


class APIAuthenticationError(PipelineError):
    """API認証に関するエラー"""
    def __init__(self, message: str, service: str = "", user_message: Optional[str] = None):
        self.service = service
        super().__init__(
            message,
            stage="auth",
            recoverable=False,
            user_message=user_message or f"{service} API の認証に失敗しました。APIキーを確認してください。",
        )


class ConfigurationError(PipelineError):
    """設定/環境の問題"""
    def __init__(self, message: str, user_message: Optional[str] = None):
        super().__init__(
            message,
            stage="config",
            recoverable=False,
            user_message=user_message or "設定に問題があります。設定ファイルを確認してください。",
        )

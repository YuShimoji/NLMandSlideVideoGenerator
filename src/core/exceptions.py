"""
パイプライン例外
"""
class PipelineError(Exception):
    """パイプラインエラー"""

    def __init__(self, message: str, stage: str = None, recoverable: bool = False, user_message: str = None):
        super().__init__(message)
        self.stage = stage
        self.recoverable = recoverable
        self.user_message = user_message or self._generate_user_message(message, stage)

    def _generate_user_message(self, message: str, stage: str) -> str:
        """ユーザーフレンドリーなエラーメッセージ生成"""
        base_messages = {
            "script": "スクリプト生成でエラーが発生しました。トピックを確認してください。",
            "voice": "音声生成でエラーが発生しました。TTS 設定を確認してください。",
            "slides": "スライド生成でエラーが発生しました。Google Slides API を確認してください。",
            "video": "動画合成でエラーが発生しました。MoviePy の設定を確認してください。",
            "upload": "動画アップロードでエラーが発生しました。YouTube API を確認してください。",
        }

        if stage and stage in base_messages:
            return base_messages[stage]
        else:
            return "処理中にエラーが発生しました。しばらく経ってから再度お試しください。"

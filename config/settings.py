"""
システム設定ファイル
"""
from pathlib import Path
from typing import Dict, Any
import os

# プロジェクトルートディレクトリ
PROJECT_ROOT = Path(__file__).parent.parent

class Settings:
    """アプリケーション設定"""
    
    def __init__(self):
        # 基本設定
        self.APP_NAME = "NLMandSlideVideoGenerator"
        self.VERSION = "1.0.0"
        self.DEBUG = os.getenv("DEBUG", "false").lower() == "true"
        
        # API設定
        self.YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
        self.YOUTUBE_CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID", "")
        self.YOUTUBE_CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET", "")
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
        
        # ファイルパス設定
        self.DATA_DIR = PROJECT_ROOT / "data"
        self.AUDIO_DIR = self.DATA_DIR / "audio"
        self.SLIDES_DIR = self.DATA_DIR / "slides"
        self.SLIDES_IMAGES_DIR = self.SLIDES_DIR / "images"
        self.VIDEOS_DIR = self.DATA_DIR / "videos"
        self.TRANSCRIPTS_DIR = self.DATA_DIR / "transcripts"
        self.SCRIPTS_DIR = self.DATA_DIR / "scripts"
        self.TEMPLATES_DIR = self.DATA_DIR / "templates"
        self.THUMBNAILS_DIR = self.DATA_DIR / "thumbnails"
        
        # ログ設定
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        self.LOG_FILE = PROJECT_ROOT / "logs" / "app.log"
        
        # 動画生成設定
        self.VIDEO_SETTINGS = {
            "resolution": (1920, 1080),
            "fps": 30,
            "video_codec": "libx264",
            "audio_codec": "aac",
            "crf": 23,
            "audio_bitrate": "128k"
        }
        
        # 字幕設定
        self.SUBTITLE_SETTINGS = {
            "font_family": "Noto Sans CJK JP",
            "font_size": 48,
            "font_color": "white",
            "background_color": "black",
            "background_opacity": 0.7,
            "position": "bottom"
        }
        
        # エフェクト設定
        self.EFFECT_SETTINGS = {
            "zoom": {
                "start_scale": 1.0,
                "end_scale": 1.1,
                "easing": "ease_in_out"
            },
            "pan": {
                "max_horizontal": 0.05,
                "max_vertical": 0.03,
                "duration_factor": 0.8
            },
            "fade": {
                "duration": 0.5,
                "type": "cross_fade"
            }
        }
        
        # NotebookLM設定
        self.NOTEBOOK_LM_SETTINGS = {
            "max_sources": 10,
            "audio_quality_threshold": 0.95,
            "transcript_accuracy_threshold": 0.98,
            "max_audio_duration": 1800  # 30分
        }
        
        # Google Slides設定
        self.SLIDES_SETTINGS = {
            "max_chars_per_slide": 200,
            "max_slides_per_batch": 20,
            "theme": "business",
            "min_font_size": 24,
            "show_speaker_on_placeholder": False,
            "auto_split_long_lines": True,
            "long_line_char_threshold": 120,
            "long_line_target_chars_per_subslide": 60,
            "long_line_max_subslides": 3,
            "min_subslide_duration": 0.5,
        }
        
        # YouTube設定
        self.YOUTUBE_SETTINGS = {
            "privacy_status": "private",
            "category_id": "27",  # 教育カテゴリ
            "default_language": "ja",
            "default_audio_language": "ja",
            "max_title_length": 100,
            "max_description_length": 5000,
            "max_tags_length": 500
        }

        # Google OAuth 設定
        self.GOOGLE_SCOPES = [
            "https://www.googleapis.com/auth/presentations",
            "https://www.googleapis.com/auth/drive"
        ]
        self.GOOGLE_CLIENT_SECRETS_FILE = Path(os.getenv(
            "GOOGLE_CLIENT_SECRETS_FILE",
            str(PROJECT_ROOT / "google_client_secret.json")
        ))
        self.GOOGLE_OAUTH_TOKEN_FILE = Path(os.getenv(
            "GOOGLE_OAUTH_TOKEN_FILE",
            str(PROJECT_ROOT / "token.json")
        ))

        # TTS 設定
        self.TTS_SETTINGS = {
            "provider": os.getenv("TTS_PROVIDER", "none"),  # none | openai | elevenlabs | azure
            "openai": {
                "model": os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts"),
                "voice": os.getenv("OPENAI_TTS_VOICE", "alloy"),
                "format": os.getenv("OPENAI_TTS_FORMAT", "mp3"),
            },
            "elevenlabs": {
                "api_key": os.getenv("ELEVENLABS_API_KEY", ""),
                "voice_id": os.getenv("ELEVENLABS_VOICE_ID", ""),
                "model": os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2"),
            },
            "azure": {
                "key": os.getenv("AZURE_SPEECH_KEY", ""),
                "region": os.getenv("AZURE_SPEECH_REGION", ""),
                "voice": os.getenv("AZURE_SPEECH_VOICE", "ja-JP-NanamiNeural"),
                "format": os.getenv("AZURE_SPEECH_FORMAT", "audio-48khz-192kbitrate-mono-mp3"),
            },
            "google_cloud": {
                "api_key": os.getenv("GOOGLE_CLOUD_TTS_KEY", ""),
                "voice": os.getenv("GOOGLE_CLOUD_TTS_VOICE", "ja-JP-Neural2-B"),
                "speaking_rate": float(os.getenv("GOOGLE_CLOUD_TTS_RATE", "1.0")),
            },
        }

        self.PIPELINE_STAGE_MODES = {
            "stage1": os.getenv("PIPELINE_STAGE1_MODE", "auto"),
            "stage2": os.getenv("PIPELINE_STAGE2_MODE", "auto"),
            "stage3": os.getenv("PIPELINE_STAGE3_MODE", "auto"),
        }

        self.PIPELINE_COMPONENTS = {
            "script_provider": os.getenv("SCRIPT_PROVIDER", "legacy"),
            "voice_pipeline": os.getenv("VOICE_PIPELINE", "legacy"),
            "editing_backend": os.getenv("EDITING_BACKEND", "moviepy"),
            "platform_adapter": os.getenv("PLATFORM_ADAPTER", "youtube"),
            "thumbnail_generator": os.getenv("THUMBNAIL_GENERATOR", "ai"),
        }

        self.YMM4_SETTINGS = {
            "project_template": os.getenv("YMM4_TEMPLATE_PATH", str(self.TEMPLATES_DIR / "ymm4" / "base_project.y4mmp")),
            "auto_hotkey_script": os.getenv("YMM4_AHK_SCRIPT", str(self.TEMPLATES_DIR / "scripts" / "ymm4_export.ahk")),
            "workspace_dir": os.getenv("YMM4_WORKSPACE_DIR", str(self.DATA_DIR / "ymm4")),
        }

        self.PUBLISHING_SETTINGS = {
            "default_platform": os.getenv("PUBLISHING_DEFAULT_PLATFORM", "youtube"),
            "schedule_timezone": os.getenv("PUBLISHING_TIMEZONE", "Asia/Tokyo"),
            "fallback_upload": os.getenv("PUBLISHING_FALLBACK", "legacy"),
        }

        # リトライ設定
        self.RETRY_SETTINGS = {
            "max_retries": 3,
            "backoff_factor": 2,
            "timeout": 30
        }

# グローバル設定インスタンス
settings = Settings()

# ディレクトリ作成
def create_directories():
    """必要なディレクトリを作成"""
    directories = [
        settings.DATA_DIR,
        settings.AUDIO_DIR,
        settings.SLIDES_DIR,
        settings.SLIDES_IMAGES_DIR,
        settings.VIDEOS_DIR,
        settings.TRANSCRIPTS_DIR,
        settings.SCRIPTS_DIR,
        settings.TEMPLATES_DIR,
        settings.THUMBNAILS_DIR,
        settings.LOG_FILE.parent
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

if __name__ == "__main__":
    create_directories()
    print(f"設定完了: {settings.APP_NAME} v{settings.VERSION}")

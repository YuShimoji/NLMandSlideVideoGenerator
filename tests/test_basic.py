"""
基本テストファイル
プロジェクトの基本機能をテスト
"""
import pytest
from pathlib import Path
import sys

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from config.settings import settings, create_directories

class TestBasicSetup:
    """基本セットアップのテスト"""
    
    def test_settings_loading(self):
        """設定の読み込みテスト"""
        assert settings.APP_NAME == "NLMandSlideVideoGenerator"
        assert settings.VERSION == "1.0.0"
        assert isinstance(settings.VIDEO_SETTINGS, dict)
        assert isinstance(settings.SUBTITLE_SETTINGS, dict)
    
    def test_directory_creation(self):
        """ディレクトリ作成テスト"""
        create_directories()
        
        # 必要なディレクトリが作成されているか確認
        assert settings.DATA_DIR.exists()
        assert settings.AUDIO_DIR.exists()
        assert settings.SLIDES_DIR.exists()
        assert settings.VIDEOS_DIR.exists()
        assert settings.TRANSCRIPTS_DIR.exists()
    
    def test_video_settings(self):
        """動画設定のテスト"""
        video_settings = settings.VIDEO_SETTINGS
        
        assert "resolution" in video_settings
        assert "fps" in video_settings
        assert "video_codec" in video_settings
        assert video_settings["resolution"] == (1920, 1080)
        assert video_settings["fps"] == 30

class TestModuleImports:
    """モジュールインポートのテスト"""
    
    def test_notebook_lm_imports(self):
        """NotebookLMモジュールのインポートテスト"""
        from notebook_lm import SourceCollector, AudioGenerator, TranscriptProcessor
        
        assert SourceCollector is not None
        assert AudioGenerator is not None
        assert TranscriptProcessor is not None
    
    def test_slides_imports(self):
        """スライドモジュールのインポートテスト"""
        from slides import SlideGenerator, ContentSplitter
        
        assert SlideGenerator is not None
        assert ContentSplitter is not None
    
    def test_video_editor_imports(self):
        """動画編集モジュールのインポートテスト"""
        from video_editor import SubtitleGenerator, EffectProcessor, VideoComposer
        
        assert SubtitleGenerator is not None
        assert EffectProcessor is not None
        assert VideoComposer is not None
    
    def test_youtube_imports(self):
        """YouTubeモジュールのインポートテスト"""
        from youtube import YouTubeUploader, MetadataGenerator
        
        assert YouTubeUploader is not None
        assert MetadataGenerator is not None

class TestDataStructures:
    """データ構造のテスト"""
    
    def test_source_info_creation(self):
        """SourceInfoの作成テスト"""
        from notebook_lm.source_collector import SourceInfo
        
        source = SourceInfo(
            url="https://example.com",
            title="テストタイトル",
            content_preview="テスト内容",
            relevance_score=0.8,
            reliability_score=0.9,
            source_type="news"
        )
        
        assert source.url == "https://example.com"
        assert source.title == "テストタイトル"
        assert source.relevance_score == 0.8
    
    def test_transcript_segment_creation(self):
        """TranscriptSegmentの作成テスト"""
        from notebook_lm.transcript_processor import TranscriptSegment
        
        segment = TranscriptSegment(
            id=1,
            start_time=0.0,
            end_time=10.0,
            speaker="ナレーター",
            text="テストテキスト",
            key_points=["ポイント1", "ポイント2"],
            slide_suggestion="スライド提案",
            confidence_score=0.95
        )
        
        assert segment.id == 1
        assert segment.speaker == "ナレーター"
        assert len(segment.key_points) == 2

if __name__ == "__main__":
    pytest.main([__file__])

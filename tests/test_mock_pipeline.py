#!/usr/bin/env python3
"""
モックテスト - 全体パイプラインのテスト
実際のAPI連携なしで動作確認を行う
"""
import sys
import os
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

# プロジェクトルートをパスに追加（絶対パスで解決）
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))  # config/ 用
sys.path.insert(0, str(project_root / "src"))  # notebook_lm/, slides/ 等用
os.chdir(project_root)

from config.settings import settings, create_directories
from notebook_lm.source_collector import SourceCollector, SourceInfo
from notebook_lm.audio_generator import AudioGenerator, AudioInfo
from notebook_lm.transcript_processor import TranscriptProcessor, TranscriptInfo, TranscriptSegment
from slides.slide_generator import SlideGenerator, SlidesPackage, SlideInfo
from video_editor.video_composer import VideoComposer, VideoInfo
from youtube.uploader import YouTubeUploader, UploadResult
from youtube.metadata_generator import MetadataGenerator, VideoMetadata

class MockTestRunner:
    """モックテスト実行クラス"""
    
    def __init__(self):
        self.test_topic = "AI技術の最新動向"
        self.test_urls = [
            "https://example.com/ai-news-1",
            "https://example.com/ai-news-2"
        ]
        
    async def run_all_tests(self):
        """全てのモックテストを実行"""
        print("=== NLMandSlideVideoGenerator モックテスト開始 ===")
        print()
        
        # ディレクトリ作成
        create_directories()
        
        tests = [
            ("ソース収集テスト", self.test_source_collection),
            ("音声生成テスト", self.test_audio_generation),
            ("文字起こしテスト", self.test_transcript_processing),
            ("スライド生成テスト", self.test_slide_generation),
            ("動画合成テスト", self.test_video_composition),
            ("メタデータ生成テスト", self.test_metadata_generation),
            ("YouTube アップロードテスト", self.test_youtube_upload),
            ("統合パイプラインテスト", self.test_full_pipeline)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            print(f"[テスト] {test_name}")
            try:
                result = await test_func()
                if result:
                    print("✓ 成功")
                    passed += 1
                else:
                    print("✗ 失敗")
            except Exception as e:
                print(f"✗ エラー: {e}")
            print()
        
        print(f"=== テスト結果: {passed}/{total} 成功 ===")
        return passed == total
    
    async def test_source_collection(self):
        """ソース収集のモックテスト"""
        collector = SourceCollector()
        
        # モックソース情報を作成
        mock_sources = [
            SourceInfo(
                url="https://example.com/ai-news-1",
                title="AI技術の最新動向について",
                content_preview="人工知能技術の最新の発展について解説します...",
                relevance_score=0.9,
                reliability_score=0.8,
                source_type="news"
            ),
            SourceInfo(
                url="https://example.com/ai-news-2", 
                title="機械学習の新しいアプローチ",
                content_preview="機械学習における革新的な手法について...",
                relevance_score=0.85,
                reliability_score=0.9,
                source_type="article"
            )
        ]
        
        # モック関数でcollect_sourcesをパッチ
        with patch.object(collector, 'collect_sources', new_callable=AsyncMock) as mock_collect:
            mock_collect.return_value = mock_sources
            
            sources = await collector.collect_sources(self.test_topic, self.test_urls)
            
            assert len(sources) == 2
            assert sources[0].title == "AI技術の最新動向について"
            print(f"  収集されたソース数: {len(sources)}")
            
        return True
    
    async def test_audio_generation(self):
        """音声生成のモックテスト"""
        generator = AudioGenerator()
        
        # モック音声情報
        mock_audio = AudioInfo(
            file_path=settings.AUDIO_DIR / "test_audio.mp3",
            duration=180.5,
            quality_score=0.95,
            sample_rate=44100,
            file_size=2048000,
            language="ja"
        )
        
        # モックソース情報
        mock_sources = [
            SourceInfo(
                url="https://example.com/test",
                title="テストソース",
                content_preview="テスト内容",
                relevance_score=0.9,
                reliability_score=0.8,
                source_type="news"
            )
        ]
        
        with patch.object(generator, 'generate_audio', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_audio
            
            audio_info = await generator.generate_audio(mock_sources, self.test_topic)
            
            assert audio_info.duration > 0
            assert audio_info.quality_score > 0.9
            print(f"  音声時間: {audio_info.duration}秒")
            print(f"  品質スコア: {audio_info.quality_score}")
            
        return True
    
    async def test_transcript_processing(self):
        """文字起こし処理のモックテスト"""
        processor = TranscriptProcessor()
        
        # モック音声情報
        mock_audio = AudioInfo(
            file_path=settings.AUDIO_DIR / "test_audio.mp3",
            duration=180.5,
            quality_score=0.95,
            sample_rate=44100,
            file_size=2048000,
            language="ja"
        )
        
        # モック台本情報
        from datetime import datetime
        mock_transcript = TranscriptInfo(
            title="AI技術の最新動向",
            total_duration=180.5,
            segments=[
                TranscriptSegment(
                    id=1,
                    start_time=0.0,
                    end_time=30.0,
                    speaker="ナレーター1",
                    text="今日はAI技術の最新動向について解説します。",
                    key_points=["AI技術", "最新動向"],
                    slide_suggestion="AI技術の概要",
                    confidence_score=0.98
                ),
                TranscriptSegment(
                    id=2,
                    start_time=30.0,
                    end_time=60.0,
                    speaker="ナレーター2",
                    text="特に機械学習の分野で注目される技術について見ていきましょう。",
                    key_points=["機械学習", "注目技術"],
                    slide_suggestion="機械学習の技術",
                    confidence_score=0.96
                )
            ],
            accuracy_score=0.97,
            created_at=datetime.now(),
            source_audio_path=str(mock_audio.file_path)
        )
        
        with patch.object(processor, 'process_transcript', new_callable=AsyncMock) as mock_process:
            mock_process.return_value = mock_transcript
            
            transcript = await processor.process_transcript(mock_audio)
            
            assert len(transcript.segments) == 2
            assert transcript.accuracy_score > 0.95
            print(f"  セグメント数: {len(transcript.segments)}")
            print(f"  精度スコア: {transcript.accuracy_score}")
            
        return True
    
    async def test_slide_generation(self):
        """スライド生成のモックテスト"""
        generator = SlideGenerator()
        
        # モック台本情報
        from datetime import datetime
        mock_transcript = TranscriptInfo(
            title="AI技術の最新動向",
            total_duration=180.5,
            segments=[
                TranscriptSegment(
                    id=1,
                    start_time=0.0,
                    end_time=90.0,
                    speaker="ナレーター1",
                    text="今日はAI技術の最新動向について解説します。",
                    key_points=["AI技術"],
                    slide_suggestion="AI技術の概要",
                    confidence_score=0.98
                )
            ],
            accuracy_score=0.97,
            created_at=datetime.now(),
            source_audio_path=""
        )
        
        # モックスライドパッケージ
        mock_slides = SlidesPackage(
            file_path=settings.SLIDES_DIR / "test_slides.pptx",
            slides=[
                SlideInfo(
                    slide_id=1,
                    title="AI技術の最新動向",
                    content="人工知能技術の発展について",
                    layout="title_slide",
                    duration=30.0
                ),
                SlideInfo(
                    slide_id=2,
                    title="機械学習の進歩",
                    content="深層学習とその応用",
                    layout="content_slide",
                    duration=60.0
                )
            ],
            total_slides=2,
            theme="business",
            created_at=None
        )
        
        with patch.object(generator, 'generate_slides', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_slides
            
            slides = await generator.generate_slides(mock_transcript, max_slides=10)
            
            assert len(slides.slides) == 2
            assert slides.total_slides == 2
            print(f"  生成されたスライド数: {slides.total_slides}")
            
        return True
    
    async def test_video_composition(self):
        """動画合成のモックテスト"""
        composer = VideoComposer()
        
        # モック入力データ
        mock_audio = AudioInfo(
            file_path=settings.AUDIO_DIR / "test_audio.mp3",
            duration=180.5,
            quality_score=0.95,
            sample_rate=44100,
            file_size=2048000,
            language="ja"
        )
        
        mock_slides = SlidesPackage(
            file_path=settings.SLIDES_DIR / "test_slides.pptx",
            slides=[],
            total_slides=2,
            theme="business",
            created_at=None
        )
        
        from datetime import datetime as dt_video
        mock_transcript = TranscriptInfo(
            title="AI技術の最新動向",
            total_duration=180.5,
            segments=[],
            accuracy_score=0.97,
            created_at=dt_video.now(),
            source_audio_path=str(mock_audio.file_path)
        )
        
        # モック動画情報
        mock_video = VideoInfo(
            file_path=settings.VIDEOS_DIR / "test_video.mp4",
            duration=180.5,
            resolution=(1920, 1080),
            fps=30,
            file_size=50000000,
            has_subtitles=True,
            has_effects=True,
            created_at=None
        )
        
        with patch.object(composer, 'compose_video', new_callable=AsyncMock) as mock_compose:
            mock_compose.return_value = mock_video
            
            video = await composer.compose_video(mock_audio, mock_slides, mock_transcript)
            
            assert video.duration > 0
            assert video.resolution == (1920, 1080)
            print(f"  動画時間: {video.duration}秒")
            print(f"  解像度: {video.resolution}")
            
        return True
    
    async def test_metadata_generation(self):
        """メタデータ生成のモックテスト"""
        generator = MetadataGenerator()
        
        # モック台本情報
        from datetime import datetime as dt_meta
        mock_transcript = TranscriptInfo(
            title="AI技術の最新動向",
            total_duration=180.5,
            segments=[],
            accuracy_score=0.97,
            created_at=dt_meta.now(),
            source_audio_path=""
        )
        
        # モックメタデータ
        mock_metadata = VideoMetadata(
            title="AI技術の最新動向 - 2024年版解説",
            description="人工知能技術の最新動向について詳しく解説します。機械学習、深層学習の最新技術を紹介。",
            tags=["AI", "人工知能", "機械学習", "技術解説", "最新動向"],
            category_id="27",
            language="ja",
            privacy_status="private"
        )
        
        with patch.object(generator, 'generate_metadata', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_metadata
            
            metadata = await generator.generate_metadata(mock_transcript, self.test_topic)
            
            assert len(metadata.title) > 0
            assert len(metadata.tags) > 0
            print(f"  タイトル: {metadata.title}")
            print(f"  タグ数: {len(metadata.tags)}")
            
        return True
    
    async def test_youtube_upload(self):
        """YouTube アップロードのモックテスト"""
        uploader = YouTubeUploader()
        
        # モック動画情報
        mock_video = VideoInfo(
            file_path=settings.VIDEOS_DIR / "test_video.mp4",
            duration=180.5,
            resolution=(1920, 1080),
            fps=30,
            file_size=50000000,
            has_subtitles=True,
            has_effects=True,
            created_at=None
        )
        
        # モックメタデータ
        mock_metadata = VideoMetadata(
            title="AI技術の最新動向 - 2024年版解説",
            description="人工知能技術の最新動向について詳しく解説します。",
            tags=["AI", "人工知能", "機械学習"],
            category_id="27",
            language="ja",
            privacy_status="private"
        )
        
        # モックアップロード結果
        mock_result = UploadResult(
            video_id="test_video_123",
            video_url="https://www.youtube.com/watch?v=test_video_123",
            upload_status="success",
            processing_status="processing",
            privacy_status="private",
            uploaded_at=None
        )
        
        with patch.object(uploader, 'upload_video', new_callable=AsyncMock) as mock_upload:
            mock_upload.return_value = mock_result
            
            result = await uploader.upload_video(mock_video, mock_metadata)
            
            assert result.upload_status == "success"
            assert "youtube.com" in result.video_url
            print(f"  動画ID: {result.video_id}")
            print(f"  アップロード状況: {result.upload_status}")
            
        return True
    
    async def test_full_pipeline(self):
        """統合パイプラインのモックテスト"""
        from main import VideoGenerationPipeline
        
        pipeline = VideoGenerationPipeline()
        
        # 各コンポーネントをモック化
        with patch.object(pipeline.source_collector, 'collect_sources', new_callable=AsyncMock) as mock_sources, \
             patch.object(pipeline.audio_generator, 'generate_audio', new_callable=AsyncMock) as mock_audio, \
             patch.object(pipeline.transcript_processor, 'process_transcript', new_callable=AsyncMock) as mock_transcript, \
             patch.object(pipeline.slide_generator, 'generate_slides', new_callable=AsyncMock) as mock_slides, \
             patch.object(pipeline.video_composer, 'compose_video', new_callable=AsyncMock) as mock_video, \
             patch.object(pipeline.youtube_uploader, 'upload_video', new_callable=AsyncMock) as mock_upload:
            
            # モックレスポンスを設定
            mock_sources.return_value = []
            mock_audio.return_value = AudioInfo(
                file_path=Path("test.mp3"), duration=180, quality_score=0.95,
                sample_rate=44100, file_size=1000000, language="ja"
            )
            from datetime import datetime as dt_full
            mock_transcript.return_value = TranscriptInfo(
                title="テスト", total_duration=180, segments=[], 
                accuracy_score=0.95, created_at=dt_full.now(), source_audio_path=""
            )
            mock_slides.return_value = SlidesPackage(
                file_path=Path("test.pptx"), slides=[], total_slides=5,
                theme="business", created_at=None
            )
            mock_video.return_value = VideoInfo(
                file_path=Path("test.mp4"), duration=180, resolution=(1920, 1080),
                fps=30, file_size=50000000, has_subtitles=True, has_effects=True, created_at=None
            )
            mock_upload.return_value = UploadResult(
                video_id="test123", video_url="https://youtube.com/watch?v=test123",
                upload_status="success", processing_status="processing", 
                privacy_status="private", uploaded_at=None
            )
            
            # パイプライン実行
            result = await pipeline.generate_video(
                topic=self.test_topic,
                urls=self.test_urls,
                max_slides=10
            )
            
            assert "youtube.com" in result
            print(f"  最終結果URL: {result}")
            
        return True

async def main():
    """メインテスト実行"""
    runner = MockTestRunner()
    success = await runner.run_all_tests()
    
    if success:
        print("✓ 全てのモックテストが成功しました")
        return 0
    else:
        print("✗ 一部のモックテストが失敗しました")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))

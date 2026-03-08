"""
デモ用モックデータ
"""
from datetime import datetime
from notebook_lm.source_collector import SourceInfo
from youtube.uploader import UploadResult
from youtube.metadata_generator import VideoMetadata


def get_mock_sources():
    """モックソースデータ"""
    return [
        SourceInfo(
            url="https://example.com/ai-trends-2024",
            title="2024年AI技術の最新動向",
            content_preview="人工知能技術は2024年に大きな進歩を遂げています。特に生成AIの分野では...",
            relevance_score=0.95,
            reliability_score=0.88,
            source_type="news"
        ),
        SourceInfo(
            url="https://example.com/machine-learning-advances",
            title="機械学習の革新的アプローチ",
            content_preview="深層学習とトランスフォーマーアーキテクチャの新しい応用について...",
            relevance_score=0.92,
            reliability_score=0.85,
            source_type="article"
        ),
        SourceInfo(
            url="https://example.com/ai-industry-report",
            title="AI業界レポート2024",
            content_preview="AI技術の産業応用が急速に拡大しており、特に自動化分野での活用が...",
            relevance_score=0.89,
            reliability_score=0.90,
            source_type="news"
        )
    ]


def get_mock_transcript():
    """モック文字起こしデータ"""
    from notebook_lm.transcript_processor import TranscriptInfo, TranscriptSegment

    return TranscriptInfo(
        title="AI技術の最新動向",
        duration=300.0,
        language="ja",
        segments=[
            TranscriptSegment(
                start_time=0.0,
                end_time=10.0,
                content="AI技術の進歩は目覚ましいものがあります。",
                confidence=0.95
            ),
            TranscriptSegment(
                start_time=10.0,
                end_time=20.0,
                content="特に生成AIの分野で大きな革新が見られます。",
                confidence=0.92
            ),
            TranscriptSegment(
                start_time=20.0,
                end_time=30.0,
                content="今後もさらなる発展が期待されます。",
                confidence=0.88
            )
        ]
    )


def get_mock_audio_info():
    """モック音声情報"""
    from notebook_lm.audio_generator import AudioInfo
    from pathlib import Path

    return AudioInfo(
        file_path=Path("data/audio/demo_audio.mp3"),
        duration=300.0,
        quality_score=0.9,
        sample_rate=44100,
        file_size=5000000,
        language="ja",
        channels=2
    )


def get_mock_slides_package():
    """モックスライドパッケージ"""
    from slides.slide_generator import SlidesPackage
    from pathlib import Path

    return SlidesPackage(
        presentation_id="demo_presentation_id",
        slides_url="https://docs.google.com/presentation/d/demo",
        total_slides=5,
        slide_ids=["slide1", "slide2", "slide3", "slide4", "slide5"],
        thumbnail_urls=["url1", "url2", "url3", "url4", "url5"],
        local_path=Path("data/slides/demo_slides.pdf")
    )


def get_mock_video_info():
    """モック動画情報"""
    from video_editor.models import VideoInfo
    from pathlib import Path

    return VideoInfo(
        file_path=Path("data/videos/demo_video.mp4"),
        duration=300.0,
        resolution=(1920, 1080),
        file_size=100000000,
        quality="1080p",
        fps=30.0
    )


def get_mock_metadata():
    """モックメタデータ"""
    return VideoMetadata(
        title="AI技術の最新動向 - デモンストレーション",
        description="""AI技術の最新動向について解説する動画です。

この動画では以下のトピックをカバーしています：

• 生成AIの最新技術
• 機械学習の効率化手法
• 産業界での実用例
• 今後の展望

📚 参考資料:
• AI業界レポート2024
• 機械学習技術動向調査
• 産業応用事例集

#AI #人工知能 #機械学習 #技術解説 #2024年""",
        tags=["AI", "人工知能", "機械学習", "技術解説", "最新動向", "2024年", "生成AI", "産業応用"],
        category_id="27",  # 教育
        language="ja",
        privacy_status="private"
    )


def get_mock_upload_result():
    """モックアップロード結果"""
    return UploadResult(
        video_id="dQw4w9WgXcQ_demo",
        video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ_demo",
        upload_status="success",
        processing_status="processing",
        privacy_status="private",
        uploaded_at=datetime.now()
    )

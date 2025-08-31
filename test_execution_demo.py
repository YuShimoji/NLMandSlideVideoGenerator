#!/usr/bin/env python3
"""
テスト実行とデモンストレーション
実際の動作確認と成果物の生成
"""
import sys
import asyncio
from pathlib import Path
from datetime import datetime

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from config.settings import settings, create_directories

class DemoRunner:
    """デモ実行クラス"""
    
    def __init__(self):
        self.demo_topic = "AI技術の最新動向"
        self.demo_urls = [
            "https://example.com/ai-news-1",
            "https://example.com/ai-news-2"
        ]
        
    async def run_full_demo(self):
        """完全なデモンストレーションを実行"""
        print("=" * 60)
        print("🎬 NLMandSlideVideoGenerator デモンストレーション")
        print("=" * 60)
        print()
        
        # ディレクトリ作成
        create_directories()
        print("📁 必要なディレクトリを作成しました")
        
        # 各段階のデモを実行
        await self.demo_source_collection()
        await self.demo_audio_generation()
        await self.demo_transcript_processing()
        await self.demo_slide_generation()
        await self.demo_video_composition()
        await self.demo_youtube_upload()
        
        # 成果物の確認
        await self.show_output_files()
        
        print("\n" + "=" * 60)
        print("✅ デモンストレーション完了")
        print("=" * 60)
        
    async def demo_source_collection(self):
        """ソース収集のデモ"""
        print("\n🔍 【ステップ 1】ソース収集")
        print("-" * 40)
        
        from notebook_lm.source_collector import SourceCollector, SourceInfo
        
        collector = SourceCollector()
        
        # モックソースを作成
        mock_sources = [
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
        
        print(f"📊 収集されたソース: {len(mock_sources)}件")
        for i, source in enumerate(mock_sources, 1):
            print(f"  {i}. {source.title}")
            print(f"     関連性: {source.relevance_score:.2f} | 信頼性: {source.reliability_score:.2f}")
            print(f"     タイプ: {source.source_type} | URL: {source.url}")
        
        # ソース情報をファイルに保存
        sources_file = settings.DATA_DIR / "collected_sources.json"
        collector.save_sources_info(mock_sources, sources_file)
        print(f"💾 ソース情報を保存: {sources_file}")
        
        return mock_sources
        
    async def demo_audio_generation(self):
        """音声生成のデモ"""
        print("\n🎵 【ステップ 2】音声生成（NotebookLM）")
        print("-" * 40)
        
        from notebook_lm.audio_generator import AudioInfo
        
        # モック音声ファイルを作成
        audio_file = settings.AUDIO_DIR / "generated_audio_demo.mp3"
        audio_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 空のファイルを作成（実際にはNotebookLMで生成）
        with open(audio_file, 'wb') as f:
            f.write(b'')  # プレースホルダー
            
        mock_audio = AudioInfo(
            file_path=audio_file,
            duration=185.7,
            quality_score=0.96,
            sample_rate=44100,
            file_size=2980000,
            language="ja",
            channels=2
        )
        
        print(f"🎧 生成された音声:")
        print(f"  ファイル: {mock_audio.file_path.name}")
        print(f"  時間: {mock_audio.duration:.1f}秒 ({mock_audio.duration//60:.0f}分{mock_audio.duration%60:.0f}秒)")
        print(f"  品質スコア: {mock_audio.quality_score:.2f}")
        print(f"  サンプルレート: {mock_audio.sample_rate}Hz")
        print(f"  ファイルサイズ: {mock_audio.file_size/1024/1024:.1f}MB")
        
        return mock_audio
        
    async def demo_transcript_processing(self):
        """文字起こし処理のデモ"""
        print("\n📝 【ステップ 3】文字起こし処理")
        print("-" * 40)
        
        from notebook_lm.transcript_processor import TranscriptInfo, TranscriptSegment
        
        # モック台本セグメントを作成
        segments = [
            TranscriptSegment(
                id=1,
                start_time=0.0,
                end_time=15.2,
                speaker="ナレーター1",
                text="こんにちは。今日はAI技術の最新動向について詳しく解説していきます。",
                confidence=0.98
            ),
            TranscriptSegment(
                id=2,
                start_time=15.2,
                end_time=32.8,
                speaker="ナレーター2",
                text="2024年は特に生成AIの分野で大きな進歩が見られました。",
                confidence=0.96
            ),
            TranscriptSegment(
                id=3,
                start_time=32.8,
                end_time=48.5,
                speaker="ナレーター1",
                text="機械学習のアルゴリズムも従来より効率的になっています。",
                confidence=0.97
            ),
            TranscriptSegment(
                id=4,
                start_time=48.5,
                end_time=65.1,
                speaker="ナレーター2",
                text="産業界での応用も急速に拡大しており、自動化技術の導入が進んでいます。",
                confidence=0.95
            )
        ]
        
        mock_transcript = TranscriptInfo(
            title="AI技術の最新動向",
            total_duration=185.7,
            segments=segments,
            accuracy_score=0.965,
            language="ja"
        )
        
        print(f"📄 文字起こし結果:")
        print(f"  タイトル: {mock_transcript.title}")
        print(f"  総時間: {mock_transcript.total_duration:.1f}秒")
        print(f"  セグメント数: {len(mock_transcript.segments)}個")
        print(f"  精度スコア: {mock_transcript.accuracy_score:.3f}")
        
        print(f"\n📋 台本内容（抜粋）:")
        for segment in segments[:2]:
            print(f"  [{segment.start_time:.1f}s-{segment.end_time:.1f}s] {segment.speaker}")
            print(f"    「{segment.text}」")
            print(f"    信頼度: {segment.confidence:.2f}")
        
        # 台本をファイルに保存
        transcript_file = settings.TRANSCRIPTS_DIR / "transcript_demo.json"
        transcript_file.parent.mkdir(parents=True, exist_ok=True)
        
        import json
        transcript_data = {
            "title": mock_transcript.title,
            "total_duration": mock_transcript.total_duration,
            "accuracy_score": mock_transcript.accuracy_score,
            "language": mock_transcript.language,
            "segments": [
                {
                    "id": seg.id,
                    "start_time": seg.start_time,
                    "end_time": seg.end_time,
                    "speaker": seg.speaker,
                    "text": seg.text,
                    "confidence": seg.confidence
                }
                for seg in mock_transcript.segments
            ]
        }
        
        with open(transcript_file, 'w', encoding='utf-8') as f:
            json.dump(transcript_data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 台本を保存: {transcript_file}")
        
        return mock_transcript
        
    async def demo_slide_generation(self):
        """スライド生成のデモ"""
        print("\n🎨 【ステップ 4】スライド生成（Google Slides）")
        print("-" * 40)
        
        from slides.slide_generator import SlideInfo, SlidesPackage
        
        # モックスライドを作成
        slides = [
            SlideInfo(
                slide_id=1,
                title="AI技術の最新動向",
                content="2024年における人工知能技術の発展",
                layout="title_slide",
                duration=15.2
            ),
            SlideInfo(
                slide_id=2,
                title="生成AIの進歩",
                content="• 大規模言語モデルの改善\n• 画像生成技術の向上\n• マルチモーダルAIの登場",
                layout="content_slide",
                duration=17.6
            ),
            SlideInfo(
                slide_id=3,
                title="機械学習の効率化",
                content="• 新しいアルゴリズムの開発\n• 計算効率の向上\n• 学習データの最適化",
                layout="content_slide",
                duration=15.7
            ),
            SlideInfo(
                slide_id=4,
                title="産業応用の拡大",
                content="• 自動化技術の導入\n• 業務プロセスの改善\n• 新しいビジネスモデル",
                layout="content_slide",
                duration=16.6
            ),
            SlideInfo(
                slide_id=5,
                title="まとめ",
                content="AI技術は急速に発展し、様々な分野で活用されています",
                layout="conclusion_slide",
                duration=12.0
            )
        ]
        
        # スライドファイルを作成
        slides_file = settings.SLIDES_DIR / "ai_trends_presentation_demo.pptx"
        slides_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 空のファイルを作成（実際にはGoogle Slidesで生成）
        with open(slides_file, 'wb') as f:
            f.write(b'')  # プレースホルダー
            
        mock_slides_package = SlidesPackage(
            file_path=slides_file,
            slides=slides,
            total_slides=len(slides),
            theme="business",
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
        print(f"🎯 生成されたスライド:")
        print(f"  ファイル: {mock_slides_package.file_path.name}")
        print(f"  スライド数: {mock_slides_package.total_slides}枚")
        print(f"  テーマ: {mock_slides_package.theme}")
        
        print(f"\n📑 スライド構成:")
        total_duration = 0
        for slide in slides:
            print(f"  {slide.slide_id}. {slide.title} ({slide.duration:.1f}s)")
            print(f"     レイアウト: {slide.layout}")
            total_duration += slide.duration
        
        print(f"\n⏱️ 総表示時間: {total_duration:.1f}秒")
        
        return mock_slides_package
        
    async def demo_video_composition(self):
        """動画合成のデモ"""
        print("\n🎬 【ステップ 5】動画合成（MoviePy）")
        print("-" * 40)
        
        from video_editor.video_composer import VideoInfo
        
        # モック動画ファイルを作成
        video_file = settings.VIDEOS_DIR / "ai_trends_video_demo.mp4"
        video_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 空のファイルを作成（実際にはMoviePyで生成）
        with open(video_file, 'wb') as f:
            f.write(b'')  # プレースホルダー
            
        mock_video = VideoInfo(
            file_path=video_file,
            duration=185.7,
            resolution=(1920, 1080),
            fps=30,
            file_size=75000000,
            has_subtitles=True,
            has_effects=True,
            created_at=datetime.now()
        )
        
        print(f"🎥 生成された動画:")
        print(f"  ファイル: {mock_video.file_path.name}")
        print(f"  時間: {mock_video.duration:.1f}秒 ({mock_video.duration//60:.0f}分{mock_video.duration%60:.0f}秒)")
        print(f"  解像度: {mock_video.resolution[0]}x{mock_video.resolution[1]} ({mock_video.resolution[0]/mock_video.resolution[1]:.1f}:1)")
        print(f"  フレームレート: {mock_video.fps}fps")
        print(f"  ファイルサイズ: {mock_video.file_size/1024/1024:.1f}MB")
        print(f"  字幕: {'有り' if mock_video.has_subtitles else '無し'}")
        print(f"  エフェクト: {'有り' if mock_video.has_effects else '無し'}")
        
        # 字幕ファイルも作成
        subtitle_file = settings.VIDEOS_DIR / "ai_trends_video_demo.srt"
        with open(subtitle_file, 'w', encoding='utf-8') as f:
            f.write("""1
00:00:00,000 --> 00:00:15,200
こんにちは。今日はAI技術の最新動向について詳しく解説していきます。

2
00:00:15,200 --> 00:00:32,800
2024年は特に生成AIの分野で大きな進歩が見られました。

3
00:00:32,800 --> 00:00:48,500
機械学習のアルゴリズムも従来より効率的になっています。

4
00:00:48,500 --> 00:01:05,100
産業界での応用も急速に拡大しており、自動化技術の導入が進んでいます。
""")
        
        print(f"📝 字幕ファイル: {subtitle_file.name}")
        
        return mock_video
        
    async def demo_youtube_upload(self):
        """YouTube アップロードのデモ"""
        print("\n📺 【ステップ 6】YouTube アップロード")
        print("-" * 40)
        
        from youtube.uploader import UploadResult
        from youtube.metadata_generator import VideoMetadata
        
        # モックメタデータ
        mock_metadata = VideoMetadata(
            title="AI技術の最新動向 - 2024年版完全解説",
            description="""2024年におけるAI技術の最新動向について詳しく解説します。

🎯 この動画で学べること:
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
        
        # モックアップロード結果
        mock_upload_result = UploadResult(
            video_id="dQw4w9WgXcQ_demo",
            video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ_demo",
            upload_status="success",
            processing_status="processing",
            privacy_status="private",
            uploaded_at=datetime.now()
        )
        
        print(f"🚀 アップロード結果:")
        print(f"  動画ID: {mock_upload_result.video_id}")
        print(f"  URL: {mock_upload_result.video_url}")
        print(f"  アップロード状況: {mock_upload_result.upload_status}")
        print(f"  処理状況: {mock_upload_result.processing_status}")
        print(f"  公開設定: {mock_upload_result.privacy_status}")
        
        print(f"\n📋 動画メタデータ:")
        print(f"  タイトル: {mock_metadata.title}")
        print(f"  説明文: {len(mock_metadata.description)}文字")
        print(f"  タグ数: {len(mock_metadata.tags)}個")
        print(f"  カテゴリ: {mock_metadata.category_id} (教育)")
        
        return mock_upload_result
        
    async def show_output_files(self):
        """生成された成果物を表示"""
        print("\n📁 【成果物一覧】")
        print("-" * 40)
        
        output_files = []
        
        # データディレクトリ内のファイルをチェック
        for directory in [settings.DATA_DIR, settings.AUDIO_DIR, settings.SLIDES_DIR, 
                         settings.VIDEOS_DIR, settings.TRANSCRIPTS_DIR]:
            if directory.exists():
                for file_path in directory.rglob("*"):
                    if file_path.is_file():
                        size = file_path.stat().st_size
                        output_files.append((file_path, size))
        
        if output_files:
            print("📄 生成されたファイル:")
            total_size = 0
            for file_path, size in sorted(output_files):
                relative_path = file_path.relative_to(project_root)
                if size > 1024 * 1024:
                    size_str = f"{size/1024/1024:.1f}MB"
                elif size > 1024:
                    size_str = f"{size/1024:.1f}KB"
                else:
                    size_str = f"{size}B"
                
                print(f"  📄 {relative_path} ({size_str})")
                total_size += size
            
            print(f"\n💾 総ファイルサイズ: {total_size/1024/1024:.1f}MB")
        else:
            print("📄 ファイルが見つかりませんでした")
        
        # ディレクトリ構造を表示
        print(f"\n📂 ディレクトリ構造:")
        print(f"  📁 {settings.DATA_DIR.name}/")
        for subdir in [settings.AUDIO_DIR, settings.SLIDES_DIR, settings.VIDEOS_DIR, settings.TRANSCRIPTS_DIR]:
            if subdir.exists():
                file_count = len(list(subdir.glob("*")))
                print(f"    📁 {subdir.name}/ ({file_count}ファイル)")

async def main():
    """メインデモ実行"""
    demo = DemoRunner()
    await demo.run_full_demo()
    
    print("\n🎉 デモンストレーション完了!")
    print("\n💡 次のステップ:")
    print("  1. API認証情報を設定")
    print("  2. 実際のNotebookLM連携をテスト")
    print("  3. Google Slides APIを設定")
    print("  4. YouTube APIを設定")
    print("  5. 本格的な動画生成を実行")

if __name__ == "__main__":
    asyncio.run(main())

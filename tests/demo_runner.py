"""
デモ実行クラス
"""
import asyncio
from pathlib import Path
from datetime import datetime

from config.settings import settings, create_directories
from .demo_data import (
    get_mock_sources,
    get_mock_transcript,
    get_mock_audio_info,
    get_mock_slides_package,
    get_mock_video_info,
    get_mock_metadata,
    get_mock_upload_result,
)


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

        mock_sources = get_mock_sources()

        print(f"📊 収集されたソース: {len(mock_sources)}件")
        for i, source in enumerate(mock_sources, 1):
            print(f"  {i}. {source.title}")
            print(f"     関連性: {source.relevance_score:.2f} | 信頼性: {source.reliability_score:.2f}")

    async def demo_audio_generation(self):
        """音声生成のデモ"""
        print("\n🎵 【ステップ 2】音声生成")
        print("-" * 40)

        mock_audio = get_mock_audio_info()

        print(f"🎧 生成された音声:")
        print(f"  ファイル: {mock_audio.file_path}")
        print(f"  長さ: {mock_audio.duration:.1f}秒")
        print(f"  サンプリングレート: {mock_audio.sample_rate}Hz")
        print(f"  チャンネル数: {mock_audio.channels}")
        print(f"  品質スコア: {mock_audio.quality_score:.2f}")

    async def demo_transcript_processing(self):
        """文字起こしのデモ"""
        print("\n📝 【ステップ 3】文字起こし")
        print("-" * 40)

        mock_transcript = get_mock_transcript()

        print(f"📄 文字起こし結果:")
        print(f"  タイトル: {mock_transcript.title}")
        print(f"  言語: {mock_transcript.language}")
        print(f"  長さ: {mock_transcript.duration:.1f}秒")
        print(f"  セグメント数: {len(mock_transcript.segments)}")

        print(f"\n📋 最初の数セグメント:")
        for i, segment in enumerate(mock_transcript.segments[:3], 1):
            print(f"  {i}. [{segment.start_time:.1f}s - {segment.end_time:.1f}s] {segment.content}")

    async def demo_slide_generation(self):
        """スライド生成のデモ"""
        print("\n📊 【ステップ 4】スライド生成")
        print("-" * 40)

        mock_slides = get_mock_slides_package()

        print(f"🎨 生成されたスライド:")
        print(f"  プレゼンテーションID: {mock_slides.presentation_id}")
        print(f"  URL: {mock_slides.slides_url}")
        print(f"  スライド数: {mock_slides.total_slides}")
        print(f"  保存先: {mock_slides.local_path}")

    async def demo_video_composition(self):
        """動画合成のデモ"""
        print("\n🎬 【ステップ 5】動画合成")
        print("-" * 40)

        mock_video = get_mock_video_info()

        print(f"🎥 生成された動画:")
        print(f"  ファイル: {mock_video.file_path}")
        print(f"  長さ: {mock_video.duration:.1f}秒")
        print(f"  解像度: {mock_video.resolution[0]}x{mock_video.resolution[1]}")
        print(f"  品質: {mock_video.quality}")
        print(f"  FPS: {mock_video.fps}")

    async def demo_youtube_upload(self):
        """YouTubeアップロードのデモ"""
        print("\n📤 【ステップ 6】YouTubeアップロード")
        print("-" * 40)

        mock_metadata = get_mock_metadata()
        mock_upload_result = get_mock_upload_result()

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
                relative_path = file_path.relative_to(Path(__file__).parent.parent)
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

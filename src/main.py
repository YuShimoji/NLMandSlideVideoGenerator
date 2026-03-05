"""
メインエントリーポイント
YouTube解説動画自動化システムの実行
"""
import asyncio
import sys
from pathlib import Path
from typing import Optional, List

# 基本的なロガー設定（loguruの代替）
from core.utils.logger import logger

try:
    from config.settings import settings, create_directories
except ImportError as e:
    print(f"設定ファイルの読み込みエラー: {e}")
    sys.exit(1)
try:
    from notebook_lm.source_collector import SourceCollector
    from notebook_lm.audio_generator import AudioGenerator
    from notebook_lm.transcript_processor import TranscriptProcessor
    from slides.slide_generator import SlideGenerator
    from video_editor.video_composer import VideoComposer
    from youtube.uploader import YouTubeUploader
    from youtube.metadata_generator import MetadataGenerator
except ImportError as e:
    print(f"モジュールインポートエラー: {e}")
    print("基本的な依存関係をインストールしてください")
    sys.exit(1)

class VideoGenerationPipeline:
    """動画生成パイプライン"""

    def __init__(self):
        self.source_collector = SourceCollector()
        self.audio_generator = AudioGenerator()
        self.transcript_processor = TranscriptProcessor()
        self.slide_generator = SlideGenerator()
        self.video_composer = VideoComposer()
        self.youtube_uploader = YouTubeUploader()
        self.metadata_generator = MetadataGenerator()

    async def generate_video(
        self,
        topic: str,
        urls: Optional[List[str]] = None,
        output_dir: Optional[Path] = None,
        max_slides: int = 20,
        video_quality: str = "1080p",
        upload_schedule: Optional[str] = None,
        private_upload: bool = True
    ) -> str:
        """
        動画生成の全工程を実行

        Args:
            topic: 調査トピック
            urls: ソースURL一覧
            output_dir: 出力ディレクトリ
            max_slides: 最大スライド数
            video_quality: 動画品質
            upload_schedule: アップロードスケジュール
            private_upload: 非公開アップロード

        Returns:
            str: 生成された動画のYouTube URL
        """
        try:
            logger.info(f"動画生成開始: {topic}")

            # Phase 1: NotebookLMでの作業
            logger.info("Phase 1: ソース収集・音声生成")
            sources = await self.source_collector.collect_sources(topic, urls)
            audio_info = await self.audio_generator.generate_audio(sources)
            transcript = await self.transcript_processor.process_audio(audio_info)

            # Phase 2: Google Slideでの作業
            logger.info("Phase 2: スライド生成")
            slides_pkg = await self.slide_generator.generate_slides(
                transcript, max_slides=max_slides
            )

            # Phase 3: 動画編集作業
            logger.info("Phase 3: 動画編集・合成")
            video_info = await self.video_composer.compose_video(
                audio_file=audio_info,
                slides_file=slides_pkg,
                transcript=transcript,
                quality=video_quality
            )

            # Phase 4: YouTubeアップロード
            logger.info("Phase 4: YouTubeアップロード")
            # メタデータ生成
            metadata_dict = await self.metadata_generator.generate_metadata(transcript)
            # プライバシー設定を反映
            metadata_dict["privacy_status"] = "private" if private_upload else "public"
            metadata_dict["language"] = settings.YOUTUBE_SETTINGS.get("default_language", "ja")

            # 認証（モック対応）
            await self.youtube_uploader.authenticate()

            upload_result = await self.youtube_uploader.upload_video(
                video=video_info,
                metadata=metadata_dict,
                thumbnail_path=None
            )
            youtube_url = upload_result.video_url

            logger.success(f"動画生成完了: {youtube_url}")
            return youtube_url

        except (OSError, AttributeError, TypeError, ValueError, RuntimeError) as e:
            logger.error(f"動画生成エラー: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"動画生成エラー: {str(e)}")
            raise

def main():
    """
    YouTube解説動画自動化システム

    使用例:
    python src/main.py --topic "AI技術の最新動向"
    """
    import argparse

    parser = argparse.ArgumentParser(description='YouTube解説動画自動化システム')
    parser.add_argument('--topic', required=True, help='調査トピック')
    parser.add_argument('--urls', nargs='*', help='ソースURL（複数指定可能）')
    parser.add_argument('--output-dir', help='出力ディレクトリ')
    parser.add_argument('--max-slides', type=int, default=20, help='最大スライド数')
    parser.add_argument('--video-quality', choices=['1080p', '720p', '480p'], default='1080p', help='動画品質')
    parser.add_argument('--max-chars-per-slide', type=int, default=None, help='1スライドあたりの最大文字数 (省略時は設定値を使用)')
    parser.add_argument('--upload-schedule', help='アップロードスケジュール (YYYY-MM-DD HH:MM)')
    parser.add_argument('--private-upload', action='store_true', default=True, help='非公開アップロード')
    parser.add_argument('--debug', action='store_true', help='デバッグモード')

    args = parser.parse_args()

    topic = args.topic
    urls = args.urls or []
    output_dir = args.output_dir
    max_slides = args.max_slides
    video_quality = args.video_quality
    max_chars_per_slide = args.max_chars_per_slide
    upload_schedule = args.upload_schedule
    private_upload = args.private_upload
    debug = args.debug

    # ログレベル設定
    if debug:
        print("[DEBUG] デバッグモードが有効です")

    # 必要なディレクトリを作成
    create_directories()

    # スライド1枚あたりの最大文字数が指定されていれば設定を上書き
    if max_chars_per_slide is not None:
        try:
            from config.settings import settings as _settings

            if max_chars_per_slide > 0:
                _settings.SLIDES_SETTINGS["max_chars_per_slide"] = max_chars_per_slide
                logger.info(f"SLIDES_SETTINGS.max_chars_per_slide を {max_chars_per_slide} に上書きしました")
        except (ImportError, AttributeError, TypeError, ValueError, OSError) as e:
            logger.warning(f"max_chars_per_slide オプションの適用に失敗しました: {e}")
        except Exception as e:
            logger.warning(f"max_chars_per_slide オプションの適用に失敗しました: {e}")

    # パイプライン実行
    pipeline = VideoGenerationPipeline()

    try:
        youtube_url = asyncio.run(
            pipeline.generate_video(
                topic=topic,
                urls=list(urls) if urls else None,
                output_dir=Path(output_dir) if output_dir else None,
                max_slides=max_slides,
                video_quality=video_quality,
                upload_schedule=upload_schedule,
                private_upload=private_upload
            )
        )

        print("✅ 動画生成完了!")
        print(f"📺 YouTube URL: {youtube_url}")

    except (OSError, RuntimeError, TypeError, ValueError) as e:
        print(f"❌ エラーが発生しました: {str(e)}")
        if debug:
            raise
    except Exception as e:
        print(f"❌ エラーが発生しました: {str(e)}")
        if debug:
            raise

if __name__ == "__main__":
    main()

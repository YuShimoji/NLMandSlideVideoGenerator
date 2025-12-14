"""
API統合テスト実行クラス
"""
import asyncio
from pathlib import Path

from config.settings import settings
from .api_test_data import get_test_sources, get_test_slides_content, get_test_text, get_test_voice_config


class APIIntegrationTest:
    """API統合テストクラス"""

    def __init__(self):
        self.test_results = {}

    async def run_all_tests(self):
        """全APIテストを実行"""
        print("🧪 API統合テスト開始")
        print("=" * 60)

        # 1. API認証情報確認
        await self.test_api_keys()

        # 2. Gemini API テスト
        await self.test_gemini_api()

        # 3. 音声生成API テスト
        await self.test_tts_apis()

        # 4. YouTube API テスト
        await self.test_youtube_api()

        # 5. Google Slides API テスト
        await self.test_slides_api()

        # 6. 統合パイプラインテスト
        await self.test_integration_pipeline()

        # 結果サマリー
        await self.show_test_summary()

    async def test_api_keys(self):
        """API認証情報テスト"""
        print("\n🔑 【テスト 1】API認証情報確認")
        print("-" * 40)

        try:
            status = {
                "gemini": bool(settings.GEMINI_API_KEY),
                "openai": bool(settings.OPENAI_API_KEY),
                "elevenlabs": bool(settings.TTS_SETTINGS.get("elevenlabs", {}).get("api_key", "")),
                "azure_speech": bool(settings.TTS_SETTINGS.get("azure", {}).get("key", ""))
                and bool(settings.TTS_SETTINGS.get("azure", {}).get("region", "")),
                "youtube": bool(settings.YOUTUBE_CLIENT_ID and settings.YOUTUBE_CLIENT_SECRET),
                "google_oauth": bool(
                    getattr(settings, "GOOGLE_CLIENT_SECRETS_FILE", None)
                    and settings.GOOGLE_CLIENT_SECRETS_FILE.exists()
                ),
            }

            missing = []
            if not settings.GEMINI_API_KEY:
                missing.append("GEMINI_API_KEY")
            if not settings.OPENAI_API_KEY:
                missing.append("OPENAI_API_KEY")
            if not settings.TTS_SETTINGS.get("elevenlabs", {}).get("api_key", ""):
                missing.append("ELEVENLABS_API_KEY")
            if not settings.TTS_SETTINGS.get("azure", {}).get("key", ""):
                missing.append("AZURE_SPEECH_KEY")
            if not settings.TTS_SETTINGS.get("azure", {}).get("region", ""):
                missing.append("AZURE_SPEECH_REGION")
            if not settings.YOUTUBE_CLIENT_ID:
                missing.append("YOUTUBE_CLIENT_ID")
            if not settings.YOUTUBE_CLIENT_SECRET:
                missing.append("YOUTUBE_CLIENT_SECRET")
            if not (
                getattr(settings, "GOOGLE_CLIENT_SECRETS_FILE", None)
                and settings.GOOGLE_CLIENT_SECRETS_FILE.exists()
            ):
                missing.append("GOOGLE_CLIENT_SECRETS_FILE")

            print("📊 API認証状況:")
            for service, available in status.items():
                status_icon = "✅" if available else "❌"
                print(f"  {status_icon} {service}: {'設定済み' if available else '未設定'}")

            if missing:
                print(f"\n⚠️ 不足しているAPI認証情報:")
                for key in missing:
                    print(f"  - {key}")

            self.test_results["api_keys"] = {
                "status": "success" if not missing else "partial",
                "available_apis": sum(status.values()),
                "total_apis": len(status),
                "missing": missing
            }

        except Exception as e:
            print(f"❌ API認証情報確認失敗: {e}")
            self.test_results["api_keys"] = {"status": "failed", "error": str(e)}

    async def test_gemini_api(self):
        """Gemini API テスト"""
        print("\n🤖 【テスト 2】Gemini API連携")
        print("-" * 40)

        try:
            from notebook_lm.gemini_integration import GeminiIntegration

            if not settings.GEMINI_API_KEY:
                print("⚠️ Gemini APIキーが設定されていません")
                self.test_results["gemini"] = {"status": "skipped", "reason": "no_api_key"}
                return

            gemini = GeminiIntegration(settings.GEMINI_API_KEY)

            test_sources = get_test_sources()

            print("📝 スクリプト生成テスト実行中...")
            script_info = await gemini.generate_script_from_sources(
                sources=test_sources,
                topic="AI技術の最新動向",
                target_duration=180.0,
                language="ja"
            )

            print(f"✅ スクリプト生成成功:")
            print(f"  タイトル: {script_info.title}")
            print(f"  セグメント数: {len(script_info.segments)}")
            print(f"  推定時間: {script_info.total_duration_estimate:.1f}秒")
            print(f"  品質スコア: {script_info.quality_score:.2f}")

            # 使用統計確認
            stats = gemini.get_usage_stats()
            print(f"📊 使用統計: {stats['request_count']}リクエスト")

            self.test_results["gemini"] = {
                "status": "success",
                "script_segments": len(script_info.segments),
                "duration_estimate": script_info.total_duration_estimate,
                "quality_score": script_info.quality_score,
                "usage_stats": stats
            }

        except Exception as e:
            print(f"❌ Gemini API テスト失敗: {e}")
            self.test_results["gemini"] = {"status": "failed", "error": str(e)}

    async def test_tts_apis(self):
        """音声生成API テスト"""
        print("\n🎵 【テスト 3】音声生成API連携")
        print("-" * 40)

        try:
            from audio.tts_integration import TTSIntegration

            # API キー設定
            tts_keys = {
                "elevenlabs": settings.TTS_SETTINGS.get("elevenlabs", {}).get("api_key", ""),
                "openai": settings.OPENAI_API_KEY,
                "azure_speech": settings.TTS_SETTINGS.get("azure", {}).get("key", ""),
                "azure_region": settings.TTS_SETTINGS.get("azure", {}).get("region", ""),
                "google_cloud": settings.TTS_SETTINGS.get("google_cloud", {}).get("api_key", ""),
            }

            tts = TTSIntegration(tts_keys)

            # プロバイダー状況確認
            provider_status = tts.get_provider_status()
            print("📊 TTS プロバイダー状況:")
            for provider, available in provider_status.items():
                status_icon = "✅" if available else "❌"
                print(f"  {status_icon} {provider}: {'利用可能' if available else '未設定'}")

            # 利用可能なプロバイダーがある場合、テスト実行
            available_providers = [p for p, status in provider_status.items() if status]

            if available_providers:
                print(f"\n🎤 音声生成テスト実行中... (プロバイダー: {available_providers[0]})")

                test_text = get_test_text()
                output_path = Path(__file__).parent.parent / "data" / "audio" / "test_audio.mp3"

                voice_config = get_test_voice_config()

                audio_info = await tts.generate_audio(
                    text=test_text,
                    output_path=output_path,
                    voice_config=voice_config
                )

                print(f"✅ 音声生成成功:")
                print(f"  ファイル: {audio_info.file_path.name}")
                print(f"  時間: {audio_info.duration:.1f}秒")
                print(f"  プロバイダー: {audio_info.provider}")
                print(f"  品質スコア: {audio_info.quality_score:.2f}")

                self.test_results["tts"] = {
                    "status": "success",
                    "available_providers": available_providers,
                    "test_audio_duration": audio_info.duration,
                    "provider_used": audio_info.provider,
                    "quality_score": audio_info.quality_score
                }
            else:
                print("⚠️ 利用可能なTTSプロバイダーがありません")
                self.test_results["tts"] = {"status": "skipped", "reason": "no_providers"}

        except Exception as e:
            print(f"❌ 音声生成API テスト失敗: {e}")
            self.test_results["tts"] = {"status": "failed", "error": str(e)}

    async def test_youtube_api(self):
        """YouTube API テスト"""
        print("\n📺 【テスト 4】YouTube API連携")
        print("-" * 40)

        try:
            from youtube.uploader import YouTubeUploader

            if not (settings.YOUTUBE_CLIENT_ID and settings.YOUTUBE_CLIENT_SECRET):
                print("⚠️ YouTube API認証情報が設定されていません")
                self.test_results["youtube"] = {"status": "skipped", "reason": "no_credentials"}
                return

            uploader = YouTubeUploader()

            print("🔐 YouTube API認証テスト...")
            auth_result = await uploader.authenticate()

            if auth_result:
                print("✅ YouTube API認証成功")

                # チャンネル情報取得テスト
                print("📊 チャンネル情報取得テスト...")
                channel_info = await uploader.get_channel_info()

                print(f"  チャンネル名: {channel_info['title']}")
                print(f"  登録者数: {channel_info['subscriber_count']:,}人")
                print(f"  動画数: {channel_info['video_count']:,}本")

                # クォータ使用状況確認
                quota_usage = uploader.get_quota_usage()
                print(f"📈 クォータ使用状況: {quota_usage['used']}/{quota_usage['limit']}")

                self.test_results["youtube"] = {
                    "status": "success",
                    "auth_success": True,
                    "channel_info": channel_info,
                    "quota_usage": quota_usage
                }
            else:
                print("❌ YouTube API認証失敗")
                self.test_results["youtube"] = {"status": "failed", "reason": "auth_failed"}

        except Exception as e:
            print(f"❌ YouTube API テスト失敗: {e}")
            self.test_results["youtube"] = {"status": "failed", "error": str(e)}

    async def test_slides_api(self):
        """Google Slides API テスト"""
        print("\n🎨 【テスト 5】Google Slides API連携")
        print("-" * 40)

        try:
            from slides.slide_generator import SlideGenerator

            if not (
                getattr(settings, "GOOGLE_CLIENT_SECRETS_FILE", None)
                and settings.GOOGLE_CLIENT_SECRETS_FILE.exists()
            ):
                print("⚠️ Google Slides API認証ファイルが設定されていません")
                self.test_results["slides"] = {"status": "skipped", "reason": "no_credentials_file"}
                return

            generator = SlideGenerator()

            print("🔐 Google Slides API認証テスト...")
            auth_result = await generator.authenticate()

            if auth_result:
                print("✅ Google Slides API認証成功")

                test_slides = get_test_slides_content()

                print("📊 スライド作成テスト...")
                # 実際のスライド作成はモックで実行
                slides_package = await generator.create_slides_from_content(
                    slides_content=test_slides,
                    presentation_title="API連携テスト"
                )

                print(f"✅ スライド作成成功:")
                print(f"  スライド数: {slides_package.total_slides}枚")
                print(f"  ファイル: {slides_package.file_path.name}")

                self.test_results["slides"] = {
                    "status": "success",
                    "auth_success": True,
                    "slides_created": slides_package.total_slides
                }
            else:
                print("❌ Google Slides API認証失敗")
                self.test_results["slides"] = {"status": "failed", "reason": "auth_failed"}

        except Exception as e:
            print(f"❌ Google Slides API テスト失敗: {e}")
            self.test_results["slides"] = {"status": "failed", "error": str(e)}

    async def test_integration_pipeline(self):
        """統合パイプラインテスト"""
        print("\n🔄 【テスト 6】統合パイプライン")
        print("-" * 40)

        try:
            # 成功したAPIの数を確認
            successful_apis = sum(1 for result in self.test_results.values()
                                if result.get("status") == "success")

            total_apis = len(self.test_results)
            success_rate = successful_apis / total_apis if total_apis > 0 else 0

            print(f"📊 API連携成功率: {successful_apis}/{total_apis} ({success_rate:.1%})")

            if success_rate >= 0.6:  # 60%以上成功
                print("✅ 統合パイプライン準備完了")
                print("💡 次のステップ: 本格的な動画生成テスト")

                self.test_results["integration"] = {
                    "status": "ready",
                    "success_rate": success_rate,
                    "successful_apis": successful_apis,
                    "total_apis": total_apis
                }
            else:
                print("⚠️ 統合パイプライン準備不完全")
                print("💡 不足しているAPI設定を完了してください")

                self.test_results["integration"] = {
                    "status": "incomplete",
                    "success_rate": success_rate,
                    "successful_apis": successful_apis,
                    "total_apis": total_apis
                }

        except Exception as e:
            print(f"❌ 統合パイプラインテスト失敗: {e}")
            self.test_results["integration"] = {"status": "failed", "error": str(e)}

    async def show_test_summary(self):
        """テスト結果サマリー表示"""
        print("\n" + "=" * 60)
        print("📋 API統合テスト結果サマリー")
        print("=" * 60)

        for test_name, result in self.test_results.items():
            status = result.get("status", "unknown")

            if status == "success":
                print(f"✅ {test_name}: 成功")
            elif status == "failed":
                print(f"❌ {test_name}: 失敗 - {result.get('error', '不明なエラー')}")
            elif status == "skipped":
                print(f"⏭️ {test_name}: スキップ - {result.get('reason', '理由不明')}")
            elif status == "partial":
                print(f"🟡 {test_name}: 部分的成功")
            else:
                print(f"❓ {test_name}: {status}")

        # 次のアクション提案
        print(f"\n💡 推奨アクション:")

        failed_tests = [name for name, result in self.test_results.items()
                       if result.get("status") == "failed"]
        skipped_tests = [name for name, result in self.test_results.items()
                        if result.get("status") == "skipped"]

        if failed_tests:
            print(f"  🔧 失敗したテストの修正: {', '.join(failed_tests)}")

        if skipped_tests:
            print(f"  🔑 API認証設定の完了: {', '.join(skipped_tests)}")

        integration_status = self.test_results.get("integration", {}).get("status")
        if integration_status == "ready":
            print(f"  🚀 本格的な動画生成テストの実行")
        elif integration_status == "incomplete":
            print(f"  ⚠️ 不足しているAPI設定の完了")

        print(f"\n📊 総合評価: ", end="")
        success_count = sum(1 for result in self.test_results.values()
                          if result.get("status") == "success")
        total_count = len(self.test_results)

        if success_count == total_count:
            print("🎉 すべてのテストが成功しました！")
        elif success_count >= total_count * 0.7:
            print("✅ 大部分のテストが成功しました")
        elif success_count >= total_count * 0.5:
            print("🟡 一部のテストが成功しました")
        else:
            print("❌ 多くのテストが失敗しました")

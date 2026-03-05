"""
音声生成モジュール
NotebookLMを使用したラジオ風音声の生成
"""
import asyncio
from typing import List, Optional
from pathlib import Path
from dataclasses import dataclass
import requests
import time
import wave
import struct

# 基本的なロガー設定（loguruの代替）
from core.utils.logger import logger
from .gemini_integration import GeminiIntegration

from config.settings import settings
from .source_collector import SourceInfo

@dataclass
class AudioInfo:
    """音声情報

    互換性のため、品質スコアやファイルサイズなどは省略可能な引数として扱う。
    既存テストでは file_path, duration, language, sample_rate のみを指定しているため、
    quality_score と file_size にはデフォルト値を設定する。
    """

    file_path: Path
    duration: float
    quality_score: float = 1.0
    sample_rate: int = 44100
    file_size: int = 0
    language: str = "ja"
    channels: int = 2

class AudioGenerator:
    """音声生成クラス"""
    
    def __init__(self):
        self.audio_quality_threshold = settings.NOTEBOOK_LM_SETTINGS["audio_quality_threshold"]
        self.max_duration = settings.NOTEBOOK_LM_SETTINGS["max_audio_duration"]
        self.output_dir = settings.AUDIO_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 代替ワークフロー用: Gemini API キー設定
        self.gemini_api_key = settings.GEMINI_API_KEY if hasattr(settings, 'GEMINI_API_KEY') else None
        self.gemini_integration = GeminiIntegration(self.gemini_api_key) if self.gemini_api_key else None

    def _tts_is_available(self) -> bool:
        provider_name = (settings.TTS_SETTINGS.get("provider", "none") or "none").lower()
        if provider_name == "none":
            return False

        api_keys = {
            "elevenlabs": settings.TTS_SETTINGS.get("elevenlabs", {}).get("api_key", ""),
            "openai": getattr(settings, "OPENAI_API_KEY", ""),
            "azure_speech": settings.TTS_SETTINGS.get("azure", {}).get("key", ""),
            "google_cloud": settings.TTS_SETTINGS.get("google_cloud", {}).get("api_key", ""),
        }
        return any(api_keys.values())
         
    async def generate_audio(self, sources: List[SourceInfo]) -> AudioInfo:
        """
        ソース情報から音声を生成
        
        Args:
            sources: ソース情報一覧
            
        Returns:
            AudioInfo: 生成された音声情報
        """
        logger.info(f"音声生成開始: {len(sources)}件のソースから")
        
        try:
            # 代替ワークフロー: Gemini + TTS 統合
            if self.gemini_integration and self._tts_is_available():
                logger.info("Gemini + TTS 代替ワークフローを使用")
                
                # Step 1: Geminiでスクリプト生成
                script_info = await self._generate_script_with_gemini(sources)
                
                # Step 2: TTSで音声生成
                audio_file = await self._generate_audio_with_tts(script_info)
                
                # Step 3: 音声品質の検証
                audio_info = await self._validate_audio_quality(audio_file)
                
                logger.success(f"代替ワークフロー音声生成完了: {audio_info.file_path}")
                return audio_info
                
            else:
                # フォールバック: プレースホルダー実装
                logger.warning("Gemini/TTS 設定が不足しているため、プレースホルダー実装を使用")
                return await self._generate_placeholder_audio()

        except (requests.RequestException, OSError, AttributeError, TypeError, ValueError, RuntimeError) as e:
            logger.error(f"音声生成エラー: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"音声生成エラー: {str(e)}")
            raise
    
    async def _generate_script_with_gemini(self, sources: List[SourceInfo]) -> 'ScriptInfo':
        """
        Gemini APIを使用してスクリプトを生成
        
        Args:
            sources: ソース情報一覧
            
        Returns:
            ScriptInfo: 生成されたスクリプト情報
        """
        logger.debug("Geminiでスクリプト生成開始")
        
        if not self.gemini_integration:
            raise ValueError("Gemini integration is not initialized")
        
        # SourceInfo を GeminiIntegration 用に変換
        gemini_sources = [
            {
                "title": source.title,
                "url": source.url,
                "content_preview": getattr(source, 'content_preview', ''),
                "relevance_score": getattr(source, 'relevance_score', 1.0),
                "reliability_score": getattr(source, 'reliability_score', 1.0)
            }
            for source in sources
        ]
        
        # トピックを推測（最初のソースのタイトルを使用）
        topic = sources[0].title if sources else "General Topic"
        
        # Gemini API でスクリプト生成
        script_info = await self.gemini_integration.generate_script_from_sources(
            sources=gemini_sources,
            topic=topic,
            target_duration=self.max_duration,
            language="ja"
        )
        
        logger.debug(f"Geminiスクリプト生成完了: {len(script_info.segments)}セグメント")
        return script_info
    
    async def _generate_audio_with_tts(self, script_info: 'ScriptInfo') -> Path:
        """
        TTS統合を使用して音声を生成
        
        Args:
            script_info: スクリプト情報
            
        Returns:
            Path: 生成された音声ファイルのパス
        """
        logger.debug("TTSで音声生成開始")
        
        try:
            from audio.tts_integration import TTSIntegration, VoiceConfig, TTSProvider

            api_keys = {
                "elevenlabs": settings.TTS_SETTINGS.get("elevenlabs", {}).get("api_key", ""),
                "openai": getattr(settings, "OPENAI_API_KEY", ""),
                "azure_speech": settings.TTS_SETTINGS.get("azure", {}).get("key", ""),
                "azure_region": settings.TTS_SETTINGS.get("azure", {}).get("region", ""),
                "google_cloud": settings.TTS_SETTINGS.get("google_cloud", {}).get("api_key", ""),
            }

            tts = TTSIntegration(api_keys)
            
            # スクリプトを結合
            full_script = "\n".join([
                f"{segment.get('section', '')}: {segment.get('content', '')}"
                for segment in script_info.segments
            ])

            provider_key = (settings.TTS_SETTINGS.get("provider", "none") or "none").lower()
            if provider_key == "none" or provider_key not in settings.TTS_SETTINGS:
                provider_key = "elevenlabs"

            provider_voice = (
                settings.TTS_SETTINGS.get(provider_key, {}).get("voice_id")
                or settings.TTS_SETTINGS.get(provider_key, {}).get("voice")
                or ""
            )
            fallback_voice = (
                settings.TTS_SETTINGS.get("elevenlabs", {}).get("voice_id")
                or settings.TTS_SETTINGS.get("azure", {}).get("voice")
                or settings.TTS_SETTINGS.get("openai", {}).get("voice")
                or settings.TTS_SETTINGS.get("google_cloud", {}).get("voice")
                or "default"
            )
            voice_id = provider_voice or fallback_voice
            language = getattr(script_info, "language", None) or "ja"

            voice_config = VoiceConfig(
                voice_id=voice_id,
                language=language,
                gender="female",
                age_range="adult",
                accent="japanese" if language == "ja" else "",
                quality="high",
            )

            output_path = self.output_dir / f"gemini_tts_{int(time.time())}.mp3"

            try:
                provider_enum = TTSProvider(provider_key)
            except ValueError:
                provider_enum = None

            if provider_enum is not None:
                status = tts.get_provider_status()
                if not status.get(provider_enum.value, False):
                    provider_enum = None

            tts_audio = await tts.generate_audio(
                text=full_script,
                output_path=output_path,
                voice_config=voice_config,
                provider=provider_enum,
            )

            logger.debug(f"TTS音声生成完了: {tts_audio.file_path}")
            return Path(tts_audio.file_path)

        except (ImportError, requests.RequestException, OSError, AttributeError, TypeError, ValueError, RuntimeError) as e:
            logger.error(f"TTS音声生成失敗: {e}")
            raise
        except Exception as e:
            logger.error(f"TTS音声生成失敗: {e}")
            raise
    
    async def _generate_placeholder_audio(self) -> AudioInfo:
        """
        プレースホルダー音声ファイルを生成
        
        Returns:
            AudioInfo: プレースホルダー音声情報
        """
        logger.warning("プレースホルダー音声生成を使用")
        
        # シンプルなWAVファイルを作成
        output_path = self.output_dir / f"placeholder_audio_{int(time.time())}.wav"
        
        # 1秒の無音WAVファイルを作成
        with wave.open(str(output_path), 'wb') as wav_file:
            wav_file.setnchannels(2)  # ステレオ
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(44100)  # 44.1kHz
            # 無音データを1秒分
            silent_data = b'\x00\x00' * 44100 * 2  # 44100サンプル * 2チャンネル * 2バイト
            wav_file.writeframes(silent_data)
        
        audio_info = AudioInfo(
            file_path=output_path,
            duration=1.0,
            quality_score=0.5,
            sample_rate=44100,
            file_size=output_path.stat().st_size,
            language="ja",
            channels=2
        )
        
        logger.debug(f"プレースホルダー音声生成完了: {output_path}")
        return audio_info
    
    async def _upload_sources(self, session_id: str, sources: List[SourceInfo]):
        """
        ソース情報をNotebookLMにアップロード (現在はシミュレーション)
        
        Args:
            session_id: NotebookLMセッションID
            sources: アップロードするソース一覧
        """
        logger.debug(f"ソースアップロード開始: {len(sources)}件 (セッション: {session_id})")
        
        for i, source in enumerate(sources, 1):
            logger.debug(f"アップロード中 ({i}/{len(sources)}): {source.title}")
            
            # 実際の実装ではブラウザ操作でURLを入力し、追加ボタンをクリックする
            await asyncio.sleep(0.5)  # アップロード時間のシミュレーション
        
        logger.debug("全ソースのアップロード完了")
    
    async def _request_audio_generation(self, session_id: str) -> str:
        """
        音声生成をリクエスト (現在はシミュレーション)
        
        Args:
            session_id: NotebookLMセッションID
            
        Returns:
            str: 音声生成ジョブID
        """
        logger.debug(f"音声生成リクエスト送信中... (セッション: {session_id})")
        
        # 実際の実装ではNotebookLMの「Audio Overview」機能を実行する
        await asyncio.sleep(1.0)
        
        job_id = f"audio_job_{int(time.time())}_{session_id[-4:]}"
        logger.debug(f"音声生成ジョブ開始: {job_id}")
        
        return job_id
    
    async def _wait_for_audio_completion(self, job_id: str) -> str:
        """
        音声生成の完了を待機
        
        Args:
            job_id: 音声生成ジョブID
            
        Returns:
            str: 生成された音声ファイルのURL
        """
        logger.info("音声生成完了を待機中...")
        
        max_wait_time = 600  # 10分
        check_interval = 30  # 30秒間隔
        
        for elapsed in range(0, max_wait_time, check_interval):
            logger.debug(f"生成状況確認中... ({elapsed}秒経過)")
            
            # TODO: 実際の生成状況確認実装
            status = await self._check_generation_status(job_id)
            
            if status == "completed":
                audio_url = await self._get_audio_download_url(job_id)
                logger.info("音声生成完了")
                return audio_url
            elif status == "failed":
                raise Exception("音声生成に失敗しました")
            
            await asyncio.sleep(check_interval)
        
        raise TimeoutError("音声生成がタイムアウトしました")
    
    async def _check_generation_status(self, job_id: str) -> str:
        """
        音声生成状況を確認 (現在はシミュレーション)
        
        Args:
            job_id: ジョブID
            
        Returns:
            str: 生成状況 ("processing", "completed", "failed")
        """
        # 生成状況確認のシミュレーション
        # 実際にはブラウザ上のプログレスバーやテキストを確認する
        
        # ジョブIDに基づいて完了したことにする（デモ・テスト用）
        logger.debug(f"ジョブ状況確認: {job_id}")
        await asyncio.sleep(0.5)
        
        return "completed"
    
    async def _get_audio_download_url(self, job_id: str) -> str:
        """
        音声ダウンロードURLを取得 (現在はシミュレーション)
        
        Args:
            job_id: ジョブID
            
        Returns:
            str: ダウンロードURL
        """
        # 実際の実装では「Download」ボタンのリンク先を取得するか、
        # 生成されたファイルの直接URLを探査する
        
        mock_url = f"https://example.com/audio/notebook_lm_{job_id}.mp3"
        logger.debug(f"ダウンロードURL取得: {mock_url}")
        
        return mock_url
    
    async def _download_audio(self, audio_url: str) -> Path:
        """
        音声ファイルをダウンロード
        
        Args:
            audio_url: 音声ファイルURL
            
        Returns:
            Path: ダウンロードされた音声ファイルパス
        """
        logger.info("音声ファイルダウンロード中...")
        
        # ファイル名生成（WAVにフォールバックしやすいようにwavを使用）
        timestamp = int(time.time())
        filename = f"generated_audio_{timestamp}.wav"
        output_path = self.output_dir / filename
        
        # ディレクトリ作成
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # ダウンロード実行（失敗時はローカル生成にフォールバック）
        try:
            response = requests.get(audio_url, stream=True, timeout=10)
            response.raise_for_status()
            # 一旦メモリに読まずに直接保存
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            logger.info(f"音声ダウンロード完了: {output_path}")
            return output_path
        except (requests.exceptions.RequestException, OSError) as e:
            logger.warning(f"音声ダウンロードに失敗しました。ローカルWAVのフォールバックを生成します: {e}")
        except Exception as e:
            logger.warning(f"音声ダウンロードで予期しない例外が発生しました。ローカルWAVのフォールバックを生成します: {e}")

        # 1秒の無音WAVを生成
        sample_rate = 44100
        duration_sec = 3
        n_channels = 1
        sampwidth = 2  # 16-bit
        n_frames = sample_rate * duration_sec
        with wave.open(str(output_path), 'w') as wf:
            wf.setnchannels(n_channels)
            wf.setsampwidth(sampwidth)
            wf.setframerate(sample_rate)
            silence_frame = struct.pack('<h', 0)
            wf.writeframes(silence_frame * n_frames)
        logger.info(f"フォールバック音声生成完了: {output_path}")
        return output_path
    
    async def _validate_audio_quality(self, audio_file: Path) -> AudioInfo:
        """
        音声品質を検証
        
        Args:
            audio_file: 音声ファイルパス
            
        Returns:
            AudioInfo: 検証済み音声情報
        """
        logger.debug("音声品質検証中...")
        
        try:
            # pydubを使用した音声解析
            from pydub import AudioSegment
            
            audio = AudioSegment.from_file(str(audio_file))
            
            # 基本情報取得
            duration = len(audio) / 1000.0  # 秒
            sample_rate = audio.frame_rate
            channels = audio.channels
            file_size = audio_file.stat().st_size
            
            # 品質スコア計算
            quality_score = self._calculate_audio_quality(audio)
            
            # 品質基準チェック
            if quality_score < self.audio_quality_threshold:
                logger.warning(f"音声品質が基準を下回っています: {quality_score:.2f}")
            
            # 時間制限チェック
            if duration > self.max_duration:
                logger.warning(f"音声が最大時間を超えています: {duration:.1f}秒")
            
            audio_info = AudioInfo(
                file_path=audio_file,
                duration=duration,
                quality_score=quality_score,
                sample_rate=sample_rate,
                file_size=file_size,
                language=settings.YOUTUBE_SETTINGS.get("default_audio_language", "ja"),
                channels=channels,
            )
            
            logger.debug(f"音声品質検証完了: スコア={quality_score:.2f}")
            return audio_info

        except ImportError as e:
            logger.error(f"音声品質検証エラー: {str(e)}")
        except (OSError, AttributeError, TypeError, ValueError, RuntimeError) as e:
            logger.error(f"音声品質検証エラー: {str(e)}")
        except Exception as e:
            logger.error(f"音声品質検証エラー: {str(e)}")

        try:
            fallback_size = audio_file.stat().st_size
        except OSError:
            fallback_size = 0

        # フォールバック: 基本情報のみ
        return AudioInfo(
            file_path=audio_file,
            duration=0.0,
            quality_score=0.5,
            sample_rate=44100,
            file_size=fallback_size,
            language=settings.YOUTUBE_SETTINGS.get("default_audio_language", "ja"),
            channels=2,
        )
    
    def _calculate_audio_quality(self, audio: 'AudioSegment') -> float:
        """
        音声品質スコアを計算
        
        Args:
            audio: 音声データ
            
        Returns:
            float: 品質スコア (0.0-1.0)
        """
        score = 0.5  # ベーススコア
        
        # サンプルレート評価
        if audio.frame_rate >= 44100:
            score += 0.2
        elif audio.frame_rate >= 22050:
            score += 0.1
        
        # チャンネル数評価
        if audio.channels >= 2:
            score += 0.1
        
        # 音量レベル評価
        if hasattr(audio, 'dBFS'):
            db_level = audio.dBFS
            if -20 <= db_level <= -6:  # 適切な音量範囲
                score += 0.2
        
        return min(score, 1.0)
    
    async def regenerate_audio_if_needed(self, audio_info: AudioInfo, sources: List[SourceInfo]) -> AudioInfo:
        """
        必要に応じて音声を再生成
        
        Args:
            audio_info: 現在の音声情報
            sources: ソース情報
            
        Returns:
            AudioInfo: 最終的な音声情報
        """
        if audio_info.quality_score < self.audio_quality_threshold:
            logger.warning("音声品質が低いため再生成します")
            return await self.generate_audio(sources)
        
        return audio_info

"""
音声生成モジュール
NotebookLMを使用したラジオ風音声の生成

DESIGN NOTE: Legacy stub. Audio synthesis is YMM4's responsibility.
This module only generates placeholder WAV files (_tts_is_available() always returns False).
See docs/DESIGN_FOUNDATIONS.md Section 3.
"""
import asyncio
from typing import List
from pathlib import Path
from dataclasses import dataclass
import requests
import time
import wave
import struct

# 基本的なロガー設定（loguruの代替）
from core.utils.logger import logger


from config.settings import settings
from .research_models import SourceInfo

# Type checking imports (used only in type annotations)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pydub import AudioSegment

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

        # NotebookLM 側の進行状況ポーリングをシミュレーションするための状態
        self._job_poll_count = {}

    async def generate_audio(self, sources: List[SourceInfo]) -> AudioInfo:
        """
        ソース情報から音声を生成。

        音声生成はYMM4側で行うため、ここではプレースホルダーを生成する。
        """
        logger.info(f"音声生成開始: {len(sources)}件のソースから")

        try:
            logger.warning("音声生成はYMM4で実施。プレースホルダーを使用")
            return await self._generate_placeholder_audio()
        except Exception as e:
            logger.error(f"音声生成エラー: {str(e)}")
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
        self._job_poll_count[job_id] = 0
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
        default_check_interval = 30  # 実運用想定: 30秒間隔
        simulated_check_interval = 1  # シミュレーション時: 1秒間隔
        is_simulated_job = job_id in self._job_poll_count
        check_interval = simulated_check_interval if is_simulated_job else default_check_interval

        for elapsed in range(0, max_wait_time, check_interval):
            logger.debug(f"生成状況確認中... ({elapsed}秒経過)")

            status = await self._check_generation_status(job_id)

            if status == "completed":
                audio_url = await self._get_audio_download_url(job_id)
                logger.info("音声生成完了")
                return audio_url
            if status == "failed":
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
        logger.debug(f"ジョブ状況確認: {job_id}")
        await asyncio.sleep(0.2)

        poll_count = int(self._job_poll_count.get(job_id, 0)) + 1
        self._job_poll_count[job_id] = poll_count

        # 3回目のポーリングまでは処理中、4回目以降で完了とみなす
        if poll_count <= 3:
            return "processing"

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

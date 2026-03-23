"""
音声ファイルから構造化台本を生成するモジュール (SP-051)

根本ワークフロー (DESIGN_FOUNDATIONS.md Section 0):
  NLM Audio Overview (.mp3) → Gemini Audio API → 構造化JSON → CSV → YMM4

方式A (採用): 1段階方式 — 音声を Gemini に直接送り、構造化 JSON を1回の API コールで取得。
方式B (フォールバック): Whisper → Gemini 構造化 (未実装、必要に応じて追加)。
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ScriptInfo は gemini_integration.py で定義されている。循環 import を避けつつ再利用する。
from notebook_lm.gemini_integration import ScriptInfo


class AudioTranscriber:
    """NLM Audio Overview → 構造化JSON 変換。

    Gemini Audio API を使い、音声ファイルから直接
    speaker/text/key_points の構造化JSONを生成する。
    """

    SUPPORTED_FORMATS = {".mp3", ".wav", ".aac", ".ogg", ".flac", ".m4a", ".webm"}
    MAX_FILE_SIZE_MB = 200  # Gemini File API 上限は 2GB だが実用上の制限
    INLINE_MAX_MB = 20  # inline data で送れる上限

    def __init__(
        self,
        api_key: str = "",
        model_name: Optional[str] = None,
    ):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self.model_name = model_name or os.environ.get("GEMINI_MODEL") or "gemini-2.5-flash"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def transcribe_and_structure(
        self,
        audio_path: Path,
        topic: str,
        target_duration: float = 300.0,
        language: str = "ja",
        style: str = "default",
        speaker_mapping: Optional[Dict[str, str]] = None,
        save_transcript: Optional[Path] = None,
    ) -> ScriptInfo:
        """音声ファイルから構造化台本を生成。

        1. バリデーション
        2. Gemini File API で音声をアップロード (大ファイル時)
        3. 構造化プロンプト + 音声で generate_content
        4. JSON レスポンスを ScriptInfo に変換
        5. (オプション) 中間テキストを保存

        Args:
            audio_path: 音声ファイルパス
            topic: 動画トピック
            target_duration: 目標尺 (秒)
            language: 出力言語
            style: プリセットスタイル名
            speaker_mapping: Host1/Host2 → キャラ名 の置換マップ
            save_transcript: 中間テキスト保存先 (None=保存しない)

        Returns:
            ScriptInfo
        """
        # 1. バリデーション
        audio_path = Path(audio_path)
        self._validate_audio(audio_path)

        logger.info(
            "Audio transcription start: %s (%.1fMB, topic=%s, model=%s)",
            audio_path.name,
            audio_path.stat().st_size / (1024 * 1024),
            topic,
            self.model_name,
        )

        # 2-3. Gemini API 呼び出し
        prompt = self._build_structure_prompt(topic, target_duration, language, style, speaker_mapping)
        raw_text = await self._call_gemini_audio(audio_path, prompt)

        # 4. JSON パース → ScriptInfo
        script_info = self._parse_response(raw_text, topic, language)

        # speaker_mapping 適用
        if speaker_mapping:
            script_info = self._apply_speaker_mapping(script_info, speaker_mapping)

        # 5. 中間テキスト保存
        if save_transcript:
            self._save_intermediate_transcript(raw_text, save_transcript)

        logger.info(
            "Audio transcription complete: %d segments, %.0fs estimated",
            len(script_info.segments),
            script_info.total_duration_estimate,
        )
        return script_info

    async def transcribe_only(
        self,
        audio_path: Path,
        language: str = "ja",
    ) -> str:
        """音声ファイルをテキストに文字起こしのみ。

        --save-transcript 用、またはデバッグ用。

        Returns:
            文字起こしテキスト
        """
        audio_path = Path(audio_path)
        self._validate_audio(audio_path)

        prompt = self._build_transcribe_only_prompt(language)
        text = await self._call_gemini_audio(audio_path, prompt)
        return text

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_audio(self, audio_path: Path) -> None:
        """音声ファイルのバリデーション。"""
        if not audio_path.exists():
            raise FileNotFoundError(f"音声ファイルが見つかりません: {audio_path}")

        suffix = audio_path.suffix.lower()
        if suffix not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"非対応の音声形式: {suffix}。対応形式: {', '.join(sorted(self.SUPPORTED_FORMATS))}"
            )

        size_mb = audio_path.stat().st_size / (1024 * 1024)
        if size_mb > self.MAX_FILE_SIZE_MB:
            raise ValueError(
                f"ファイルサイズが大きすぎます: {size_mb:.1f}MB (上限: {self.MAX_FILE_SIZE_MB}MB)"
            )

        if size_mb == 0:
            raise ValueError("音声ファイルが空です")

    # ------------------------------------------------------------------
    # Gemini Audio API
    # ------------------------------------------------------------------

    async def _call_gemini_audio(self, audio_path: Path, prompt: str) -> str:
        """Gemini API に音声 + プロンプトを送り、テキストレスポンスを返す。

        ファイルサイズに応じて inline data / File API を使い分ける。
        """
        try:
            from google import genai
        except ImportError:
            raise ImportError(
                "google-generativeai SDK が必要です。"
                "pip install google-genai でインストールしてください。"
            )

        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY が未設定です。環境変数またはコンストラクタで指定してください。"
            )

        client = genai.Client(api_key=self.api_key)

        size_mb = audio_path.stat().st_size / (1024 * 1024)

        if size_mb <= self.INLINE_MAX_MB:
            # inline data で送信
            response = await self._call_inline(client, audio_path, prompt)
        else:
            # File API 経由
            response = await self._call_with_file_api(client, audio_path, prompt)

        return response

    async def _call_inline(self, client: Any, audio_path: Path, prompt: str) -> str:
        """inline data で Gemini に音声を送信。"""
        import asyncio

        mime_type = self._get_mime_type(audio_path)
        audio_bytes = audio_path.read_bytes()

        def _sync_call() -> str:
            response = client.models.generate_content(
                model=self.model_name,
                contents=[
                    prompt,
                    {"inline_data": {"mime_type": mime_type, "data": audio_bytes}},
                ],
            )
            return response.text

        # google-genai の同期 API を別スレッドで実行
        return await asyncio.get_event_loop().run_in_executor(None, _sync_call)

    async def _call_with_file_api(self, client: Any, audio_path: Path, prompt: str) -> str:
        """File API で音声をアップロードしてから Gemini に送信。"""
        import asyncio

        def _sync_call() -> str:
            # アップロード
            uploaded = client.files.upload(file=str(audio_path))
            logger.info("File API upload complete: %s", uploaded.name)

            # 生成
            response = client.models.generate_content(
                model=self.model_name,
                contents=[prompt, uploaded],
            )
            return response.text

        return await asyncio.get_event_loop().run_in_executor(None, _sync_call)

    @staticmethod
    def _get_mime_type(audio_path: Path) -> str:
        """拡張子から MIME type を推定。"""
        mime_map = {
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".aac": "audio/aac",
            ".ogg": "audio/ogg",
            ".flac": "audio/flac",
            ".m4a": "audio/mp4",
            ".webm": "audio/webm",
        }
        return mime_map.get(audio_path.suffix.lower(), "audio/mpeg")

    # ------------------------------------------------------------------
    # Prompts
    # ------------------------------------------------------------------

    def _build_structure_prompt(
        self,
        topic: str,
        target_duration: float,
        language: str,
        style: str,
        speaker_mapping: Optional[Dict[str, str]],
    ) -> str:
        """1段階プロンプト: 音声 → 構造化JSON。"""
        lang_instruction = "日本語" if language == "ja" else "English"
        duration_min = target_duration / 60

        # セグメント数ヒント (target_duration から動的算出)
        if target_duration <= 300:
            seg_hint = "15-25"
        elif target_duration <= 900:
            seg_hint = "30-50"
        elif target_duration <= 1800:
            seg_hint = "60-90"
        else:
            seg_hint = "90-150"

        speaker_names = ["Host1", "Host2"]
        if speaker_mapping:
            speaker_names = list(speaker_mapping.values())[:2] or speaker_names

        return f"""あなたは音声対話の文字起こしと構造化の専門家です。

添付された音声ファイルを聞き、以下のJSON形式で構造化してください。

【重要な制約】
- 音声の内容を忠実に文字起こししてください。要約・意訳・省略は禁止です。
- 話者を音声の特徴（声質・トーン）から識別し、「{speaker_names[0]}」「{speaker_names[1]}」に割り当ててください
- 1セグメント = 1話者の連続発話
- 各セグメントのtextは50-150文字程度で分割（長い発話は複数セグメントに）
- 元の対話の論理構造（導入→本論→まとめ等）を維持
- 出力言語: {lang_instruction}
- 目標尺: 約{duration_min:.0f}分
- セグメント数の目安: {seg_hint}セグメント

【トピック】
{topic}

【出力JSON形式】
{{
  "title": "動画タイトル",
  "segments": [
    {{
      "id": 1,
      "speaker": "{speaker_names[0]}",
      "text": "発話テキスト",
      "key_points": ["重要ポイント1"],
      "duration_hint": 15
    }}
  ],
  "total_duration_estimate": {target_duration}
}}

JSONのみを出力してください。説明文は不要です。"""

    def _build_transcribe_only_prompt(self, language: str) -> str:
        """文字起こしのみのプロンプト。"""
        lang = "日本語" if language == "ja" else "English"
        return f"""添付された音声ファイルを忠実に文字起こししてください。
要約や意訳は行わず、話された内容をそのまま書き起こしてください。
話者の交代が明らかな箇所には空行を入れてください。
出力言語: {lang}"""

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    def _parse_response(self, raw_text: str, topic: str, language: str) -> ScriptInfo:
        """Gemini のテキストレスポンスを ScriptInfo に変換。"""
        # JSON ブロック抽出 (```json ... ``` のラップ対応)
        json_text = raw_text.strip()
        if json_text.startswith("```"):
            # コードブロックを除去
            lines = json_text.split("\n")
            # 先頭行 (```json) と末尾行 (```) を除去
            start = 1
            end = len(lines)
            for i in range(len(lines) - 1, 0, -1):
                if lines[i].strip() == "```":
                    end = i
                    break
            json_text = "\n".join(lines[start:end])

        try:
            data = json.loads(json_text)
        except json.JSONDecodeError as e:
            logger.error("JSON parse failed: %s\nRaw text (first 500 chars): %s", e, raw_text[:500])
            raise ValueError(f"Gemini レスポンスの JSON パースに失敗: {e}") from e

        segments = data.get("segments", [])
        title = data.get("title", f"{topic} 解説")
        total_duration = data.get("total_duration_estimate", 0)

        # segments を標準形式に正規化
        normalized: List[Dict[str, Any]] = []
        for i, seg in enumerate(segments):
            normalized.append({
                "id": seg.get("id", i + 1),
                "speaker": seg.get("speaker", "Host1"),
                "text": seg.get("text", ""),
                "key_points": seg.get("key_points", []),
                "duration_hint": seg.get("duration_hint", 15),
                "slide_suggestion": seg.get("slide_suggestion", ""),
            })

        # total_duration 推定 (duration_hint の合計、またはレスポンスの値)
        if total_duration <= 0 and normalized:
            total_duration = sum(s.get("duration_hint", 15) for s in normalized)

        return ScriptInfo(
            title=title,
            content=raw_text,
            segments=normalized,
            total_duration_estimate=total_duration,
            language=language,
            quality_score=0.8,  # 音声経由は高品質前提
            created_at=datetime.now(),
        )

    def _apply_speaker_mapping(
        self, script_info: ScriptInfo, mapping: Dict[str, str]
    ) -> ScriptInfo:
        """セグメント内の speaker 名を mapping で置換する。"""
        for seg in script_info.segments:
            original = seg.get("speaker", "")
            if original in mapping:
                seg["speaker"] = mapping[original]
        return script_info

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _save_intermediate_transcript(raw_text: str, save_path: Path) -> None:
        """中間テキストをファイルに保存。"""
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_text(raw_text, encoding="utf-8")
        logger.info("Intermediate transcript saved: %s", save_path)

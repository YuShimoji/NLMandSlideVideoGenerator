#!/usr/bin/env python3
"""
LLM連携トランスクリプト構造化モジュール

根本ワークフロー (DESIGN_FOUNDATIONS.md Section 0):
  NLM音声 → テキスト化 → **Gemini構造化** → CSV → YMM4

主要パス:
  structure_transcript()  — NLMトランスクリプトをspeaker/textセグメントに構造化 (メイン)
  generate_script_from_sources() — ソースから台本を生成 (フォールバック、NLMテキスト不在時)

ILLMProvider 抽象を通じて Gemini / OpenAI / Claude / DeepSeek を透過的に利用。
後方互換: api_key のみ指定時は create_llm_provider() で自動生成。
"""
import asyncio
import json
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from dataclasses import dataclass

from core.utils.logger import logger

if TYPE_CHECKING:
    from core.llm_provider import ILLMProvider

@dataclass
class GeminiResponse:
    """Gemini APIレスポンス"""
    content: str
    model: str
    usage_metadata: Dict[str, Any]
    safety_ratings: List[Dict[str, Any]]
    created_at: datetime

@dataclass
class ScriptInfo:
    """生成されたスクリプト情報"""
    title: str
    content: str
    segments: List[Dict[str, Any]]
    total_duration_estimate: float
    language: str
    quality_score: float
    created_at: datetime

class GeminiIntegration:
    """LLM連携トランスクリプト構造化クラス (マルチLLM対応)

    主要メソッド:
        structure_transcript()  — NLMテキスト → 構造化JSON (メインパス)
        generate_script_from_sources() — ソース → 台本生成 (フォールバック)
        generate_slide_content()  — 台本 → スライド内容

    DESIGN_FOUNDATIONS準拠: Geminiは「構造化」が主責務。台本「生成」はフォールバック。
    """

    # モデルフォールバックチェーン (gemini-2.5-flash を全用途で使用)
    DEFAULT_MODELS = ["gemini-2.5-flash"]

    # プリセットディレクトリのデフォルトパス
    PRESETS_DIR = Path(__file__).resolve().parent.parent.parent / "config" / "script_presets"

    def __init__(
        self,
        api_key: str = "",
        model_name: str | None = None,
        llm_provider: Optional["ILLMProvider"] = None,
    ):
        self.api_key = api_key
        self.model_name: str = model_name or os.environ.get("GEMINI_MODEL") or self.DEFAULT_MODELS[0]
        self.fallback_models = [m for m in self.DEFAULT_MODELS if m != self.model_name]
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.request_count = 0
        self.max_requests_per_minute = 60
        self._presets_cache: Dict[str, Dict[str, Any]] = {}
        self.fallback_used: bool = False
        self.actual_provider: str = ""

        # ILLMProvider: 外部注入 or api_key から自動生成
        if llm_provider is not None:
            self._llm_provider: Optional["ILLMProvider"] = llm_provider
            self.model_name = llm_provider.model_name
        elif api_key:
            try:
                from core.llm_provider import create_llm_provider
                self._llm_provider = create_llm_provider(api_key=api_key)
            except Exception:
                self._llm_provider = None
        else:
            self._llm_provider = None

    def load_preset(self, style: str = "default") -> Dict[str, Any]:
        """スクリプトスタイルプリセットを読み込む (SP-036)"""
        if style in self._presets_cache:
            return self._presets_cache[style]

        preset_path = self.PRESETS_DIR / f"{style}.json"
        if not preset_path.exists():
            available = [p.stem for p in self.PRESETS_DIR.glob("*.json")] if self.PRESETS_DIR.exists() else []
            raise ValueError(f"Unknown style preset '{style}'. Available: {available}")

        with open(preset_path, "r", encoding="utf-8") as f:
            preset: Dict[str, Any] = json.load(f)

        self._presets_cache[style] = preset
        logger.info(f"Script preset loaded: {preset.get('display_name', style)}")
        return preset

    def list_presets(self) -> List[Dict[str, str]]:
        """利用可能なプリセット一覧を返す"""
        if not self.PRESETS_DIR.exists():
            return []
        result = []
        for p in sorted(self.PRESETS_DIR.glob("*.json")):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                result.append({"name": p.stem, "display_name": data.get("display_name", p.stem)})
            except (json.JSONDecodeError, OSError):
                pass
        return result

    async def generate_script_from_sources(
        self,
        sources: List[Dict[str, Any]],
        topic: str,
        target_duration: float = 300.0,
        language: str = "ja",
        style: str = "default",
        speaker_mapping: Optional[Dict[str, str]] = None,
    ) -> ScriptInfo:
        """ソースから台本を生成 (フォールバックパス)。

        DESIGN_FOUNDATIONS準拠: NotebookLMトランスクリプトが得られない場合にのみ使用。
        品質はNotebookLM経由のstructure_transcript()より劣る。
        メインパスは structure_transcript() を使用すること。
        """
        try:
            logger.info(f"Gemini APIでスクリプト生成開始: {topic} (style={style})")

            # プロンプト構築
            prompt = self._build_script_prompt(
                sources, topic, target_duration, language,
                style=style, speaker_mapping=speaker_mapping,
            )

            # Gemini API呼び出し
            response = await self._call_gemini_api(prompt)

            # レスポンス解析
            script_info = await self._parse_script_response(response, topic, language)

            logger.info(f"スクリプト生成完了: {len(script_info.segments)}セグメント")
            return script_info

        except asyncio.CancelledError:
            raise
        except (OSError, AttributeError, TypeError, ValueError, RuntimeError) as e:
            logger.error(f"スクリプト生成失敗: {e}")
            raise
        except Exception as e:
            logger.error(f"スクリプト生成失敗: {e}")
            raise

    def _build_script_prompt(
        self,
        sources: List[Dict[str, Any]],
        topic: str,
        target_duration: float,
        language: str,
        style: str = "default",
        speaker_mapping: Optional[Dict[str, str]] = None,
    ) -> str:
        """スクリプト生成用プロンプトを構築 (SP-036: プリセット駆動)"""

        # プリセット読み込み (失敗時はデフォルトにフォールバック)
        try:
            preset = self.load_preset(style)
        except (ValueError, OSError):
            logger.warning(f"Preset '{style}' not found, falling back to built-in default")
            preset = {}

        # ソース情報をまとめる
        sources_text = ""
        for i, source in enumerate(sources, 1):
            sources_text += f"""
ソース{i}: {source.get('title', 'タイトル不明')}
URL: {source.get('url', 'URL不明')}
内容: {source.get('content_preview', 'プレビューなし')}
関連性: {source.get('relevance_score', 0.0):.2f}
信頼性: {source.get('reliability_score', 0.0):.2f}
---
"""

        # 言語設定
        lang_instruction = "日本語" if language == "ja" else "英語"

        # プリセットからセグメント密度を取得
        segment_density = preset.get("segment_density", {})
        avg_seconds = preset.get("avg_segment_seconds", {})

        # duration の閾値キーを文字列で検索 (プリセットのキーは文字列)
        duration_key = str(300)
        for threshold in ["300", "900", "1800", "3600"]:
            if target_duration <= int(threshold):
                duration_key = threshold
                break
        else:
            duration_key = "3600"

        segment_count_hint = segment_density.get(duration_key, "20-30")
        avg_segment_sec = avg_seconds.get(duration_key, 55)

        # プリセットから各フィールドを取得
        role = preset.get("role", "あなたはYouTube解説動画のスクリプト作成の専門家です。")
        tone = preset.get("tone", "分かりやすい話し言葉")
        structure = preset.get("structure", ["導入", "本論", "まとめ"])
        requirements = preset.get("requirements", [
            "視聴者が理解しやすい構成にしてください",
            "話し言葉で自然な文体にしてください",
            "重要なポイントは強調してください",
        ])
        speakers = preset.get("speakers", {})
        speaker_names = speakers.get("default_names", ["Host"])
        speaker_style = speakers.get("style", "")

        # 構成パターンの文字列化
        structure_text = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(structure))

        # 要件の文字列化 (プリセット要件 + 共通要件)
        common_reqs = [
            f"目安時間: {target_duration/60:.1f}分（約{int(target_duration)}秒）",
            f"セグメント数目安: {segment_count_hint}個（各セグメント{avg_segment_sec}秒前後）",
            "各セグメントの content は50-150文字程度の短い発話にしてください。1つの発話で1つのポイントだけを伝えてください",
            "対談形式の場合、テンポよく話者が交互に入れ替わるようにしてください。長いモノローグは避けてください",
            "冒頭の最初のセグメントには必ずフック（この動画で分かること、意外な事実、問いかけ等）を入れてください",
            "ソースを引用する際は「ソース1」「ソース3」のようなリテラル番号ではなく、「最近の調査によると」「専門家の分析では」等の自然な言い回しを使ってください",
            "key_points はスライド画像検索に使える具体的なキーワードを含めてください",
        ]
        all_reqs = requirements + common_reqs
        reqs_text = "\n".join(f"{i+1}. {r}" for i, r in enumerate(all_reqs))

        # speaker_mapping 適用: プリセットの話者名を実際の名前に変換
        if speaker_mapping:
            speaker_names = [speaker_mapping.get(n, n) for n in speaker_names]

        # 話者情報の構築
        if len(speaker_names) == 1:
            speaker_instruction = f"話者は「{speaker_names[0]}」の1名です。"
            speaker_example = speaker_names[0]
        else:
            speaker_list = "、".join(f"「{n}」" for n in speaker_names)
            speaker_instruction = f"話者は{speaker_list}の{len(speaker_names)}名です。"
            if speaker_style:
                speaker_instruction += f" {speaker_style}で進行してください。"
            speaker_example = speaker_names[0]

        # プロンプト構築
        prompt = f"""
{role}
以下の情報を基に、{target_duration/60:.1f}分程度の動画用スクリプトを{lang_instruction}で作成してください。

【トーン】
{tone}

【トピック】
{topic}

【参考ソース】
{sources_text}

【構成パターン】
{structure_text}

【話者】
{speaker_instruction}

【重要な制約】
- 1つのセグメントには必ず1人の話者のみを含めてください。複数人の発話を1セグメントに混在させないでください。
- 対談形式の場合、話者が交互に入れ替わる形で複数セグメントに分割してください。
- 各セグメントの "speaker" フィールドには、上記の話者名をそのまま使用してください。
- セグメントの "content" フィールドには、そのspeakerの発話のみを含めてください。他の話者の名前や発話を本文中に含めないでください。

【要件】
{reqs_text}

【出力形式】
以下のJSON形式で出力してください：

{{
  "title": "動画タイトル",
  "segments": [
    {{
      "section": "セクション名",
      "content": "この話者が話す内容のみ（他の話者の発話は含めない）",
      "duration_estimate": {avg_segment_sec}.0,
      "key_points": ["重要ポイント1", "重要ポイント2"],
      "speaker": "{speaker_example}"
    }}
  ],
  "total_duration_estimate": {target_duration},
  "language": "{language}"
}}
"""
        return prompt

    async def _call_llm_provider(self, prompt: str) -> GeminiResponse:
        """ILLMProvider 経由でテキスト生成を試行。"""
        assert self._llm_provider is not None
        text = await self._llm_provider.generate_text(prompt)
        if not text:
            raise RuntimeError("LLM provider returned empty response")
        self.request_count += 1
        return GeminiResponse(
            content=text,
            model=self._llm_provider.model_name,
            usage_metadata={},
            safety_ratings=[],
            created_at=datetime.now(),
        )

    async def _call_gemini_api(self, prompt: str) -> GeminiResponse:
        """LLM API を呼び出し（プロバイダー抽象 + モックフォールバック）"""
        try:
            # レート制限チェック
            await self._check_rate_limit()

            # ILLMProvider 経由の呼び出し
            if self._llm_provider is not None:
                try:
                    response = await self._call_llm_provider(prompt)
                    self.fallback_used = False
                    self.actual_provider = self._llm_provider.model_name
                    return response
                except ImportError as e:
                    logger.warning(f"LLM SDK未インストール: {e}")
                    self.fallback_used = True
                except Exception as e:
                    err_str = str(e).lower()
                    is_quota = "429" in err_str or ("resource" in err_str and "exhaust" in err_str)
                    if is_quota:
                        logger.warning(f"LLM クォータ超過、モックへフォールバック: {e}")
                    else:
                        logger.warning(f"LLM API呼び出し失敗、モックへフォールバック: {e}")
                    self.fallback_used = True

            # モック実装（フォールバック）— Host1/Host2対話形式でYMM4 speaker_mapping互換
            self.fallback_used = True
            self.actual_provider = "mock"
            await asyncio.sleep(0.5)
            # プロンプトからトピック名を抽出
            import re
            topic_match = re.search(r"【トピック】\s*\n(.+?)(?:\n|$)", prompt)
            mock_topic = topic_match.group(1).strip() if topic_match else "最新技術動向"
            mock_content = self._build_mock_content(mock_topic)

            mock_response = GeminiResponse(
                content=json.dumps(mock_content, ensure_ascii=False, indent=2),
                model=self.model_name,
                usage_metadata={"prompt_tokens": 1200, "completion_tokens": 800},
                safety_ratings=[{"category": "HARM_CATEGORY_HARASSMENT", "probability": "NEGLIGIBLE"}],
                created_at=datetime.now()
            )

            self.request_count += 1
            return mock_response

        except asyncio.CancelledError:
            raise
        except (OSError, AttributeError, TypeError, ValueError, RuntimeError) as e:
            logger.error(f"LLM API呼び出し失敗: {e}")
            raise
        except Exception as e:
            logger.error(f"LLM API呼び出し失敗: {e}")
            raise

    @staticmethod
    def _extract_json_from_response(text: str) -> str:
        """GeminiレスポンスからJSON部分を抽出。

        Gemini APIはMarkdownコードブロック (```json ... ```) でJSONを返す場合がある。
        """
        import re
        # ```json ... ``` パターンを検出
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
        if match:
            return match.group(1).strip()
        # そのままJSONとして試行
        return text.strip()

    async def _parse_script_response(
        self,
        response: GeminiResponse,
        topic: str,
        language: str
    ) -> ScriptInfo:
        """Gemini APIレスポンスを解析してScriptInfoに変換"""
        try:
            # JSONレスポンスを解析 (Markdownコードブロック対応)
            cleaned = self._extract_json_from_response(response.content)
            content_data = json.loads(cleaned)

            # セグメント情報を構築
            segments = []
            total_duration = 0.0

            for segment_data in content_data.get("segments", []):
                segment = {
                    "section": segment_data.get("section", ""),
                    "content": segment_data.get("content", ""),
                    "duration_estimate": segment_data.get("duration_estimate", 30.0),
                    "key_points": segment_data.get("key_points", [])
                }
                segments.append(segment)
                total_duration += segment["duration_estimate"]

            # 品質スコアを計算（セグメント数、内容の長さ、キーポイントの数などから算出）
            quality_score = self._calculate_quality_score(segments, content_data)

            script_info = ScriptInfo(
                title=content_data.get("title", topic),
                content=response.content,
                segments=segments,
                total_duration_estimate=total_duration,
                language=language,
                quality_score=quality_score,
                created_at=response.created_at
            )

            return script_info

        except json.JSONDecodeError as e:
            logger.error(f"JSONレスポンス解析失敗: {e}")
            raise
        except (KeyError, AttributeError, TypeError, ValueError, RuntimeError) as e:
            logger.error(f"スクリプトレスポンス解析失敗: {e}")
            raise
        except Exception as e:
            logger.error(f"スクリプトレスポンス解析失敗: {e}")
            raise

    def _calculate_quality_score(self, segments: List[Dict], content_data: Dict) -> float:
        """スクリプトの品質スコアを計算"""
        score = 0.0

        # セグメント数の評価（3以上あれば妥当）
        segment_count = len(segments)
        if segment_count >= 3:
            score += 0.3
        elif segment_count > 0:
            score += 0.1

        # 各セグメントの内容長評価
        avg_content_length = sum(len(seg.get("content", "")) for seg in segments) / max(len(segments), 1)
        if 50 <= avg_content_length <= 300:
            score += 0.3
        elif avg_content_length > 0:
            score += 0.1

        # キーポイントの存在評価
        total_key_points = sum(len(seg.get("key_points", [])) for seg in segments)
        if total_key_points >= len(segments):  # セグメントあたり平均1個以上
            score += 0.2

        # タイトルの存在評価
        if content_data.get("title") and len(content_data["title"]) > 5:
            score += 0.2

        return min(score, 1.0)

    @staticmethod
    def _build_mock_content(topic: str) -> dict:
        """トピック反映型モック台本を生成。Gemini不通時のフォールバック。"""
        return {
            "title": f"{topic} - 完全解説",
            "segments": [
                {
                    "section": "導入",
                    "content": f"こんにちは。今日は{topic}について、最新の動向を詳しく解説していきます。この分野は近年急速に発展しており、注目すべき変化が起きています。",
                    "duration_estimate": 25.0,
                    "key_points": [topic, "最新動向"],
                    "speaker": "Host1",
                },
                {
                    "section": "背景と現状",
                    "content": f"{topic}の背景を見ていきましょう。技術の進歩により、従来は困難だった課題の解決が可能になりつつあります。特に近年の研究成果は目覚ましいものがあります。",
                    "duration_estimate": 45.0,
                    "key_points": [f"{topic}の背景", "技術進歩", "研究成果"],
                    "speaker": "Host2",
                },
                {
                    "section": "主要な展開",
                    "content": f"{topic}における主要な展開について説明します。実用化に向けた取り組みが加速しており、産業界でも大きな関心を集めています。",
                    "duration_estimate": 40.0,
                    "key_points": [f"{topic}の展開", "実用化", "産業応用"],
                    "speaker": "Host1",
                },
                {
                    "section": "課題と展望",
                    "content": f"{topic}にはまだいくつかの課題も残されています。しかし、研究者や企業の努力により、これらの課題は着実に解決に向かっています。",
                    "duration_estimate": 50.0,
                    "key_points": [f"{topic}の課題", "解決への取り組み"],
                    "speaker": "Host2",
                },
                {
                    "section": "まとめ",
                    "content": f"以上、{topic}について解説しました。この分野は今後もさらなる発展が期待されます。引き続き注目していきましょう。",
                    "duration_estimate": 30.0,
                    "key_points": [f"{topic}の将来", "今後の展望"],
                    "speaker": "Host1",
                },
            ],
            "total_duration_estimate": 190.0,
            "language": "ja",
        }

    # -- 最小文字数: これ未満だと構造化に十分な情報がない --
    MIN_TRANSCRIPT_LENGTH = 50
    # -- 最大文字数: Gemini コンテキスト窓に収めるための安全上限 --
    MAX_TRANSCRIPT_LENGTH = 500_000

    async def structure_transcript(
        self,
        transcript_text: str,
        topic: str,
        target_duration: float = 300.0,
        language: str = "ja",
        style: str = "default",
        speaker_mapping: Optional[Dict[str, str]] = None,
    ) -> ScriptInfo:
        """NotebookLMトランスクリプトを構造化してScriptInfoに変換。

        根本ワークフロー (NLM音声→テキスト→Gemini構造化) の中核メソッド。
        台本を「生成」するのではなく、既存の対話テキストを
        speaker/text のセグメントに「構造化」する。

        Args:
            transcript_text: NotebookLMからのテキスト（文字起こし全文）
            topic: 動画のトピック名
            target_duration: 目標動画尺（秒）
            language: 出力言語 ("ja" / "en")
            style: スクリプトスタイルプリセット名
            speaker_mapping: 話者名の置換マッピング

        Returns:
            ScriptInfo: 構造化されたセグメント群

        Raises:
            ValueError: transcript_text が空または短すぎる場合
        """
        # 入力バリデーション
        if not transcript_text or not transcript_text.strip():
            raise ValueError("transcript_text が空です。NotebookLMのテキスト出力を確認してください。")

        cleaned = transcript_text.strip()
        if len(cleaned) < self.MIN_TRANSCRIPT_LENGTH:
            raise ValueError(
                f"transcript_text が短すぎます ({len(cleaned)}文字)。"
                f"最低{self.MIN_TRANSCRIPT_LENGTH}文字のテキストが必要です。"
            )

        if len(cleaned) > self.MAX_TRANSCRIPT_LENGTH:
            logger.warning(
                f"transcript_text が長大です ({len(cleaned)}文字)。"
                f"先頭{self.MAX_TRANSCRIPT_LENGTH}文字に切り詰めます。"
            )
            cleaned = cleaned[: self.MAX_TRANSCRIPT_LENGTH]

        logger.info(
            f"トランスクリプト構造化開始: {topic} "
            f"(style={style}, {len(cleaned)}文字, 目標{target_duration/60:.1f}分)"
        )

        prompt = self._build_structure_prompt(
            cleaned, topic, target_duration, language,
            style=style, speaker_mapping=speaker_mapping,
        )

        try:
            response = await self._call_gemini_api(prompt)
            script_info = await self._parse_script_response(response, topic, language)
        except json.JSONDecodeError as e:
            logger.error(f"構造化レスポンスのJSON解析に失敗: {e}")
            raise
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"トランスクリプト構造化に失敗: {e}")
            raise

        # 構造化結果のバリデーション
        if not script_info.segments:
            logger.warning("構造化結果のセグメントが0件です。元テキストの形式を確認してください。")

        logger.info(
            f"トランスクリプト構造化完了: {len(script_info.segments)}セグメント, "
            f"推定{script_info.total_duration_estimate/60:.1f}分"
        )
        return script_info

    def _build_structure_prompt(
        self,
        transcript_text: str,
        topic: str,
        target_duration: float,
        language: str,
        style: str = "default",
        speaker_mapping: Optional[Dict[str, str]] = None,
    ) -> str:
        """トランスクリプト構造化用プロンプトを構築。

        generate用プロンプトとの違い:
        - ソース情報ではなく、対話テキスト全文を入力とする
        - 「生成」ではなく「構造化」(話者分離+セグメント分割)を指示する
        - 元テキストの内容・表現をできるだけ維持する
        """
        try:
            preset = self.load_preset(style)
        except (ValueError, OSError):
            logger.warning(f"Preset '{style}' not found, falling back to built-in default")
            preset = {}

        lang_instruction = "日本語" if language == "ja" else "英語"

        # プリセットからセグメント密度を取得
        segment_density = preset.get("segment_density", {})
        avg_seconds = preset.get("avg_segment_seconds", {})

        duration_key = str(300)
        for threshold in ["300", "900", "1800", "3600"]:
            if target_duration <= int(threshold):
                duration_key = threshold
                break
        else:
            duration_key = "3600"

        segment_count_hint = segment_density.get(duration_key, "20-30")
        avg_segment_sec = avg_seconds.get(duration_key, 55)

        speakers = preset.get("speakers", {})
        speaker_names = speakers.get("default_names", ["Host1", "Host2"])
        if speaker_mapping:
            speaker_names = [speaker_mapping.get(n, n) for n in speaker_names]

        speaker_list = "、".join(f"「{n}」" for n in speaker_names)
        speaker_example = speaker_names[0]

        prompt = f"""あなたはNotebookLMの対話形式トランスクリプトを、動画制作用の構造化JSONに変換する専門家です。

以下の対話テキストを解析し、{lang_instruction}の動画用スクリプトJSONに構造化してください。

【重要: これは「生成」ではなく「構造化」タスクです】
- 元テキストの内容・表現・情報をできるだけそのまま維持してください
- 話者の発話を分離し、セグメントに分割してください
- 独自の内容を追加しないでください
- 元テキストにない情報を捏造しないでください

【トピック】
{topic}

【対話テキスト (NotebookLMトランスクリプト)】
{transcript_text}

【構造化の指示】
1. 話者を識別し、{speaker_list}に割り当ててください
   - 2名の対話形式が一般的です
   - 話者が明示されていない場合は文脈から推定してください
2. 対話を意味のあるセグメントに分割してください
   - セグメント数目安: {segment_count_hint}個
   - 各セグメント: {avg_segment_sec}秒前後 (50-150文字程度)
3. 各セグメントにセクション名とkey_pointsを付与してください
   - key_pointsはスライド画像検索に使える具体的なキーワード

【制約】
- 1セグメント = 1話者の発話のみ
- セグメントの content に他の話者の発話を含めない
- 元テキストの論理構造 (導入→本論→まとめ等) を維持する
- 目安時間: {target_duration/60:.1f}分（約{int(target_duration)}秒）

【出力形式】
以下のJSON形式で出力してください：

{{
  "title": "動画タイトル (元テキストの主題から生成)",
  "segments": [
    {{
      "section": "セクション名",
      "content": "この話者の発話内容 (元テキストからの抽出・整形)",
      "duration_estimate": {avg_segment_sec}.0,
      "key_points": ["キーワード1", "キーワード2"],
      "speaker": "{speaker_example}"
    }}
  ],
  "total_duration_estimate": {target_duration},
  "language": "{language}"
}}
"""
        return prompt

    async def _check_rate_limit(self):
        """レート制限をチェック"""
        if self.request_count >= self.max_requests_per_minute:
            logger.warning("レート制限に達しました。1分間待機します...")
            await asyncio.sleep(60)
            self.request_count = 0

    async def generate_slide_content(
        self,
        script_info: ScriptInfo,
        max_slides: int = 10
    ) -> List[Dict[str, Any]]:
        """スクリプトからスライド内容を生成"""
        try:
            logger.info("スライド内容生成開始")

            prompt = f"""
以下のスクリプトを基に、プレゼンテーション用のスライド内容を生成してください。

【スクリプト】
{script_info.content}

【要件】
1. 最大{max_slides}枚のスライドを作成
2. 各スライドには簡潔なタイトルと要点を記載
3. 視覚的に理解しやすい構成にする
4. 箇条書きを効果的に使用する

【出力形式】
以下のJSON形式で出力してください：

{{
  "slides": [
    {{
      "slide_number": 1,
      "title": "スライドタイトル",
      "content": "スライド内容（箇条書き可）",
      "layout": "title_slide|content_slide|conclusion_slide",
      "duration": 15.0
    }}
  ]
}}
"""

            response = await self._call_gemini_api(prompt)
            slide_data = json.loads(response.content)

            logger.info(f"スライド内容生成完了: {len(slide_data.get('slides', []))}枚")
            slides: list = slide_data.get("slides", [])
            return list(slides)

        except asyncio.CancelledError:
            raise
        except (json.JSONDecodeError, OSError, AttributeError, TypeError, ValueError, RuntimeError) as e:
            logger.error(f"スライド内容生成失敗: {e}")
            raise
        except Exception as e:
            logger.error(f"スライド内容生成失敗: {e}")
            raise

    async def generate_thumbnail_copy(
        self,
        script_info: "ScriptInfo",
        language: str = "ja",
    ) -> Dict[str, Any]:
        """台本からサムネイル用フック文言を自動生成する (SP-037 Phase 4)。

        成功パターンのフック構文 (thumbnail_pattern_analysis.md Section 2.3) を
        プロンプトに組み込み、YouTube解説動画の「売れるサムネイル」文言を生成する。

        Args:
            script_info: 台本データ (title, segments)
            language: 出力言語 ("ja" / "en")

        Returns:
            dict: {
                "main_text": "なぜXは...",       # 5-12文字のフック文言
                "sub_text": "驚きの理由が...",    # 10-25文字の補足
                "label": "ゆっくり解説",          # カテゴリラベル
                "suggested_pattern": "C",         # 推奨レイアウトパターン (A-E)
                "suggested_color": "dark_red",    # 推奨色彩プリセット名
            }
        """
        title = script_info.title
        # 最初の3セグメントからコンテキストを取得
        first_segments = script_info.segments[:3]
        segments_text = "\n".join(
            f"- [{seg.get('speaker', '?')}] {seg.get('content', '')}"
            for seg in first_segments
        )

        lang_instruction = "日本語" if language == "ja" else "英語"

        prompt = f"""あなたはYouTube解説動画のサムネイル文言を作成する専門家です。

以下の台本情報から、クリック率の高いサムネイル用テキストを{lang_instruction}で生成してください。

【台本タイトル】
{title}

【冒頭の内容】
{segments_text}

【サムネイル文言の成功パターン】
高再生数のYouTube解説動画サムネイルには、以下のフック構文が使われています:
- 「なぜX？」 — 知的好奇心の直接刺激
- 「Xの正体」 — 謎の提示+解決の約束
- 「Xの謎」 — ミステリー感の醸成
- 「絶対にX」 — 断定による強い主張
- 「衝撃のX」 — 感情的インパクト
- 「XX選」 — ボリュームの約束

【制約】
- main_text: 5-12文字。視覚的フック。モバイルでも読める大きさで表示される
- sub_text: 10-25文字。補足情報。クリック判断材料
- label: 「ゆっくり解説」「総集編」「緊急解説」等のカテゴリ表示
- suggested_pattern: A(中央テキスト), B(左画像+右テキスト), C(地図+矢印), D(縦分割), E(数字+リスト) から1つ選択
- suggested_color: dark_red(時事/ミステリー), dark_yellow(科学/雑学), map_white(地理), high_contrast(AI/テック), warm_alert(緊急ニュース) から1つ選択

【出力形式】
以下のJSON形式で出力してください:

{{
  "main_text": "フック文言",
  "sub_text": "補足説明",
  "label": "カテゴリ",
  "suggested_pattern": "A",
  "suggested_color": "dark_red"
}}
"""

        try:
            response = await self._call_gemini_api(prompt)
            cleaned = self._extract_json_from_response(response.content)
            result: Dict[str, Any] = json.loads(cleaned)

            # バリデーション
            required_keys = {"main_text", "sub_text", "label", "suggested_pattern", "suggested_color"}
            missing = required_keys - set(result.keys())
            if missing:
                logger.warning(f"サムネイル文言生成: 不足キー {missing}、デフォルト値で補完")
                defaults = {
                    "main_text": title[:12] if title else "解説",
                    "sub_text": "詳しく解説します",
                    "label": "ゆっくり解説",
                    "suggested_pattern": "A",
                    "suggested_color": "dark_red",
                }
                for key in missing:
                    result[key] = defaults[key]

            valid_patterns = {"A", "B", "C", "D", "E"}
            if result.get("suggested_pattern") not in valid_patterns:
                result["suggested_pattern"] = "A"

            valid_colors = {"dark_red", "dark_yellow", "map_white", "high_contrast", "warm_alert"}
            if result.get("suggested_color") not in valid_colors:
                result["suggested_color"] = "dark_red"

            logger.info(
                f"サムネイル文言生成完了: main='{result['main_text']}', "
                f"pattern={result['suggested_pattern']}, color={result['suggested_color']}"
            )
            return result

        except json.JSONDecodeError as e:
            logger.warning(f"サムネイル文言JSON解析失敗: {e}、デフォルト値を返します")
            return {
                "main_text": title[:12] if title else "解説",
                "sub_text": "最新情報を徹底解説",
                "label": "ゆっくり解説",
                "suggested_pattern": "A",
                "suggested_color": "dark_red",
            }
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"サムネイル文言生成失敗: {e}")
            raise

    def get_usage_stats(self) -> Dict[str, Any]:
        """使用統計を取得"""
        return {
            "request_count": self.request_count,
            "max_requests_per_minute": self.max_requests_per_minute,
            "remaining_requests": self.max_requests_per_minute - self.request_count,
            "model_name": self.model_name
        }

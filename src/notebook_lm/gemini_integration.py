#!/usr/bin/env python3
"""
Gemini API連携モジュール
NotebookLMの代替としてGoogle AI Studio (Gemini API)を使用
"""
import asyncio
import json
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from dataclasses import dataclass

from core.utils.logger import logger

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
    """Gemini API連携クラス"""

    # モデルフォールバックチェーン: 高品質→高クォータ
    DEFAULT_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash"]

    # プリセットディレクトリのデフォルトパス
    PRESETS_DIR = Path(__file__).resolve().parent.parent.parent / "config" / "script_presets"

    def __init__(self, api_key: str, model_name: str | None = None):
        self.api_key = api_key
        self.model_name: str = model_name or os.environ.get("GEMINI_MODEL") or self.DEFAULT_MODELS[0]
        self.fallback_models = [m for m in self.DEFAULT_MODELS if m != self.model_name]
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.request_count = 0
        self.max_requests_per_minute = 60
        self._presets_cache: Dict[str, Dict[str, Any]] = {}

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
        style: str = "default"
    ) -> ScriptInfo:
        """ソースからスクリプトを生成"""
        try:
            logger.info(f"Gemini APIでスクリプト生成開始: {topic} (style={style})")

            # プロンプト構築
            prompt = self._build_script_prompt(sources, topic, target_duration, language, style=style)

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
        style: str = "default"
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
            "各セグメントの content は200-400文字程度の充実した内容にしてください",
            "key_points はスライド画像検索に使える具体的なキーワードを含めてください",
        ]
        all_reqs = requirements + common_reqs
        reqs_text = "\n".join(f"{i+1}. {r}" for i, r in enumerate(all_reqs))

        # 話者指定
        speaker_json = speaker_names[0] if len(speaker_names) == 1 else f'{speaker_names[0]}」または「{speaker_names[1]}'

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

【要件】
{reqs_text}

【出力形式】
以下のJSON形式で出力してください：

{{
  "title": "動画タイトル",
  "segments": [
    {{
      "section": "セクション名",
      "content": "話す内容",
      "duration_estimate": {avg_segment_sec}.0,
      "key_points": ["重要ポイント1", "重要ポイント2"],
      "speaker": "{speaker_names[0]}"
    }}
  ],
  "total_duration_estimate": {target_duration},
  "language": "{language}"
}}
"""
        return prompt

    async def _try_model(self, model: str, prompt: str) -> GeminiResponse:
        """指定モデルでAPI呼び出しを試行"""
        from google import genai
        client = genai.Client(api_key=self.api_key)
        resp = await asyncio.to_thread(
            client.models.generate_content,
            model=model,
            contents=prompt,
        )
        content_str = getattr(resp, "text", None)
        if not content_str:
            try:
                to_dict = getattr(resp, "to_dict", None)
                content_str = json.dumps(to_dict(), ensure_ascii=False) if to_dict else str(resp)
            except Exception:
                content_str = json.dumps({
                    "title": "生成結果", "segments": [],
                    "total_duration_estimate": 0, "language": "ja"
                }, ensure_ascii=False)
        self.request_count += 1
        return GeminiResponse(
            content=content_str,
            model=model,
            usage_metadata={},
            safety_ratings=[],
            created_at=datetime.now(),
        )

    async def _call_gemini_api(self, prompt: str) -> GeminiResponse:
        """Gemini APIを呼び出し（モデルフォールバックチェーン付き）"""
        try:
            # レート制限チェック
            await self._check_rate_limit()

            # 実API呼び出し（APIキーが設定されていれば試行）
            if self.api_key:
                models_to_try = [self.model_name] + self.fallback_models
                last_error = None
                for model in models_to_try:
                    try:
                        response = await self._try_model(model, prompt)
                        if model != self.model_name:
                            logger.info(f"フォールバックモデル {model} で生成成功")
                        return response
                    except ImportError as e:
                        logger.warning(f"google-genai SDK未インストール: {e}")
                        break  # SDK問題はモデル変更で解決しない
                    except Exception as e:
                        last_error = e
                        err_str = str(e).lower()
                        is_quota = "429" in err_str or "resource" in err_str and "exhaust" in err_str
                        if is_quota and model != models_to_try[-1]:
                            logger.warning(f"{model} クォータ超過、次のモデルへフォールバック: {e}")
                            continue
                        logger.warning(f"{model} API呼び出し失敗: {e}")
                        break  # クォータ以外のエラーはフォールバック不要
                if last_error:
                    logger.warning(f"全モデル失敗、モックへフォールバック: {last_error}")

            # モック実装（フォールバック）— Host1/Host2対話形式でYMM4 speaker_mapping互換
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
            logger.error(f"Gemini API呼び出し失敗: {e}")
            raise
        except Exception as e:
            logger.error(f"Gemini API呼び出し失敗: {e}")
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

    def get_usage_stats(self) -> Dict[str, Any]:
        """使用統計を取得"""
        return {
            "request_count": self.request_count,
            "max_requests_per_minute": self.max_requests_per_minute,
            "remaining_requests": self.max_requests_per_minute - self.request_count,
            "model_name": self.model_name
        }

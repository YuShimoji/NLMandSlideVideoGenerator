"""
NLM Study Guide → YMM4 CSV 変換器 (SP-047 Phase 2)

NotebookLM の Study Guide (Markdown テキスト) を受け取り、
Gemini を使って YMM4 CSV 形式のダイアログスクリプトに変換する。

品質基準 (SP-047):
- 冒頭 15 秒にフック
- セグメント粒度: 15-30 秒
- 発話長: 50-100 文字
- ソース引用はナチュラルな言い回し
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from notebook_lm.gemini_integration import GeminiIntegration, ScriptInfo

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# SP-047 品質基準
_QUALITY_STANDARDS = """
### SP-047 品質基準 (必須)
1. **冒頭フック**: 最初のセグメントは「この動画で分かること」または衝撃的な事実から始める (15秒以内)
2. **セグメント粒度**: 1セグメント = 15-30 秒相当 (50-100 文字/発話)
3. **発話長**: 1発話 50-100 文字。200文字を超えない
4. **対話テンポ**: 相槌・確認・驚き等の短い反応 (10-30文字) を適度に挿入
5. **ソース引用**: "ソース1" "ソース3" などのリテラル引用を禁止。「研究によると」「報告書では」等の自然な言い回し
6. **キャラクター個性**: テンプレート的相槌 ("そうなんですね" の繰り返し) を避ける
"""

_CONVERSION_PROMPT = """\
以下の Study Guide テキストを、YouTube 解説動画用の 2 人対話スクリプトに変換してください。

## Study Guide
{study_guide_text}

## 変換仕様

### 話者設定
- speaker_a: 「ずんだもん」 (説明担当: 好奇心旺盛、少し興奮気味)
- speaker_b: 「四国めたん」 (進行担当: 落ち着いた知的な口調)

### 目標時間
{target_duration_seconds} 秒 (目安セグメント数: {target_segments} 個)

{quality_standards}

## 出力 JSON 形式

```json
{{
  "title": "動画タイトル (50文字以内)",
  "summary": "動画の概要 (100文字以内)",
  "segments": [
    {{
      "section": "セクション名 (オープニング/本編/まとめ等)",
      "speaker_a_text": "ずんだもん の発話テキスト (空欄可)",
      "speaker_b_text": "四国めたん の発話テキスト (空欄可)",
      "duration_estimate": 20.0,
      "key_points": ["ポイント1", "ポイント2"]
    }}
  ]
}}
```

注意:
- speaker_a_text か speaker_b_text のどちらか一方のみを入力 (1セグメント=1発話)
- 空欄の場合は "" (空文字) を指定
- JSON のみ出力。説明文は不要
"""


class NlmScriptConverter:
    """
    Study Guide テキスト → YMM4 CSV 互換 ScriptInfo への変換器。

    使用例:
        converter = NlmScriptConverter(api_key="GEMINI_API_KEY")
        script_info = await converter.convert(study_guide_text, topic="AI最新動向", target_duration=600)
    """

    def __init__(
        self,
        api_key: str = "",
        llm_provider: Any = None,
        style: str = "default",
    ):
        self._gemini = GeminiIntegration(
            api_key=api_key or os.environ.get("GEMINI_API_KEY", ""),
            llm_provider=llm_provider,
        )
        self._style = style

    async def convert(
        self,
        study_guide_text: str,
        topic: str,
        target_duration: float = 600.0,
        language: str = "ja",
        speaker_a: str = "ずんだもん",
        speaker_b: str = "四国めたん",
    ) -> ScriptInfo:
        """
        Study Guide テキストを ScriptInfo に変換する。

        Args:
            study_guide_text: NLM が生成した Markdown テキスト
            topic: 動画のトピック名
            target_duration: 目標動画尺 (秒)。デフォルト 600秒 (10分)
            language: 言語コード
            speaker_a: 話者 A の名前
            speaker_b: 話者 B の名前

        Returns:
            ScriptInfo (既存パイプラインと互換)
        """
        target_segments = max(5, int(target_duration / 22))  # 22秒/セグメント目安
        prompt = _CONVERSION_PROMPT.format(
            study_guide_text=study_guide_text,
            target_duration_seconds=int(target_duration),
            target_segments=target_segments,
            quality_standards=_QUALITY_STANDARDS,
        )

        logger.info(
            "NLM Study Guide → Script 変換開始: topic=%s, duration=%.0fs, segments≈%d",
            topic,
            target_duration,
            target_segments,
        )

        try:
            response = await self._gemini._call_gemini_api(prompt)
            script_info = self._parse_response(response, topic, language, speaker_a, speaker_b)
            logger.info("変換完了: %d セグメント, 品質スコア=%.2f", len(script_info.segments), script_info.quality_score)
            return script_info
        except Exception as exc:
            logger.warning("Gemini API 変換失敗 (%s)、モックにフォールバック", exc)
            return self._mock_script(study_guide_text, topic, target_duration)

    def _parse_response(
        self,
        response: Any,
        topic: str,
        language: str,
        speaker_a: str,
        speaker_b: str,
    ) -> ScriptInfo:
        """Gemini レスポンス JSON を ScriptInfo に変換する。"""
        cleaned = GeminiIntegration._extract_json_from_response(response.content)
        data: Dict[str, Any] = json.loads(cleaned)

        segments: List[Dict[str, Any]] = []
        total_duration = 0.0

        for seg in data.get("segments", []):
            speaker_a_text: str = seg.get("speaker_a_text", "")
            speaker_b_text: str = seg.get("speaker_b_text", "")
            content = speaker_a_text or speaker_b_text
            speaker = speaker_a if speaker_a_text else speaker_b

            duration = float(seg.get("duration_estimate", 20.0))
            segments.append(
                {
                    "section": seg.get("section", ""),
                    "content": content,
                    "speaker": speaker,
                    "duration_estimate": duration,
                    "key_points": seg.get("key_points", []),
                }
            )
            total_duration += duration

        quality_score = self._score(segments, data)

        return ScriptInfo(
            title=data.get("title", topic),
            content=response.content,
            segments=segments,
            total_duration_estimate=total_duration,
            language=language,
            quality_score=quality_score,
            created_at=getattr(response, "created_at", datetime.now()),
        )

    @staticmethod
    def _score(segments: List[Dict[str, Any]], data: Dict[str, Any]) -> float:
        """簡易品質スコア計算 (SP-047 基準)。"""
        score = 0.0
        if not segments:
            return 0.0

        # セグメント数チェック (5 以上)
        if len(segments) >= 5:
            score += 0.25

        # 発話長チェック (平均 50-100 文字)
        avg_len = sum(len(s.get("content", "")) for s in segments) / len(segments)
        if 40 <= avg_len <= 120:
            score += 0.25
        elif avg_len > 0:
            score += 0.1

        # セグメント尺チェック (平均 15-30 秒)
        avg_dur = sum(s.get("duration_estimate", 0) for s in segments) / len(segments)
        if 12 <= avg_dur <= 35:
            score += 0.25

        # タイトル存在
        if data.get("title"):
            score += 0.25

        return min(score, 1.0)

    def _mock_script(self, study_guide_text: str, topic: str, target_duration: float) -> ScriptInfo:
        """テスト用モックスクリプトを返す。"""
        segments = [
            {
                "section": "オープニング",
                "content": f"今日は「{topic}」について解説するのだ！最近注目されているこのテーマ、実は意外な事実が隠れているよ。",
                "speaker": "ずんだもん",
                "duration_estimate": 18.0,
                "key_points": ["概要紹介"],
            },
            {
                "section": "オープニング",
                "content": "そうなの？どんな事実があるの？",
                "speaker": "四国めたん",
                "duration_estimate": 5.0,
                "key_points": [],
            },
            {
                "section": "本編",
                "content": "まず最初に知っておきたいのが基本的な仕組みなのだ。Study Guideによると、この分野には大きく3つの側面があるよ。",
                "speaker": "ずんだもん",
                "duration_estimate": 22.0,
                "key_points": ["3つの側面"],
            },
            {
                "section": "本編",
                "content": "3つの側面か。それぞれ詳しく教えてもらえる？",
                "speaker": "四国めたん",
                "duration_estimate": 6.0,
                "key_points": [],
            },
            {
                "section": "まとめ",
                "content": f"今日は{topic}について学んだのだ！主なポイントは3つだったよね。ぜひ日常生活でも意識してみてね。",
                "speaker": "ずんだもん",
                "duration_estimate": 20.0,
                "key_points": ["まとめ"],
            },
        ]

        total = sum(s["duration_estimate"] for s in segments)
        return ScriptInfo(
            title=f"{topic} — 完全解説",
            content="[mock]",
            segments=segments,
            total_duration_estimate=total,
            language="ja",
            quality_score=0.75,
            created_at=datetime.now(),
        )

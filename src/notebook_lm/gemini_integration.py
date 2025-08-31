#!/usr/bin/env python3
"""
Gemini API連携モジュール
NotebookLMの代替としてGoogle AI Studio (Gemini API)を使用
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# SimpleLogger クラス
class SimpleLogger:
    @staticmethod
    def info(message: str):
        print(f"[INFO] {message}")
    
    @staticmethod
    def error(message: str):
        print(f"[ERROR] {message}")
    
    @staticmethod
    def warning(message: str):
        print(f"[WARNING] {message}")

logger = SimpleLogger()

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
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.model_name = "gemini-1.5-pro"
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.request_count = 0
        self.max_requests_per_minute = 60
        
    async def generate_script_from_sources(
        self, 
        sources: List[Dict[str, Any]], 
        topic: str,
        target_duration: float = 300.0,
        language: str = "ja"
    ) -> ScriptInfo:
        """ソースからスクリプトを生成"""
        try:
            logger.info(f"Gemini APIでスクリプト生成開始: {topic}")
            
            # プロンプト構築
            prompt = self._build_script_prompt(sources, topic, target_duration, language)
            
            # Gemini API呼び出し
            response = await self._call_gemini_api(prompt)
            
            # レスポンス解析
            script_info = await self._parse_script_response(response, topic, language)
            
            logger.info(f"スクリプト生成完了: {len(script_info.segments)}セグメント")
            return script_info
            
        except Exception as e:
            logger.error(f"スクリプト生成失敗: {e}")
            raise
    
    def _build_script_prompt(
        self, 
        sources: List[Dict[str, Any]], 
        topic: str,
        target_duration: float,
        language: str
    ) -> str:
        """スクリプト生成用プロンプトを構築"""
        
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
        
        # プロンプト構築
        prompt = f"""
あなたはYouTube解説動画のスクリプト作成の専門家です。
以下の情報を基に、{target_duration/60:.1f}分程度の解説動画用スクリプトを{lang_instruction}で作成してください。

【トピック】
{topic}

【参考ソース】
{sources_text}

【要件】
1. 視聴者が理解しやすい構成にしてください
2. 導入→本論→まとめの流れで構成してください
3. 各セクションに適切な見出しをつけてください
4. 話し言葉で自然な文体にしてください
5. 重要なポイントは強調してください
6. 目安時間: {target_duration/60:.1f}分（約{int(target_duration)}秒）

【出力形式】
以下のJSON形式で出力してください：

{{
  "title": "動画タイトル",
  "segments": [
    {{
      "section": "セクション名",
      "content": "話す内容",
      "duration_estimate": 30.0,
      "key_points": ["重要ポイント1", "重要ポイント2"]
    }}
  ],
  "total_duration_estimate": {target_duration},
  "language": "{language}"
}}
"""
        return prompt
    
    async def _call_gemini_api(self, prompt: str) -> GeminiResponse:
        """Gemini APIを呼び出し"""
        try:
            # レート制限チェック
            await self._check_rate_limit()
            
            # 実際のAPI呼び出しはここで実装
            # import google.generativeai as genai
            # genai.configure(api_key=self.api_key)
            # model = genai.GenerativeModel(self.model_name)
            # response = model.generate_content(prompt)
            
            # モック実装
            await asyncio.sleep(2)  # API呼び出し時間をシミュレート
            
            mock_content = {
                "title": "AI技術の最新動向 - 2024年版完全解説",
                "segments": [
                    {
                        "section": "導入",
                        "content": "こんにちは。今日は2024年におけるAI技術の最新動向について、詳しく解説していきます。人工知能の分野は日々進歩しており、特に生成AIの領域では革新的な変化が起きています。",
                        "duration_estimate": 25.0,
                        "key_points": ["2024年のAI動向", "生成AIの進歩"]
                    },
                    {
                        "section": "生成AIの進歩",
                        "content": "まず、生成AIの分野から見ていきましょう。大規模言語モデルの性能向上により、より自然で正確なテキスト生成が可能になりました。また、画像生成技術も大幅に改善され、商用利用も増加しています。",
                        "duration_estimate": 45.0,
                        "key_points": ["大規模言語モデル", "画像生成技術", "商用利用"]
                    },
                    {
                        "section": "機械学習の効率化",
                        "content": "次に、機械学習アルゴリズムの効率化について説明します。新しい最適化手法により、従来よりも少ない計算資源で高い性能を実現できるようになりました。これにより、より多くの企業がAI技術を導入しやすくなっています。",
                        "duration_estimate": 40.0,
                        "key_points": ["最適化手法", "計算効率", "企業導入"]
                    },
                    {
                        "section": "産業応用の拡大",
                        "content": "AI技術の産業応用も急速に拡大しています。製造業では品質管理の自動化、金融業ではリスク分析の高度化、医療分野では診断支援システムの導入が進んでいます。これらの応用により、業務効率の大幅な改善が実現されています。",
                        "duration_estimate": 50.0,
                        "key_points": ["製造業", "金融業", "医療分野", "業務効率化"]
                    },
                    {
                        "section": "まとめ",
                        "content": "以上、2024年のAI技術動向について解説しました。生成AI、機械学習の効率化、産業応用の拡大という3つの観点から見ると、AI技術は確実に私たちの生活と仕事を変革しています。今後もこの分野の発展に注目していきましょう。",
                        "duration_estimate": 30.0,
                        "key_points": ["技術変革", "生活への影響", "今後の展望"]
                    }
                ],
                "total_duration_estimate": 190.0,
                "language": "ja"
            }
            
            mock_response = GeminiResponse(
                content=json.dumps(mock_content, ensure_ascii=False, indent=2),
                model=self.model_name,
                usage_metadata={"prompt_tokens": 1200, "completion_tokens": 800},
                safety_ratings=[{"category": "HARM_CATEGORY_HARASSMENT", "probability": "NEGLIGIBLE"}],
                created_at=datetime.now()
            )
            
            self.request_count += 1
            return mock_response
            
        except Exception as e:
            logger.error(f"Gemini API呼び出し失敗: {e}")
            raise
    
    async def _parse_script_response(
        self, 
        response: GeminiResponse, 
        topic: str, 
        language: str
    ) -> ScriptInfo:
        """Gemini APIレスポンスを解析してScriptInfoに変換"""
        try:
            # JSONレスポンスを解析
            content_data = json.loads(response.content)
            
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
        except Exception as e:
            logger.error(f"スクリプトレスポンス解析失敗: {e}")
            raise
    
    def _calculate_quality_score(self, segments: List[Dict], content_data: Dict) -> float:
        """スクリプトの品質スコアを計算"""
        score = 0.0
        
        # セグメント数の評価（3-7セグメントが理想的）
        segment_count = len(segments)
        if 3 <= segment_count <= 7:
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
            return slide_data.get("slides", [])
            
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

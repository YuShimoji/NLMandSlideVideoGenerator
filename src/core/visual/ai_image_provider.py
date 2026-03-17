"""AI画像生成プロバイダー (SP-033 Phase 3)

Gemini Imagen API を使用して、台本セグメントに基づく
ユニークなイラスト・図解を自動生成する。
"""
from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..utils.logger import logger

# リトライ設定
_MAX_RETRIES = 3
_BACKOFF_BASE = 2.0

# Imagen モデル (Imagen 3 は廃止済み、Imagen 4 が現行)
_DEFAULT_MODEL = os.environ.get("IMAGEN_MODEL", "imagen-4.0-generate-001")


@dataclass
class GeneratedImage:
    """AI生成画像のメタデータ。"""

    prompt: str
    image_path: Optional[Path] = None
    mime_type: str = "image/png"
    enhanced_prompt: str = ""
    source: str = "ai"
    error: Optional[str] = None


class AIImageProvider:
    """Gemini Imagen APIを使用したAI画像生成。

    責務:
    1. 台本セグメントから画像プロンプトを生成
    2. Imagen API で画像を生成
    3. 生成画像をキャッシュディレクトリに保存
    4. 品質フィルター (RAIフィルタ検出)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        cache_dir: Optional[Path] = None,
        model: str = _DEFAULT_MODEL,
        aspect_ratio: str = "16:9",
    ) -> None:
        """
        Args:
            api_key: Gemini API キー。None時は環境変数を使用。
            cache_dir: 生成画像のキャッシュディレクトリ。
            model: Imagen モデル名。
            aspect_ratio: 生成画像のアスペクト比。
        """
        from config.settings import settings
        self.api_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        self.model = model
        self.aspect_ratio = aspect_ratio

        if cache_dir is None:
            cache_dir = Path(settings.STOCK_IMAGE_SETTINGS.get(
                "cache_dir", "data/stock_images"
            )) / "ai_generated"
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def generate_for_segments(
        self,
        segments: List[Dict[str, Any]],
        topic: str = "",
        style_hint: str = "clean, professional illustration for educational video",
    ) -> List[GeneratedImage]:
        """台本セグメント群から画像を一括生成する。

        Args:
            segments: 台本セグメント群。
            topic: 動画のトピック (プロンプト生成のコンテキスト)。
            style_hint: スタイル指示 (全プロンプトに付与)。

        Returns:
            セグメント順のGeneratedImageリスト。
        """
        if not self.api_key:
            logger.warning("GEMINI_API_KEY未設定。AI画像生成をスキップ。")
            return [GeneratedImage(prompt="", error="no_api_key") for _ in segments]

        results: List[GeneratedImage] = []
        for i, segment in enumerate(segments):
            prompt = self._build_prompt(segment, topic, style_hint)

            # キャッシュチェック
            cached = self._check_cache(prompt)
            if cached:
                logger.debug(f"セグメント{i}: キャッシュヒット")
                results.append(cached)
                continue

            # API呼び出し
            generated = self._generate_with_retry(prompt, segment_index=i)
            results.append(generated)

            # レート制限対策: セグメント間に短い待機
            if i < len(segments) - 1 and generated.image_path:
                time.sleep(0.5)

        success = sum(1 for r in results if r.image_path)
        logger.info(f"AI画像生成: {success}/{len(segments)}件成功")
        return results

    def generate_single(
        self,
        prompt: str,
    ) -> GeneratedImage:
        """単一プロンプトから画像を生成する。

        Args:
            prompt: 画像生成プロンプト。

        Returns:
            GeneratedImage。
        """
        if not self.api_key:
            return GeneratedImage(prompt=prompt, error="no_api_key")

        cached = self._check_cache(prompt)
        if cached:
            return cached

        return self._generate_with_retry(prompt)

    def _build_prompt(
        self,
        segment: Dict[str, Any],
        topic: str,
        style_hint: str,
    ) -> str:
        """セグメントから画像生成プロンプトを構築する。"""
        parts: List[str] = []

        # キーポイントがある場合はそれを主題に
        key_points = segment.get("key_points", [])
        section = segment.get("section", "")
        content = segment.get("content", "") or segment.get("text", "")

        if key_points:
            subject = ", ".join(key_points[:3])
        elif section:
            subject = section
        elif content:
            subject = content[:100]
        else:
            subject = topic or "abstract concept"

        # プロンプト構築
        if topic:
            parts.append(f"Topic: {topic}.")
        parts.append(f"Subject: {subject}.")
        if style_hint:
            parts.append(f"Style: {style_hint}.")
        parts.append("No text or watermarks in the image.")

        return " ".join(parts)

    def _generate_with_retry(
        self,
        prompt: str,
        segment_index: int = 0,
    ) -> GeneratedImage:
        """リトライ付きで画像を生成する。"""
        for attempt in range(_MAX_RETRIES):
            try:
                return self._call_api(prompt)
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    wait = _BACKOFF_BASE ** (attempt + 1)
                    logger.warning(
                        f"レート制限 (attempt {attempt + 1}/{_MAX_RETRIES}), "
                        f"{wait:.0f}秒待機: {e}"
                    )
                    time.sleep(wait)
                elif "400" in error_str:
                    # プロンプト問題 → リトライ不要
                    logger.warning(f"プロンプトエラー (segment {segment_index}): {e}")
                    return GeneratedImage(prompt=prompt, error=f"prompt_error: {e}")
                else:
                    if attempt < _MAX_RETRIES - 1:
                        time.sleep(_BACKOFF_BASE ** attempt)
                    else:
                        logger.warning(
                            f"AI画像生成失敗 (segment {segment_index}): {e}"
                        )
                        return GeneratedImage(prompt=prompt, error=str(e))

        return GeneratedImage(prompt=prompt, error="max_retries_exceeded")

    def _call_api(self, prompt: str) -> GeneratedImage:
        """Gemini Imagen API を呼び出す。"""
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self.api_key)

        response = client.models.generate_images(
            model=self.model,
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio=self.aspect_ratio,
                language="en",  # type: ignore[arg-type]
                safety_filter_level="BLOCK_MEDIUM_AND_ABOVE",  # type: ignore[arg-type]
                output_mime_type="image/png",
            ),
        )

        if not response.images:
            return GeneratedImage(prompt=prompt, error="no_images_returned")

        img = response.images[0]
        if img is None:
            return GeneratedImage(prompt=prompt, error="null_image_entry")

        # RAIフィルタチェック
        rai_reason = getattr(img, "rai_filtered_reason", None)
        if rai_reason:
            logger.warning(f"RAIフィルタ: {rai_reason}")
            return GeneratedImage(
                prompt=prompt,
                error=f"rai_filtered: {rai_reason}",
            )

        img_data = getattr(img, "image", None)
        if not img_data or not getattr(img_data, "image_bytes", None):
            return GeneratedImage(prompt=prompt, error="empty_image_data")

        # ファイル保存
        cache_key = hashlib.md5(prompt.encode()).hexdigest()[:12]
        file_path = self.cache_dir / f"ai_{cache_key}.png"
        file_path.write_bytes(img_data.image_bytes)

        enhanced = getattr(img, "enhanced_prompt", "") or ""

        logger.debug(f"AI画像生成成功: {file_path}")
        return GeneratedImage(
            prompt=prompt,
            image_path=file_path,
            enhanced_prompt=enhanced,
        )

    def _check_cache(self, prompt: str) -> Optional[GeneratedImage]:
        """キャッシュから画像を検索する。"""
        cache_key = hashlib.md5(prompt.encode()).hexdigest()[:12]
        file_path = self.cache_dir / f"ai_{cache_key}.png"
        if file_path.exists():
            return GeneratedImage(
                prompt=prompt,
                image_path=file_path,
                source="ai_cache",
            )
        return None

"""
ストック画像API統合モジュール (SP-033 Phase 2)

Pexels / Pixabay の無料APIからキーワード検索で画像を取得し、
スライド素材として利用可能な形式でダウンロード・キャッシュする。
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

import requests
from requests.exceptions import ConnectionError, HTTPError, Timeout

from config.settings import settings
from core.utils.logger import logger

# リトライ対象のHTTPステータスコード
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
_MAX_RETRIES = 3
_BACKOFF_BASE = 1.0  # 秒 (1, 2, 4 の指数バックオフ)


@dataclass
class StockImage:
    """ストック画像メタデータ。"""

    id: str
    url: str
    download_url: str
    width: int
    height: int
    photographer: str
    source: str  # "pexels" | "pixabay"
    alt_text: str = ""
    tags: List[str] = field(default_factory=list)
    local_path: Optional[Path] = None


class StockImageClient:
    """Pexels / Pixabay APIクライアント。

    優先順位:
    1. Pexels (高品質、200 req/hour 無料)
    2. Pixabay (大量、5000 req/hour 無料)
    3. キーなし → 空リスト返却 (エラーにしない)

    エラーハンドリング:
    - 5xx / 429: 指数バックオフでリトライ (最大3回)
    - 401 / 403: APIキー無効としてログし、リトライしない
    - 接続エラー / タイムアウト: リトライ (最大3回)
    """

    PEXELS_BASE = "https://api.pexels.com/v1"
    PIXABAY_BASE = "https://pixabay.com/api/"

    def __init__(
        self,
        pexels_api_key: Optional[str] = None,
        pixabay_api_key: Optional[str] = None,
        cache_dir: Optional[Path] = None,
    ) -> None:
        self.pexels_api_key = pexels_api_key or settings.STOCK_IMAGE_SETTINGS.get("pexels_api_key", "")
        self.pixabay_api_key = pixabay_api_key or settings.STOCK_IMAGE_SETTINGS.get("pixabay_api_key", "")
        self.cache_dir = cache_dir or (settings.DATA_DIR / "stock_images")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "NLMSlideVideoGenerator/1.0",
        })

        self._last_request_time: float = 0
        self._min_interval: float = 0.5  # 秒

    def validate_api_keys(self) -> Dict[str, bool]:
        """APIキーの有効性を事前検証する。

        Returns:
            {"pexels": True/False, "pixabay": True/False}
        """
        result: Dict[str, bool] = {"pexels": False, "pixabay": False}

        if self.pexels_api_key:
            try:
                self._rate_limit()
                resp = self.session.get(
                    f"{self.PEXELS_BASE}/search",
                    headers={"Authorization": self.pexels_api_key},
                    params={"query": "test", "per_page": 1},
                    timeout=10,
                )
                if resp.status_code == 200:
                    result["pexels"] = True
                    logger.info("Pexels APIキー検証OK")
                elif resp.status_code in (401, 403):
                    logger.error(f"Pexels APIキー無効 (HTTP {resp.status_code})")
                else:
                    logger.warning(f"Pexels APIキー検証: HTTP {resp.status_code}")
            except (ConnectionError, Timeout) as e:
                logger.warning(f"Pexels APIキー検証: 接続失敗 - {e}")

        if self.pixabay_api_key:
            try:
                self._rate_limit()
                resp = self.session.get(
                    self.PIXABAY_BASE,
                    params={"key": self.pixabay_api_key, "q": "test", "per_page": 3},
                    timeout=10,
                )
                if resp.status_code == 200:
                    result["pixabay"] = True
                    logger.info("Pixabay APIキー検証OK")
                elif resp.status_code in (401, 403):
                    logger.error(f"Pixabay APIキー無効 (HTTP {resp.status_code})")
                else:
                    logger.warning(f"Pixabay APIキー検証: HTTP {resp.status_code}")
            except (ConnectionError, Timeout) as e:
                logger.warning(f"Pixabay APIキー検証: 接続失敗 - {e}")

        return result

    def search(
        self,
        query: str,
        count: int = 5,
        orientation: str = "landscape",
        min_width: int = 1920,
    ) -> List[StockImage]:
        """キーワードで画像を検索。Pexels優先、フォールバックでPixabay。"""
        images: List[StockImage] = []

        if self.pexels_api_key:
            try:
                images = self._search_pexels(query, count, orientation, min_width)
                if images:
                    logger.info(f"Pexels検索成功: '{query}' → {len(images)}件")
                    return images
            except HTTPError as e:
                status = e.response.status_code if e.response is not None else "?"
                logger.warning(f"Pexels検索失敗 (HTTP {status}): {e}")
            except (ConnectionError, Timeout) as e:
                logger.warning(f"Pexels検索失敗 (接続): {e}")
            except Exception as e:
                logger.warning(f"Pexels検索失敗: {e}")

        if self.pixabay_api_key:
            try:
                images = self._search_pixabay(query, count, orientation, min_width)
                if images:
                    logger.info(f"Pixabay検索成功: '{query}' → {len(images)}件")
                    return images
            except HTTPError as e:
                status = e.response.status_code if e.response is not None else "?"
                logger.warning(f"Pixabay検索失敗 (HTTP {status}): {e}")
            except (ConnectionError, Timeout) as e:
                logger.warning(f"Pixabay検索失敗 (接続): {e}")
            except Exception as e:
                logger.warning(f"Pixabay検索失敗: {e}")

        if not self.pexels_api_key and not self.pixabay_api_key:
            logger.warning("ストック画像APIキー未設定。PEXELS_API_KEY または PIXABAY_API_KEY を .env に設定してください。")

        return images

    def search_for_segments(
        self,
        segments: List[Dict[str, Any]],
        images_per_segment: int = 1,
        orientation: str = "landscape",
    ) -> List[StockImage]:
        """台本セグメント群からキーワードを抽出し、一括検索+ダウンロード。

        各セグメントの key_points や section 名からクエリを生成し、
        重複を避けながら画像を収集する。

        Returns:
            セグメント順に並んだStockImageリスト (ダウンロード済み)。
        """
        all_images: List[StockImage] = []
        seen_ids: set[str] = set()

        for i, segment in enumerate(segments):
            query = self._build_query_from_segment(segment)
            if not query:
                logger.debug(f"セグメント{i}: クエリ生成スキップ")
                all_images.append(StockImage(
                    id=f"empty_{i}", url="", download_url="",
                    width=0, height=0, photographer="", source="none",
                ))
                continue

            results = self.search(query, count=images_per_segment + 2, orientation=orientation)

            added = 0
            for img in results:
                if img.id in seen_ids:
                    continue
                seen_ids.add(img.id)

                downloaded = self.download(img)
                if downloaded:
                    all_images.append(downloaded)
                    added += 1
                    if added >= images_per_segment:
                        break

            if added == 0:
                logger.warning(f"セグメント{i}: '{query}' で画像取得失敗")
                all_images.append(StockImage(
                    id=f"empty_{i}", url="", download_url="",
                    width=0, height=0, photographer="", source="none",
                ))

        return all_images

    def download(self, image: StockImage) -> Optional[StockImage]:
        """画像をダウンロードしてキャッシュに保存。"""
        if not image.download_url:
            return None

        # キャッシュチェック
        cache_key = hashlib.md5(image.download_url.encode()).hexdigest()
        ext = ".jpg"
        if ".png" in image.download_url.lower():
            ext = ".png"
        cache_path = self.cache_dir / f"{image.source}_{cache_key}{ext}"

        if cache_path.exists():
            image.local_path = cache_path
            logger.debug(f"キャッシュヒット: {cache_path}")
            return image

        try:
            response = self._request_with_retry(
                image.download_url,
                timeout=30,
                source_name=f"Download({image.source})",
            )

            cache_path.write_bytes(response.content)
            image.local_path = cache_path
            logger.info(f"ダウンロード完了: {image.source}/{image.id} → {cache_path}")
            return image

        except HTTPError as e:
            status = e.response.status_code if e.response is not None else "?"
            logger.warning(f"ダウンロード失敗 (HTTP {status}): {image.download_url}")
            return None
        except (ConnectionError, Timeout) as e:
            logger.warning(f"ダウンロード失敗 (接続): {image.download_url} - {e}")
            return None
        except Exception as e:
            logger.warning(f"ダウンロード失敗: {image.download_url} - {e}")
            return None

    def _search_pexels(
        self,
        query: str,
        count: int,
        orientation: str,
        min_width: int,
    ) -> List[StockImage]:
        """Pexels API検索。"""
        headers = {"Authorization": self.pexels_api_key}
        params: Dict[str, Any] = {
            "query": query,
            "per_page": min(count, 15),
            "orientation": orientation,
        }

        response = self._request_with_retry(
            f"{self.PEXELS_BASE}/search",
            headers=headers,
            params=params,
            timeout=10,
            source_name="Pexels",
        )
        data = response.json()

        images: List[StockImage] = []
        for photo in data.get("photos", []):
            src = photo.get("src", {})
            original_w = photo.get("width", 0)
            original_h = photo.get("height", 0)

            if original_w < min_width:
                continue

            # large2x は 1920px幅以上が保証される
            download_url = src.get("large2x") or src.get("large") or src.get("original", "")

            images.append(StockImage(
                id=f"pexels_{photo['id']}",
                url=photo.get("url", ""),
                download_url=download_url,
                width=original_w,
                height=original_h,
                photographer=photo.get("photographer", ""),
                source="pexels",
                alt_text=photo.get("alt", ""),
            ))

        return images

    def _search_pixabay(
        self,
        query: str,
        count: int,
        orientation: str,
        min_width: int,
    ) -> List[StockImage]:
        """Pixabay API検索。"""
        params: Dict[str, Any] = {
            "key": self.pixabay_api_key,
            "q": query,
            "per_page": min(count, 20),
            "orientation": "horizontal" if orientation == "landscape" else orientation,
            "min_width": min_width,
            "image_type": "photo",
            "safesearch": "true",
            "lang": "ja",
        }

        response = self._request_with_retry(
            self.PIXABAY_BASE,
            params=params,
            timeout=10,
            source_name="Pixabay",
        )
        data = response.json()

        images: List[StockImage] = []
        for hit in data.get("hits", []):
            images.append(StockImage(
                id=f"pixabay_{hit['id']}",
                url=hit.get("pageURL", ""),
                download_url=hit.get("largeImageURL", ""),
                width=hit.get("imageWidth", 0),
                height=hit.get("imageHeight", 0),
                photographer=hit.get("user", ""),
                source="pixabay",
                alt_text="",
                tags=[t.strip() for t in hit.get("tags", "").split(",") if t.strip()],
            ))

        return images

    def _build_query_from_segment(self, segment: Dict[str, Any]) -> str:
        """台本セグメントから検索クエリを生成。"""
        # key_points がある場合は最も具体的なキーワードを使用
        key_points = segment.get("key_points", [])
        section = segment.get("section", "")
        content = segment.get("content", "") or segment.get("text", "")

        if key_points:
            # key_points の先頭2つを結合（クエリ長制限: 80文字）
            query = " ".join(key_points[:2])
            if len(query) > 80:
                query = key_points[0][:80]
            return query

        if section:
            return section

        # content から名詞的な部分を抽出 (簡易)
        if content:
            # 最初の40文字をクエリとして使用
            return content[:40].strip()

        return ""

    def _request_with_retry(
        self,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: int = 10,
        source_name: str = "",
    ) -> requests.Response:
        """リトライ付きHTTP GETリクエスト。

        - 5xx / 429: 指数バックオフでリトライ
        - 401 / 403: リトライせず即座にHTTPError送出
        - ConnectionError / Timeout: リトライ

        Raises:
            HTTPError: 401/403 または リトライ上限超過時
            ConnectionError: リトライ上限超過時
            Timeout: リトライ上限超過時
        """
        last_exception: Optional[Exception] = None

        for attempt in range(_MAX_RETRIES):
            try:
                self._rate_limit()
                response = self.session.get(
                    url, headers=headers, params=params, timeout=timeout,
                )

                # 401/403: APIキー無効 — リトライ不要
                if response.status_code in (401, 403):
                    logger.error(
                        f"{source_name} APIキー無効/失効 (HTTP {response.status_code})"
                    )
                    response.raise_for_status()

                # 429/5xx: リトライ対象
                if response.status_code in _RETRYABLE_STATUS_CODES:
                    wait = _BACKOFF_BASE * (2 ** attempt)
                    # 429: Retry-After ヘッダーがあれば優先
                    if response.status_code == 429:
                        retry_after = response.headers.get("Retry-After")
                        if retry_after and retry_after.isdigit():
                            wait = max(wait, float(retry_after))
                    logger.warning(
                        f"{source_name} HTTP {response.status_code} "
                        f"(attempt {attempt + 1}/{_MAX_RETRIES}), "
                        f"{wait:.1f}秒後にリトライ"
                    )
                    time.sleep(wait)
                    continue

                response.raise_for_status()
                return response

            except (ConnectionError, Timeout) as e:
                last_exception = e
                wait = _BACKOFF_BASE * (2 ** attempt)
                logger.warning(
                    f"{source_name} {type(e).__name__} "
                    f"(attempt {attempt + 1}/{_MAX_RETRIES}), "
                    f"{wait:.1f}秒後にリトライ"
                )
                time.sleep(wait)
                continue

        # リトライ上限超過
        if last_exception:
            raise last_exception
        # 最終レスポンスがリトライ対象エラーだった場合
        raise HTTPError(
            f"{source_name} リトライ上限超過 ({_MAX_RETRIES}回)",
            response=response,  # type: ignore[possibly-undefined]
        )

    def _rate_limit(self) -> None:
        """簡易レート制限。"""
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.monotonic()

    def get_attribution(self, images: List[StockImage]) -> str:
        """クレジット表記を生成 (動画概要欄用)。"""
        lines: List[str] = []
        for img in images:
            if img.source == "none" or not img.photographer:
                continue
            source_name = "Pexels" if img.source == "pexels" else "Pixabay"
            lines.append(f"Photo by {img.photographer} on {source_name}")

        if not lines:
            return ""

        unique_lines = list(dict.fromkeys(lines))  # 重複除去 (順序保持)
        return "--- Image Credits ---\n" + "\n".join(unique_lines)

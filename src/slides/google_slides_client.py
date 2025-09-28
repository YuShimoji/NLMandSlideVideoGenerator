"""
Google Slides クライアント
- プレゼンテーション作成
- スライド追加
- サムネイル/画像の取得
- PPTX エクスポート（Drive API）

認証:
- config.settings.GoogleAuthHelper を使用して Credentials を取得
- 非対話環境では既存 token.json がない場合は None を返す設計
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Any, Optional

import io
import requests

from config.settings import settings
from gapi.google_auth import GoogleAuthHelper


class SimpleLogger:
    def info(self, msg): print(f"[INFO] {msg}")
    def success(self, msg): print(f"[SUCCESS] {msg}")
    def warning(self, msg): print(f"[WARNING] {msg}")
    def error(self, msg): print(f"[ERROR] {msg}")


logger = SimpleLogger()


class GoogleSlidesClient:
    def __init__(self) -> None:
        self.auth = GoogleAuthHelper()
        self._slides_service = None
        self._drive_service = None

    def _get_slides_service(self):
        if self._slides_service is not None:
            return self._slides_service
        creds = self.auth.get_credentials()
        if not creds:
            return None
        try:
            from googleapiclient.discovery import build
            self._slides_service = build("slides", "v1", credentials=creds, cache_discovery=False)
            return self._slides_service
        except Exception as e:
            logger.warning(f"Slides API クライアント初期化失敗: {e}")
            return None

    def _get_drive_service(self):
        if self._drive_service is not None:
            return self._drive_service
        creds = self.auth.get_credentials()
        if not creds:
            return None
        try:
            from googleapiclient.discovery import build
            self._drive_service = build("drive", "v3", credentials=creds, cache_discovery=False)
            return self._drive_service
        except Exception as e:
            logger.warning(f"Drive API クライアント初期化失敗: {e}")
            return None

    def is_available(self) -> bool:
        return self._get_slides_service() is not None

    def create_presentation(self, title: str) -> Optional[str]:
        service = self._get_slides_service()
        if not service:
            logger.warning("Slides API 未認証のため、モックへフォールバックします")
            return None
        try:
            body = {"title": title}
            pres = service.presentations().create(body=body).execute()
            pres_id = pres.get("presentationId") or pres.get("presentationId") or pres.get("presentationId")
            if not pres_id:
                # 一部環境でキー名が異なる場合
                pres_id = pres.get("presentationId") or pres.get("presentationId")
            logger.success(f"プレゼン作成: {pres_id}")
            return pres.get("presentationId") or pres.get("presentationId") or pres.get("presentationId")
        except Exception as e:
            logger.warning(f"プレゼン作成失敗: {e}")
            return None

    def add_slides(self, presentation_id: str, slides: List[Dict[str, Any]]) -> bool:
        service = self._get_slides_service()
        if not service:
            return False
        try:
            requests_body = []
            for slide in slides:
                # スライド作成
                requests_body.append({
                    "createSlide": {
                        "slideLayoutReference": {"predefinedLayout": "TITLE_AND_BODY"}
                    }
                })
                # テキスト挿入（タイトル・本文）
                title_text = slide.get("title", "")
                content_text = slide.get("content", "")
                # 簡易的に、直前に作成したスライドのプレースホルダーにテキスト設定
                requests_body.append({
                    "insertText": {
                        "objectId": "title",
                        "text": title_text
                    }
                })
                requests_body.append({
                    "insertText": {
                        "objectId": "body",
                        "text": content_text
                    }
                })
            # 実行
            service.presentations().batchUpdate(
                presentationId=presentation_id,
                body={"requests": requests_body}
            ).execute()
            return True
        except Exception as e:
            logger.warning(f"スライド追加失敗: {e}")
            return False

    def export_thumbnails(self, presentation_id: str, out_dir: Path) -> List[Path]:
        service = self._get_slides_service()
        if not service:
            return []
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
            pres = service.presentations().get(presentationId=presentation_id).execute()
            pages = pres.get("slides", [])
            saved: List[Path] = []
            for idx, page in enumerate(pages, start=1):
                page_id = page.get("objectId")
                if not page_id:
                    continue
                # サムネイルURL取得
                thumb = service.presentations().pages().getThumbnail(
                    presentationId=presentation_id,
                    pageObjectId=page_id,
                    thumbnailProperties_mimeType="PNG",
                    thumbnailProperties_thumbnailSize="LARGE",
                ).execute()
                url = thumb.get("contentUrl")
                if not url:
                    continue
                # ダウンロード
                resp = requests.get(url, timeout=30)
                resp.raise_for_status()
                img_path = out_dir / f"slide_{idx:03d}.png"
                with open(img_path, "wb") as f:
                    f.write(resp.content)
                saved.append(img_path)
            logger.success(f"スライド画像保存: {len(saved)}枚 -> {out_dir}")
            return saved
        except Exception as e:
            logger.warning(f"サムネイル取得失敗: {e}")
            return []

    def export_pptx(self, presentation_id: str, out_path: Path) -> bool:
        drive = self._get_drive_service()
        if not drive:
            return False
        try:
            from googleapiclient.http import MediaIoBaseDownload
            request = drive.files().export_media(
                fileId=presentation_id,
                mimeType="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            )
            out_path.parent.mkdir(parents=True, exist_ok=True)
            fh = io.FileIO(str(out_path), "wb")
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
            logger.success(f"PPTXエクスポート完了: {out_path}")
            return True
        except Exception as e:
            logger.warning(f"PPTXエクスポート失敗: {e}")
            return False

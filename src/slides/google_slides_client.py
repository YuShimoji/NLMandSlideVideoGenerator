"""
Google Slides クライアント
- テンプレート複製方式 (推奨): テンプレートプレゼンを複製しプレースホルダーを置換
- プログラマティック方式 (フォールバック): 空プレゼン作成 + レイアウト指定 + テキスト挿入
- サムネイル/PNG 取得
- PPTX エクスポート (Drive API)

認証:
- gapi.google_auth.GoogleAuthHelper を使用して Credentials を取得
- 非対話環境では既存 token.json がない場合は None を返す設計

三段フォールバック:
  テンプレート複製 → プログラマティック作成 → (呼び出し側で python-pptx モック)
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional

import io
import requests as http_requests

from gapi.google_auth import GoogleAuthHelper
from core.utils.logger import logger
from .slide_templates import LayoutType, SlideContent, SlideTemplateConfig


class GoogleSlidesClient:
    def __init__(self, template_config: Optional[SlideTemplateConfig] = None) -> None:
        self.auth = GoogleAuthHelper()
        self._slides_service = None
        self._drive_service = None
        self.template_config = template_config or SlideTemplateConfig()

    # ------------------------------------------------------------------
    # Service 初期化
    # ------------------------------------------------------------------

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
        creds = self.auth.get_credentials()
        if not creds:
            return False
        try:
            import googleapiclient.discovery  # noqa: F401
            return True
        except ImportError as e:
            logger.warning(f"google-api-python-client が見つからないため Slides API を使用できません: {e}")
            return False
        except Exception as e:
            logger.warning(f"Slides API 利用可否チェックに失敗: {e}")
            return False

    # ------------------------------------------------------------------
    # テンプレート複製方式
    # ------------------------------------------------------------------

    def copy_presentation(self, template_id: str, new_title: str) -> Optional[str]:
        """テンプレートプレゼンテーションを複製して新しいプレゼンIDを返す。

        Drive API の files().copy() を使用する。
        """
        drive = self._get_drive_service()
        if not drive:
            logger.warning("Drive API 未認証のため、テンプレート複製をスキップします")
            return None
        try:
            copied = drive.files().copy(
                fileId=template_id,
                body={"name": new_title},
            ).execute()
            new_id = copied.get("id")
            if new_id:
                logger.success(f"テンプレート複製完了: {template_id} -> {new_id}")
                return str(new_id)
            return None
        except Exception as e:
            logger.warning(f"テンプレート複製失敗: {e}")
            return None

    def replace_template_placeholders(
        self,
        presentation_id: str,
        slide_contents: List[SlideContent],
    ) -> bool:
        """テンプレートプレゼン内のプレースホルダータグを一括置換する。

        テンプレートには {{TITLE}}, {{BODY}}, {{SPEAKER}}, {{KEYPOINTS}} のような
        プレースホルダー文字列が含まれている前提。
        replaceAllText で一括置換する。

        テンプレート内にスライドが N 枚あり、slide_contents が M 個の場合:
        - M <= N: 余剰スライドは削除
        - M > N: 追加分は add_slides_with_content で追加
        """
        service = self._get_slides_service()
        if not service:
            return False

        try:
            pres = service.presentations().get(
                presentationId=presentation_id
            ).execute()
            existing_slides = pres.get("slides", [])
            # 最初のスライド (タイトルスライド) はスキップする場合があるが、
            # テンプレートの設計次第。ここでは全スライドを対象とする。

            api_requests: List[Dict[str, Any]] = []
            cfg = self.template_config

            # 各スライドのプレースホルダーを置換
            # テンプレートではスライドごとに {{TITLE_1}}, {{BODY_1}} のように
            # インデックス付きタグを使うか、
            # 全スライド同一タグで replaceAllText するかの二択。
            # ここではインデックス付きタグ方式を採用:
            #   {{TITLE_1}}, {{BODY_1}}, {{SPEAKER_1}}, {{KEYPOINTS_1}}
            for i, content in enumerate(slide_contents):
                idx = i + 1
                replacements = {
                    f"{{{{TITLE_{idx}}}}}": content.title,
                    f"{{{{BODY_{idx}}}}}": content.format_body_with_keypoints(),
                    f"{{{{SPEAKER_{idx}}}}}": content.format_subtitle(),
                    f"{{{{KEYPOINTS_{idx}}}}}": "\n".join(
                        f"  {kp}" for kp in content.key_points
                    ),
                }
                for tag, replacement in replacements.items():
                    if replacement:
                        api_requests.append({
                            "replaceAllText": {
                                "containsText": {
                                    "text": tag,
                                    "matchCase": True,
                                },
                                "replaceText": replacement,
                            }
                        })
                    else:
                        # 空のプレースホルダーは空文字で置換して消す
                        api_requests.append({
                            "replaceAllText": {
                                "containsText": {
                                    "text": tag,
                                    "matchCase": True,
                                },
                                "replaceText": "",
                            }
                        })

            # 余剰スライドの削除
            if len(existing_slides) > len(slide_contents):
                for slide in existing_slides[len(slide_contents):]:
                    slide_id = slide.get("objectId")
                    if slide_id:
                        api_requests.append({
                            "deleteObject": {"objectId": slide_id}
                        })

            if api_requests:
                service.presentations().batchUpdate(
                    presentationId=presentation_id,
                    body={"requests": api_requests},
                ).execute()
                logger.success(
                    f"テンプレートプレースホルダー置換完了: {len(slide_contents)}枚分"
                )

            # テンプレートにスライドが足りない場合は追加
            if len(slide_contents) > len(existing_slides):
                extra = slide_contents[len(existing_slides):]
                self.add_slides_with_content(presentation_id, extra)

            return True

        except Exception as e:
            logger.warning(f"テンプレートプレースホルダー置換失敗: {e}")
            return False

    # ------------------------------------------------------------------
    # プログラマティック方式 (フォールバック)
    # ------------------------------------------------------------------

    def create_presentation(self, title: str) -> Optional[str]:
        service = self._get_slides_service()
        if not service:
            logger.warning("Slides API 未認証のため、モックへフォールバックします")
            return None
        try:
            body = {"title": title}
            pres = service.presentations().create(body=body).execute()
            pres_id = pres.get("presentationId")
            logger.success(f"プレゼン作成: {pres_id}")
            return str(pres_id) if pres_id else None
        except Exception as e:
            logger.warning(f"プレゼン作成失敗: {e}")
            return None

    def add_slides(self, presentation_id: str, slides: List[Dict[str, Any]]) -> bool:
        """プレゼンテーションにスライドを追加 (レガシー互換)

        SlideContent を使わない旧 API。内部で SlideContent に変換して
        add_slides_with_content を呼ぶ。
        """
        contents = [SlideContent.from_dict(s) for s in slides]
        return self.add_slides_with_content(presentation_id, contents)

    def add_slides_with_content(
        self,
        presentation_id: str,
        slide_contents: List[SlideContent],
    ) -> bool:
        """プレゼンテーションにレイアウト付きスライドを追加しテキストを挿入する。

        Step 1: createSlide でレイアウト指定のスライドを一括作成
        Step 2: presentations().get() でプレースホルダー objectId を取得
        Step 3: insertText でテキストを挿入
        """
        service = self._get_slides_service()
        if not service:
            logger.warning("Slides API 未利用のため add_slides をスキップします")
            return False

        if not slide_contents:
            logger.warning("追加対象スライドが空のため、Slides API 呼び出しをスキップします")
            return True

        try:
            # Step 1: スライド作成
            create_requests: List[Dict[str, Any]] = []
            slide_object_ids: List[str] = []

            for content in slide_contents:
                obj_id = f"slide_{uuid.uuid4().hex[:12]}"
                slide_object_ids.append(obj_id)
                create_requests.append({
                    "createSlide": {
                        "objectId": obj_id,
                        "slideLayoutReference": {
                            "predefinedLayout": content.layout.value,
                        },
                    }
                })

            result = service.presentations().batchUpdate(
                presentationId=presentation_id,
                body={"requests": create_requests},
            ).execute()
            logger.info(f"スライド作成完了: {len(slide_contents)}枚")

            # Step 2: プレースホルダー objectId を取得
            pres = service.presentations().get(
                presentationId=presentation_id
            ).execute()
            all_slides = pres.get("slides", [])

            # 作成したスライドを objectId で特定
            slide_map: Dict[str, Dict] = {}
            for slide_page in all_slides:
                oid = slide_page.get("objectId", "")
                if oid in slide_object_ids:
                    slide_map[oid] = slide_page

            # Step 3: テキスト挿入
            text_requests: List[Dict[str, Any]] = []

            for obj_id, content in zip(slide_object_ids, slide_contents):
                slide_page = slide_map.get(obj_id)
                if not slide_page:
                    continue

                placeholders = self._extract_placeholders(slide_page)

                # タイトルプレースホルダー
                title_ph = placeholders.get("TITLE") or placeholders.get("CENTERED_TITLE")
                if title_ph and content.title:
                    text_requests.append({
                        "insertText": {
                            "objectId": title_ph,
                            "text": content.title,
                            "insertionIndex": 0,
                        }
                    })

                # サブタイトル / 話者名
                subtitle_ph = placeholders.get("SUBTITLE")
                if subtitle_ph and content.speaker:
                    text_requests.append({
                        "insertText": {
                            "objectId": subtitle_ph,
                            "text": content.format_subtitle(),
                            "insertionIndex": 0,
                        }
                    })

                # 本文プレースホルダー
                body_ph = placeholders.get("BODY")
                if body_ph:
                    body_text = content.format_body_with_keypoints()
                    if body_text:
                        text_requests.append({
                            "insertText": {
                                "objectId": body_ph,
                                "text": body_text,
                                "insertionIndex": 0,
                            }
                        })

            if text_requests:
                service.presentations().batchUpdate(
                    presentationId=presentation_id,
                    body={"requests": text_requests},
                ).execute()
                logger.success(
                    f"テキスト挿入完了: {len(text_requests)}件のプレースホルダー"
                )

            logger.success(f"Slides API で {len(slide_contents)} 枚のスライドを作成しました")
            return True

        except Exception as e:
            logger.warning(f"スライド追加失敗: {e}")
            return False

    @staticmethod
    def _extract_placeholders(slide_page: Dict) -> Dict[str, str]:
        """スライドページからプレースホルダーの type -> objectId マッピングを抽出する。"""
        result: Dict[str, str] = {}
        elements = slide_page.get("pageElements", [])
        for elem in elements:
            shape = elem.get("shape", {})
            ph = shape.get("placeholder", {})
            ph_type = ph.get("type")
            obj_id = elem.get("objectId")
            if ph_type and obj_id:
                # 同一 type が複数ある場合 (TWO_COLUMNS の BODY x2)、
                # 最初のもののみ格納 (後続は BODY_2 等で区別)
                if ph_type not in result:
                    result[ph_type] = obj_id
                else:
                    # 2番目以降は _N サフィックス
                    n = 2
                    while f"{ph_type}_{n}" in result:
                        n += 1
                    result[f"{ph_type}_{n}"] = obj_id
        return result

    # ------------------------------------------------------------------
    # テンプレート複製 + コンテンツ挿入 統合メソッド
    # ------------------------------------------------------------------

    def generate_from_template(
        self,
        slide_contents: List[SlideContent],
        presentation_title: str,
    ) -> Optional[str]:
        """テンプレート複製方式でプレゼンテーションを生成する。

        Returns:
            成功時はプレゼンテーションID、失敗時は None。
        """
        if not self.template_config.is_template_mode:
            logger.info("テンプレートID未設定のため、テンプレート複製方式をスキップ")
            return None

        template_id = self.template_config.template_presentation_id
        if not template_id:
            return None

        # 1. テンプレート複製
        new_pres_id = self.copy_presentation(template_id, presentation_title)
        if not new_pres_id:
            return None

        # 2. プレースホルダー置換
        success = self.replace_template_placeholders(new_pres_id, slide_contents)
        if not success:
            logger.warning("プレースホルダー置換に失敗しましたが、プレゼンは作成済みです")

        return new_pres_id

    def generate_programmatic(
        self,
        slide_contents: List[SlideContent],
        presentation_title: str,
    ) -> Optional[str]:
        """プログラマティック方式でプレゼンテーションを生成する。

        テンプレートなしで空プレゼン作成 + レイアウト指定 + テキスト挿入。

        Returns:
            成功時はプレゼンテーションID、失敗時は None。
        """
        pres_id = self.create_presentation(presentation_title)
        if not pres_id:
            return None

        self.add_slides_with_content(pres_id, slide_contents)
        return pres_id

    # ------------------------------------------------------------------
    # エクスポート
    # ------------------------------------------------------------------

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
                thumb = service.presentations().pages().getThumbnail(
                    presentationId=presentation_id,
                    pageObjectId=page_id,
                    thumbnailProperties_mimeType="PNG",
                    thumbnailProperties_thumbnailSize="LARGE",
                ).execute()
                url = thumb.get("contentUrl")
                if not url:
                    continue
                resp = http_requests.get(url, timeout=30)
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

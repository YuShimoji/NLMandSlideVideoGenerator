"""
スライドテンプレート管理モジュール

レイアウトパターンの定義、Google Slides テンプレートの設定管理、
プレースホルダーマッピングを担当する。

テンプレート複製方式:
  1. Google Drive 上のテンプレートプレゼンを複製
  2. プレースホルダーにテキストを挿入
  3. PNG 化してダウンロード

フォールバック:
  - テンプレートID未設定時 → predefinedLayout で空スライド作成 + テキスト挿入
  - API未認証時 → python-pptx モック
"""
from __future__ import annotations

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional


class LayoutType(str, Enum):
    """スライドレイアウトパターン

    Google Slides の predefinedLayout 名に対応。
    テンプレート複製方式では、テンプレート内の対応レイアウトを使用する。
    """

    TITLE = "TITLE"
    TITLE_AND_BODY = "TITLE_AND_BODY"
    TITLE_AND_TWO_COLUMNS = "TITLE_AND_TWO_COLUMNS"
    TITLE_ONLY = "TITLE_ONLY"
    BLANK = "BLANK"
    SECTION_HEADER = "SECTION_HEADER"
    ONE_COLUMN_TEXT = "ONE_COLUMN_TEXT"

    @classmethod
    def from_content_hint(cls, hint: str) -> "LayoutType":
        """コンテンツヒント文字列からレイアウトを推定する。

        content_splitter や Gemini 由来のレイアウト指定を
        Google Slides の predefinedLayout に変換する。
        """
        mapping = {
            "title": cls.TITLE,
            "title_slide": cls.TITLE,
            "section": cls.SECTION_HEADER,
            "section_header": cls.SECTION_HEADER,
            "two_column": cls.TITLE_AND_TWO_COLUMNS,
            "two_columns": cls.TITLE_AND_TWO_COLUMNS,
            "full_text": cls.TITLE_AND_BODY,
            "title_and_content": cls.TITLE_AND_BODY,
            "title_and_body": cls.TITLE_AND_BODY,
            "stats": cls.TITLE_AND_BODY,
            "emphasis": cls.SECTION_HEADER,
            "title_only": cls.TITLE_ONLY,
            "blank": cls.BLANK,
        }
        normalized = hint.strip().lower().replace("-", "_")
        return mapping.get(normalized, cls.TITLE_AND_BODY)


# ---------------------------------------------------------------------------
# プレースホルダー定義
# ---------------------------------------------------------------------------

# Google Slides の predefinedLayout ごとに想定されるプレースホルダー。
# batchUpdate で insertText する際に使う。
# objectId はスライド作成後に presentations().get() で取得するため、
# ここでは placeholder の type のみ定義する。
PLACEHOLDER_TYPES = {
    LayoutType.TITLE: ["CENTERED_TITLE", "SUBTITLE"],
    LayoutType.TITLE_AND_BODY: ["TITLE", "BODY"],
    LayoutType.TITLE_AND_TWO_COLUMNS: ["TITLE", "BODY", "BODY"],
    LayoutType.TITLE_ONLY: ["TITLE"],
    LayoutType.SECTION_HEADER: ["TITLE", "SUBTITLE"],
    LayoutType.ONE_COLUMN_TEXT: ["TITLE", "BODY"],
    LayoutType.BLANK: [],
}


# ---------------------------------------------------------------------------
# テンプレート設定
# ---------------------------------------------------------------------------

@dataclass
class SlideTemplateConfig:
    """テンプレートプレゼンテーションの設定

    Attributes:
        template_presentation_id: Google Drive 上のテンプレートプレゼンID。
            None の場合はプログラマティック作成にフォールバック。
        layout_mapping: テンプレート内のレイアウト名 → LayoutType のマッピング。
            テンプレート複製時に、各スライドに適用するレイアウトを選択するために使う。
        default_layout: レイアウト指定がないスライドに使うデフォルト。
        title_placeholder_tag: テンプレート内のタイトルプレースホルダーを
            識別するためのタグ文字列 (例: "{{TITLE}}")。
        body_placeholder_tag: テンプレート内の本文プレースホルダーを
            識別するためのタグ文字列 (例: "{{BODY}}")。
        speaker_placeholder_tag: 話者名プレースホルダー (例: "{{SPEAKER}}")。
        keypoints_placeholder_tag: キーポイントプレースホルダー (例: "{{KEYPOINTS}}")。
    """

    template_presentation_id: Optional[str] = None
    layout_mapping: Dict[str, LayoutType] = field(default_factory=dict)
    default_layout: LayoutType = LayoutType.TITLE_AND_BODY
    title_placeholder_tag: str = "{{TITLE}}"
    body_placeholder_tag: str = "{{BODY}}"
    speaker_placeholder_tag: str = "{{SPEAKER}}"
    keypoints_placeholder_tag: str = "{{KEYPOINTS}}"

    @property
    def is_template_mode(self) -> bool:
        """テンプレート複製方式が利用可能か"""
        return self.template_presentation_id is not None

    @classmethod
    def from_settings(cls, slides_settings: dict) -> "SlideTemplateConfig":
        """settings.SLIDES_SETTINGS から SlideTemplateConfig を生成する。"""
        template_id = slides_settings.get("template_presentation_id")
        default_layout_str = slides_settings.get("default_layout", "TITLE_AND_BODY")
        try:
            default_layout = LayoutType(default_layout_str)
        except ValueError:
            default_layout = LayoutType.TITLE_AND_BODY

        return cls(
            template_presentation_id=template_id if template_id else None,
            default_layout=default_layout,
            title_placeholder_tag=slides_settings.get(
                "title_placeholder_tag", "{{TITLE}}"
            ),
            body_placeholder_tag=slides_settings.get(
                "body_placeholder_tag", "{{BODY}}"
            ),
            speaker_placeholder_tag=slides_settings.get(
                "speaker_placeholder_tag", "{{SPEAKER}}"
            ),
            keypoints_placeholder_tag=slides_settings.get(
                "keypoints_placeholder_tag", "{{KEYPOINTS}}"
            ),
        )


# ---------------------------------------------------------------------------
# スライドコンテンツ → API リクエスト変換
# ---------------------------------------------------------------------------

@dataclass
class SlideContent:
    """1枚のスライドに挿入するコンテンツ

    google_slides_client に渡す中間表現。
    """

    title: str = ""
    body: str = ""
    speaker: str = ""
    key_points: List[str] = field(default_factory=list)
    layout: LayoutType = LayoutType.TITLE_AND_BODY

    @classmethod
    def from_dict(cls, d: dict, default_layout: LayoutType = LayoutType.TITLE_AND_BODY) -> "SlideContent":
        """content_splitter / Gemini 出力の辞書から生成する。"""
        layout_hint = d.get("layout", d.get("layout_type", ""))
        layout = LayoutType.from_content_hint(layout_hint) if layout_hint else default_layout

        speakers = d.get("speakers", [])
        speaker_str = ", ".join(speakers) if isinstance(speakers, list) else str(speakers or "")

        key_points = d.get("key_points", [])

        body = d.get("text", d.get("content", ""))

        return cls(
            title=d.get("title", ""),
            body=body,
            speaker=speaker_str,
            key_points=key_points if isinstance(key_points, list) else [],
            layout=layout,
        )

    def format_body_with_keypoints(self) -> str:
        """本文 + キーポイントを統合した表示用テキストを返す。"""
        parts = []
        if self.body:
            parts.append(self.body)
        if self.key_points:
            parts.append("")
            for kp in self.key_points:
                parts.append(f"  {kp}")
        return "\n".join(parts)

    def format_subtitle(self) -> str:
        """話者名を含むサブタイトルを返す。"""
        if self.speaker:
            return self.speaker
        return ""

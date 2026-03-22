#!/usr/bin/env python3
"""
YMM4テンプレートベースのサムネイル生成モジュール (SP-037 Phase 3-4)

ユーザーがYMM4で作成したサムネイルテンプレート (.y4mmp) を読み込み、
可変要素 (テキスト、画像パス、配色) を差し替えて出力する。

Phase 4 追加機能:
- 色彩プリセット (5種) による TextItem の色差し替え
- バリエーション生成 (A/Bテスト用)
- 拡張プレースホルダー (MAIN_TEXT, SUB_TEXT, SECTION_1-4 等)

ワークフロー:
1. ユーザーがYMM4でサムネイルテンプレートを作成 (1フレーム .y4mmp)
2. テンプレートを config/thumbnail_templates/ に配置
3. パイプラインが本モジュールでテキスト/画像/色を差し替え
4. 出力: work_dir/thumbnail_project.y4mmp (+ バリエーション)
5. ユーザーがYMM4で開き、1フレームPNG書き出し+レビュー

テンプレート規約:
- TextItem の Text フィールドに {{TITLE}}, {{SUBTITLE}} 等のプレースホルダーを記述
- ImageItem の FilePath に {{BACKGROUND}}, {{CHARACTER}} 等のプレースホルダーを記述
- プレースホルダー名は大文字英字+アンダースコアで {{NAME}} 形式
"""

import copy
import json
import re
import shutil
from pathlib import Path
from typing import Any

from config.settings import settings, PROJECT_ROOT
from core.utils.logger import logger


# プレースホルダーパターン: {{NAME}} 形式
_PLACEHOLDER_RE = re.compile(r"\{\{([A-Z_]+)\}\}")

# デフォルトのテンプレートディレクトリ
_DEFAULT_TEMPLATE_DIR = PROJECT_ROOT / "config" / "thumbnail_templates"

# 色彩プリセット定義 (SP-037 Phase 4)
# YMM4 の色フォーマット: #RRGGBB 文字列
COLOR_PRESETS: dict[str, dict[str, Any]] = {
    "dark_red": {
        "description": "時事、衝撃、ミステリー向け",
        "main_font_color": "#FF0000",
        "main_outline_color": "#FFFFFF",
        "main_outline_width": 5,
        "sub_font_color": "#FFFFFF",
        "sub_outline_color": "#333333",
        "sub_outline_width": 3,
    },
    "dark_yellow": {
        "description": "科学、発見、雑学向け",
        "main_font_color": "#FFD700",
        "main_outline_color": "#CC0000",
        "main_outline_width": 5,
        "sub_font_color": "#FFFFFF",
        "sub_outline_color": "#333333",
        "sub_outline_width": 3,
    },
    "map_white": {
        "description": "地理、インフラ、地政学向け",
        "main_font_color": "#FFFFFF",
        "main_outline_color": "#FF0000",
        "main_outline_width": 5,
        "sub_font_color": "#FFFF00",
        "sub_outline_color": "#000000",
        "sub_outline_width": 3,
    },
    "high_contrast": {
        "description": "テクノロジー、AI、未来系向け",
        "main_font_color": "#FFFFFF",
        "main_outline_color": "#000000",
        "main_outline_width": 6,
        "sub_font_color": "#00FF9D",
        "sub_outline_color": "#000000",
        "sub_outline_width": 3,
    },
    "warm_alert": {
        "description": "緊急ニュース、警告系向け",
        "main_font_color": "#FFD700",
        "main_outline_color": "#FF4500",
        "main_outline_width": 5,
        "sub_font_color": "#FFFFFF",
        "sub_outline_color": "#8B0000",
        "sub_outline_width": 3,
    },
}

# メインテキストとサブテキストの判定に使うプレースホルダー名
_MAIN_TEXT_PLACEHOLDERS = {"TITLE", "MAIN_TEXT"}
_SUB_TEXT_PLACEHOLDERS = {"SUBTITLE", "SUB_TEXT"}


class Ymm4ThumbnailGenerator:
    """YMM4テンプレートベースのサムネイル生成器。

    テンプレート .y4mmp を読み込み、プレースホルダーを差し替えて
    新しい .y4mmp を出力する。YMM4で開いて1フレーム書き出し用。
    """

    def __init__(self, template_dir: Path | None = None) -> None:
        self.template_dir = template_dir or _DEFAULT_TEMPLATE_DIR
        self._templates: dict[str, dict[str, Any]] = {}

    def discover_templates(self) -> list[str]:
        """利用可能なテンプレート名を一覧する。"""
        if not self.template_dir.exists():
            return []
        return [p.stem for p in sorted(self.template_dir.glob("*.y4mmp"))]

    def load_template(self, name: str) -> dict[str, Any]:
        """テンプレートをロードする。キャッシュあり。"""
        if name in self._templates:
            return self._templates[name]

        path = self.template_dir / f"{name}.y4mmp"
        if not path.exists():
            raise FileNotFoundError(f"サムネイルテンプレートが見つかりません: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self._templates[name] = data
        logger.info(f"サムネイルテンプレートをロード: {name} ({path})")
        return data

    def list_placeholders(self, name: str) -> dict[str, list[str]]:
        """テンプレート内のプレースホルダーを検出して一覧する。

        Returns:
            {"text": ["TITLE", "SUBTITLE"], "image": ["BACKGROUND", "CHARACTER"]}
        """
        data = self.load_template(name)
        text_placeholders: list[str] = []
        image_placeholders: list[str] = []

        items = self._get_all_items(data)
        for item in items:
            item_type = item.get("$type", "")

            # TextItem のプレースホルダー
            if "TextItem" in item_type:
                text_val = item.get("Text", "")
                text_placeholders.extend(_PLACEHOLDER_RE.findall(text_val))

            # ImageItem のプレースホルダー
            if "ImageItem" in item_type:
                path_val = item.get("FilePath", "")
                image_placeholders.extend(_PLACEHOLDER_RE.findall(path_val))

            # Serif フィールド (VoiceItem 等)
            serif_val = item.get("Serif", "")
            if serif_val:
                text_placeholders.extend(_PLACEHOLDER_RE.findall(serif_val))

        return {
            "text": sorted(set(text_placeholders)),
            "image": sorted(set(image_placeholders)),
        }

    def generate(
        self,
        template_name: str,
        output_dir: Path,
        replacements: dict[str, str],
        output_filename: str = "thumbnail_project.y4mmp",
        color_preset: str | None = None,
    ) -> Path:
        """テンプレートのプレースホルダーを差し替えて .y4mmp を出力する。

        Args:
            template_name: テンプレート名 (拡張子なし)。
            output_dir: 出力先ディレクトリ。
            replacements: プレースホルダー名 → 値 のマッピング。
                例: {"TITLE": "AI最新動向", "BACKGROUND": "C:/images/bg.png"}
            output_filename: 出力ファイル名。
            color_preset: 色彩プリセット名 (Phase 4)。None の場合はテンプレートの色をそのまま使う。

        Returns:
            出力された .y4mmp のパス。
        """
        data = self.load_template(template_name)

        # ディープコピーして元テンプレートを汚さない
        project = copy.deepcopy(data)

        # 全アイテムのプレースホルダーを差し替え
        replaced_count = 0
        items = self._get_all_items(project)
        for item in items:
            replaced_count += self._replace_in_item(item, replacements)

        # 色彩プリセット適用 (Phase 4)
        if color_preset:
            self._apply_color_preset(project, color_preset, replacements)

        # FilePath を出力先に更新
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / output_filename
        project["FilePath"] = str(out_path.resolve())

        # 書き出し
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(project, f, ensure_ascii=False, indent=2)

        logger.info(
            f"サムネイルプロジェクト生成: {out_path} "
            f"(テンプレート: {template_name}, 置換: {replaced_count}件"
            f"{', プリセット: ' + color_preset if color_preset else ''})"
        )

        # テンプレートディレクトリにある素材ファイルを出力先にコピー
        self._copy_template_assets(template_name, output_dir)

        return out_path

    def generate_from_script(
        self,
        template_name: str,
        script: dict[str, Any],
        output_dir: Path,
        background_image: Path | str | None = None,
        character_image: Path | str | None = None,
        color_preset: str | None = None,
    ) -> Path:
        """台本データからプレースホルダーを自動構成してサムネイルを生成する。

        パイプライン統合用のヘルパーメソッド。

        Args:
            template_name: テンプレート名。
            script: 台本データ (title, segments)。
            output_dir: 出力先ディレクトリ。
            background_image: 背景画像のパス。
            character_image: キャラクター画像のパス。
            color_preset: 色彩プリセット名。

        Returns:
            出力された .y4mmp のパス。
        """
        title = script.get("title", "")
        segments = script.get("segments", [])
        subtitle = ""
        if segments:
            first_text = segments[0].get("content", segments[0].get("text", ""))
            subtitle = first_text[:40] + ("..." if len(first_text) > 40 else "")

        replacements: dict[str, str] = {
            "TITLE": title,
            "SUBTITLE": subtitle,
        }

        if background_image:
            replacements["BACKGROUND"] = str(Path(background_image).resolve())

        if character_image:
            replacements["CHARACTER"] = str(Path(character_image).resolve())

        return self.generate(
            template_name=template_name,
            output_dir=output_dir,
            replacements=replacements,
            color_preset=color_preset,
        )

    def generate_variants(
        self,
        template_name: str,
        output_dir: Path,
        base_replacements: dict[str, str],
        variant_texts: list[dict[str, str]] | None = None,
        color_presets: list[str] | None = None,
    ) -> list[Path]:
        """複数バリエーションの .y4mmp を生成する (A/Bテスト用)。

        テキストバリエーション x 色バリエーション の組み合わせを生成する。
        どちらか一方のみ指定した場合は、その軸のバリエーションのみ生成。

        Args:
            template_name: テンプレート名。
            output_dir: 出力先ディレクトリ。
            base_replacements: ベースのプレースホルダー値。
            variant_texts: テキストバリエーション。各 dict は差し替えるキーと値。
                例: [{"MAIN_TEXT": "なぜXは..."}, {"MAIN_TEXT": "衝撃のX"}]
            color_presets: 適用する色彩プリセット名のリスト。

        Returns:
            生成された .y4mmp パスのリスト。
        """
        results: list[Path] = []

        # バリエーションの組み合わせを構築
        text_variants = variant_texts or [{}]
        preset_variants = color_presets or [None]

        variant_index = 0
        for text_overrides in text_variants:
            for preset in preset_variants:
                variant_index += 1
                replacements = {**base_replacements, **text_overrides}
                filename = f"thumbnail_variant_{variant_index:02d}.y4mmp"

                path = self.generate(
                    template_name=template_name,
                    output_dir=output_dir,
                    replacements=replacements,
                    output_filename=filename,
                    color_preset=preset,
                )
                results.append(path)

        logger.info(
            f"サムネイルバリエーション生成完了: {len(results)}件 "
            f"(テキスト: {len(text_variants)}パターン, "
            f"色: {len(preset_variants)}パターン)"
        )
        return results

    @staticmethod
    def list_color_presets() -> dict[str, str]:
        """利用可能な色彩プリセットとその説明を返す。"""
        return {name: preset["description"] for name, preset in COLOR_PRESETS.items()}

    def _get_all_items(self, project: dict[str, Any]) -> list[dict[str, Any]]:
        """プロジェクト内の全タイムラインアイテムを取得する。"""
        items: list[dict[str, Any]] = []
        for timeline in project.get("Timelines", []):
            items.extend(timeline.get("Items", []))
        return items

    def _replace_in_item(self, item: dict[str, Any], replacements: dict[str, str]) -> int:
        """アイテム内のプレースホルダーを差し替える。再帰的に全フィールドを走査。"""
        count = 0

        def _replace_value(value: Any) -> tuple[Any, int]:
            if isinstance(value, str):
                new_val = value
                c = 0
                for name, replacement in replacements.items():
                    placeholder = "{{" + name + "}}"
                    if placeholder in new_val:
                        new_val = new_val.replace(placeholder, replacement)
                        c += 1
                return new_val, c
            if isinstance(value, dict):
                c = 0
                for k, v in value.items():
                    new_v, sub_c = _replace_value(v)
                    if sub_c > 0:
                        value[k] = new_v
                        c += sub_c
                return value, c
            if isinstance(value, list):
                c = 0
                for i, v in enumerate(value):
                    new_v, sub_c = _replace_value(v)
                    if sub_c > 0:
                        value[i] = new_v
                        c += sub_c
                return value, c
            return value, 0

        for key, val in item.items():
            new_val, c = _replace_value(val)
            if c > 0:
                item[key] = new_val
                count += c

        return count

    def _apply_color_preset(
        self,
        project: dict[str, Any],
        preset_name: str,
        replacements: dict[str, str],
    ) -> None:
        """色彩プリセットを適用する。

        TextItem の FontColor, OutlineColor, OutlineWidth を差し替え。
        メインテキスト (TITLE/MAIN_TEXT を含む TextItem) と
        サブテキスト (SUBTITLE/SUB_TEXT を含む TextItem) を区別して色を適用する。

        Args:
            project: プロジェクト JSON (変更される)。
            preset_name: プリセット名。
            replacements: プレースホルダーの差し替え結果 (テキスト判定に使用)。
        """
        if preset_name not in COLOR_PRESETS:
            logger.warning(f"不明な色彩プリセット: {preset_name}")
            return

        preset = COLOR_PRESETS[preset_name]
        items = self._get_all_items(project)
        applied = 0

        for item in items:
            item_type = item.get("$type", "")
            if "TextItem" not in item_type:
                continue

            text_val = item.get("Text", "")
            role = self._classify_text_role(text_val, replacements)

            if role == "main":
                item["FontColor"] = preset["main_font_color"]
                item["OutlineColor"] = preset["main_outline_color"]
                item["OutlineWidth"] = preset["main_outline_width"]
                applied += 1
            elif role == "sub":
                item["FontColor"] = preset["sub_font_color"]
                item["OutlineColor"] = preset["sub_outline_color"]
                item["OutlineWidth"] = preset["sub_outline_width"]
                applied += 1

        logger.debug(f"色彩プリセット '{preset_name}' 適用: {applied}件のTextItem")

    @staticmethod
    def _classify_text_role(
        text_val: str,
        replacements: dict[str, str],
    ) -> str | None:
        """TextItem のテキスト内容からメイン/サブを判定する。

        Returns:
            "main", "sub", or None (判定不能)。
        """
        # プレースホルダーがまだ残っている場合 (差し替え前)
        placeholders = _PLACEHOLDER_RE.findall(text_val)
        for ph in placeholders:
            if ph in _MAIN_TEXT_PLACEHOLDERS:
                return "main"
            if ph in _SUB_TEXT_PLACEHOLDERS:
                return "sub"

        # 差し替え後のテキストと比較して判定
        for key, value in replacements.items():
            if key in _MAIN_TEXT_PLACEHOLDERS and value and value in text_val:
                return "main"
            if key in _SUB_TEXT_PLACEHOLDERS and value and value in text_val:
                return "sub"

        return None

    # レイアウトパターン → テンプレート名のマッピング (SP-037 Phase 4)
    PATTERN_TEMPLATE_MAP: dict[str, str] = {
        "A": "center_text",
        "B": "left_image",
        "C": "map_arrow",
        "D": "vertical_split",
        "E": "number_list",
    }

    def generate_from_thumbnail_copy(
        self,
        thumbnail_copy: dict[str, Any],
        output_dir: Path,
        background_image: Path | str | None = None,
        character_image: Path | str | None = None,
        template_name: str | None = None,
    ) -> Path:
        """Gemini生成のサムネイル文言からYMM4プロジェクトを生成する。

        GeminiIntegration.generate_thumbnail_copy() の出力を受け取り、
        推奨パターン・色彩プリセットを適用してサムネイルを生成する。

        Args:
            thumbnail_copy: generate_thumbnail_copy() の出力 dict。
            output_dir: 出力先ディレクトリ。
            background_image: 背景画像パス。
            character_image: キャラクター画像パス。
            template_name: テンプレート名を明示指定する場合。
                None の場合は suggested_pattern からマッピング。

        Returns:
            出力された .y4mmp パス。
        """
        # テンプレート選択: 明示指定 > suggested_pattern > デフォルト
        if template_name is None:
            pattern = thumbnail_copy.get("suggested_pattern", "A")
            template_name = self.PATTERN_TEMPLATE_MAP.get(pattern, "center_text")

        # 利用可能テンプレートの確認
        available = self.discover_templates()
        if template_name not in available:
            if available:
                template_name = available[0]
                logger.warning(
                    f"推奨テンプレート '{template_name}' が見つかりません。"
                    f"'{template_name}' を使用します"
                )
            else:
                raise FileNotFoundError(
                    "サムネイルテンプレートが1つも見つかりません。"
                    "config/thumbnail_templates/ にYMM4テンプレートを配置してください。"
                )

        # プレースホルダー構成
        replacements: dict[str, str] = {
            "MAIN_TEXT": thumbnail_copy.get("main_text", ""),
            "TITLE": thumbnail_copy.get("main_text", ""),
            "SUB_TEXT": thumbnail_copy.get("sub_text", ""),
            "SUBTITLE": thumbnail_copy.get("sub_text", ""),
            "LABEL": thumbnail_copy.get("label", ""),
        }

        if background_image:
            replacements["BACKGROUND"] = str(Path(background_image).resolve())
        if character_image:
            replacements["CHARACTER"] = str(Path(character_image).resolve())

        color_preset = thumbnail_copy.get("suggested_color")

        return self.generate(
            template_name=template_name,
            output_dir=output_dir,
            replacements=replacements,
            color_preset=color_preset,
        )

    def _copy_template_assets(self, template_name: str, output_dir: Path) -> None:
        """テンプレートに付随する素材ファイル (画像等) を出力先にコピーする。

        テンプレートと同名のディレクトリ (config/thumbnail_templates/{name}/)
        が存在する場合、その中身を output_dir にコピーする。
        """
        assets_dir = self.template_dir / template_name
        if not assets_dir.is_dir():
            return

        for asset_file in assets_dir.iterdir():
            if asset_file.is_file():
                dest = output_dir / asset_file.name
                if not dest.exists():
                    shutil.copy2(asset_file, dest)
                    logger.debug(f"テンプレート素材コピー: {asset_file.name}")

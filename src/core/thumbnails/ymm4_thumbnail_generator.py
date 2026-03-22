#!/usr/bin/env python3
"""
YMM4テンプレートベースのサムネイル生成モジュール (SP-037 Phase 3)

ユーザーがYMM4で作成したサムネイルテンプレート (.y4mmp) を読み込み、
可変要素 (テキスト、画像パス、配色) を差し替えて出力する。

ワークフロー:
1. ユーザーがYMM4でサムネイルテンプレートを作成 (1フレーム .y4mmp)
2. テンプレートを config/thumbnail_templates/ に配置
3. パイプラインが本モジュールでテキスト/画像を差し替え
4. 出力: work_dir/thumbnail_project.y4mmp
5. ユーザーがYMM4で開き、1フレームPNG書き出し+レビュー

テンプレート規約:
- TextItem の Text フィールドに {{TITLE}}, {{SUBTITLE}} 等のプレースホルダーを記述
- ImageItem の FilePath に {{BACKGROUND}}, {{CHARACTER}} 等のプレースホルダーを記述
- プレースホルダー名は大文字英字+アンダースコアで {{NAME}} 形式
"""

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
    ) -> Path:
        """テンプレートのプレースホルダーを差し替えて .y4mmp を出力する。

        Args:
            template_name: テンプレート名 (拡張子なし)。
            output_dir: 出力先ディレクトリ。
            replacements: プレースホルダー名 → 値 のマッピング。
                例: {"TITLE": "AI最新動向", "BACKGROUND": "C:/images/bg.png"}
            output_filename: 出力ファイル名。

        Returns:
            出力された .y4mmp のパス。
        """
        data = self.load_template(template_name)

        # ディープコピーして元テンプレートを汚さない
        import copy
        project = copy.deepcopy(data)

        # 全アイテムのプレースホルダーを差し替え
        replaced_count = 0
        items = self._get_all_items(project)
        for item in items:
            replaced_count += self._replace_in_item(item, replacements)

        # FilePath を出力先に更新
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / output_filename
        project["FilePath"] = str(out_path.resolve())

        # 書き出し
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(project, f, ensure_ascii=False, indent=2)

        logger.info(
            f"サムネイルプロジェクト生成: {out_path} "
            f"(テンプレート: {template_name}, 置換: {replaced_count}件)"
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
    ) -> Path:
        """台本データからプレースホルダーを自動構成してサムネイルを生成する。

        パイプライン統合用のヘルパーメソッド。

        Args:
            template_name: テンプレート名。
            script: 台本データ (title, segments)。
            output_dir: 出力先ディレクトリ。
            background_image: 背景画像のパス。
            character_image: キャラクター画像のパス。

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
        )

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

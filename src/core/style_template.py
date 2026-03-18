"""スタイルテンプレートマネージャー (SP-031)

style_template.json の読み込み・検証・複数テンプレート管理を行う。
テンプレートは CsvAssembler と C# プラグイン (YMM4) の双方で参照される。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .utils.logger import logger


# テンプレートの必須セクション
_REQUIRED_SECTIONS = {"subtitle", "speaker_colors", "animation", "timing"}


@dataclass
class StyleTemplate:
    """スタイルテンプレートデータ。"""

    name: str
    description: str = ""
    version: str = "1.0.0"
    video: Dict[str, Any] = field(default_factory=dict)
    subtitle: Dict[str, Any] = field(default_factory=dict)
    speaker_colors: List[str] = field(default_factory=list)
    animation: Dict[str, Any] = field(default_factory=dict)
    bgm: Dict[str, Any] = field(default_factory=dict)
    crossfade: Dict[str, Any] = field(default_factory=dict)
    timing: Dict[str, Any] = field(default_factory=dict)
    thumbnail: Dict[str, Any] = field(default_factory=dict)
    validation: Dict[str, Any] = field(default_factory=dict)
    raw: Dict[str, Any] = field(default_factory=dict)

    def get_speaker_color(self, index: int) -> str:
        """話者インデックスに対応する色を返す (サイクル方式)。"""
        if not self.speaker_colors:
            return "#FFFFFF"
        return self.speaker_colors[index % len(self.speaker_colors)]

    def to_dict(self) -> Dict[str, Any]:
        """テンプレートを辞書に変換する。"""
        result: Dict[str, Any] = {
            "version": self.version,
            "metadata": {"name": self.name, "description": self.description},
            "subtitle": self.subtitle,
            "speaker_colors": self.speaker_colors,
            "animation": self.animation,
            "timing": self.timing,
            "validation": self.validation,
        }
        if self.video:
            result["video"] = self.video
        if self.bgm:
            result["bgm"] = self.bgm
        if self.crossfade:
            result["crossfade"] = self.crossfade
        if self.thumbnail:
            result["thumbnail"] = self.thumbnail
        return result


class StyleTemplateManager:
    """複数のスタイルテンプレートを管理する。

    config/ ディレクトリから style_template*.json を読み込み、
    名前でアクセスできるようにする。
    """

    def __init__(self, config_dir: Optional[Path] = None) -> None:
        """
        Args:
            config_dir: テンプレートJSON群があるディレクトリ。
                None の場合は PROJECT_ROOT/config を使用。
        """
        if config_dir is None:
            config_dir = Path(__file__).parent.parent.parent / "config"
        self.config_dir = config_dir
        self._templates: Dict[str, StyleTemplate] = {}
        self._default_name: str = "default"

    def load_all(self) -> int:
        """config_dir 内の全テンプレートJSONを読み込む。

        Returns:
            読み込んだテンプレート数。
        """
        if not self.config_dir.exists():
            logger.warning(f"テンプレートディレクトリが見つかりません: {self.config_dir}")
            return 0

        count = 0
        for json_path in sorted(self.config_dir.glob("style_template*.json")):
            try:
                template = self.load_file(json_path)
                if template:
                    self._templates[template.name] = template
                    count += 1
            except Exception as e:
                logger.warning(f"テンプレート読み込み失敗: {json_path}: {e}")

        if count > 0:
            logger.info(f"テンプレート {count}件読み込み: {list(self._templates.keys())}")
        return count

    def load_file(self, json_path: Path) -> Optional[StyleTemplate]:
        """単一のテンプレートJSONファイルを読み込む。

        Args:
            json_path: テンプレートJSONファイルパス。

        Returns:
            StyleTemplate。読み込み失敗時は None。
        """
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"テンプレートJSON読み込み失敗: {json_path}: {e}")
            return None

        errors = self.validate_schema(data)
        if errors:
            logger.warning(f"テンプレートスキーマ検証失敗 {json_path}: {errors}")
            return None

        metadata = data.get("metadata", {})
        name = metadata.get("name", json_path.stem)

        template = StyleTemplate(
            name=name,
            description=metadata.get("description", ""),
            version=data.get("version", "1.0.0"),
            video=data.get("video", {}),
            subtitle=data.get("subtitle", {}),
            speaker_colors=data.get("speaker_colors", []),
            animation=data.get("animation", {}),
            bgm=data.get("bgm", {}),
            crossfade=data.get("crossfade", {}),
            timing=data.get("timing", {}),
            thumbnail=data.get("thumbnail", {}),
            validation=data.get("validation", {}),
            raw=data,
        )

        self._templates[name] = template
        return template

    def get(self, name: Optional[str] = None) -> Optional[StyleTemplate]:
        """テンプレートを名前で取得する。

        Args:
            name: テンプレート名。None の場合はデフォルトを返す。

        Returns:
            StyleTemplate。見つからない場合は None。
        """
        if name is None:
            name = self._default_name
        return self._templates.get(name)

    def get_or_default(self, name: Optional[str] = None) -> StyleTemplate:
        """テンプレートを取得。見つからない場合はビルトインデフォルトを返す。"""
        template = self.get(name)
        if template is not None:
            return template
        return self._builtin_default()

    def list_templates(self) -> List[str]:
        """利用可能なテンプレート名一覧を返す。"""
        return sorted(self._templates.keys())

    def set_default(self, name: str) -> bool:
        """デフォルトテンプレートを設定する。"""
        if name in self._templates:
            self._default_name = name
            return True
        return False

    @staticmethod
    def validate_schema(data: Dict[str, Any]) -> List[str]:
        """テンプレートJSONのスキーマを簡易検証する。

        Returns:
            エラーメッセージのリスト。空ならOK。
        """
        errors: List[str] = []

        if not isinstance(data, dict):
            return ["ルートがオブジェクトではありません"]

        for section in _REQUIRED_SECTIONS:
            if section not in data:
                errors.append(f"必須セクション '{section}' がありません")

        subtitle = data.get("subtitle", {})
        if subtitle and not isinstance(subtitle, dict):
            errors.append("subtitle はオブジェクトである必要があります")

        colors = data.get("speaker_colors", [])
        if colors and not isinstance(colors, list):
            errors.append("speaker_colors は配列である必要があります")
        elif colors:
            for i, c in enumerate(colors):
                if not isinstance(c, str) or not c.startswith("#"):
                    errors.append(f"speaker_colors[{i}]: 有効なカラーコードではありません: {c}")

        animation = data.get("animation", {})
        if animation and not isinstance(animation, dict):
            errors.append("animation はオブジェクトである必要があります")

        timing = data.get("timing", {})
        if timing and not isinstance(timing, dict):
            errors.append("timing はオブジェクトである必要があります")

        return errors

    @staticmethod
    def _builtin_default() -> StyleTemplate:
        """ビルトインのデフォルトテンプレートを返す。"""
        return StyleTemplate(
            name="builtin_default",
            description="ビルトインデフォルト (ファイル読み込み失敗時のフォールバック)",
            video={
                "width": 1920,
                "height": 1080,
                "fps": 60,
            },
            subtitle={
                "font_size": 48,
                "y_position_ratio": 0.35,
                "base_point": "CenterBottom",
                "max_width_ratio": 0.9,
                "word_wrap": "Character",
                "bold": True,
                "style": "Border",
                "style_color": "#000000",
            },
            speaker_colors=[
                "#FFFFFF", "#FFFF64", "#64FFFF",
                "#64FF96", "#FFB464", "#C896FF",
            ],
            animation={
                "ken_burns_zoom_ratio": 1.05,
                "zoom_in_ratio": 1.15,
                "zoom_out_ratio": 1.15,
                "pan_zoom_ratio": 1.12,
                "pan_distance_ratio": 0.05,
            },
            bgm={
                "volume_percent": 30,
                "fade_in_seconds": 2.0,
                "fade_out_seconds": 2.0,
                "layer": 0,
            },
            crossfade={
                "enabled": True,
                "duration_seconds": 0.5,
            },
            timing={
                "padding_seconds": 0.3,
                "default_duration_seconds": 3.0,
            },
            validation={
                "max_total_duration_seconds": 3600,
                "warn_gap_threshold_seconds": 1.0,
                "warn_overlap_threshold_seconds": -0.1,
            },
        )


def create_template_variant(
    base: StyleTemplate,
    name: str,
    overrides: Dict[str, Any],
) -> StyleTemplate:
    """既存テンプレートのバリアントを作成する。

    Args:
        base: ベーステンプレート。
        name: 新しいテンプレート名。
        overrides: 上書きする設定辞書。

    Returns:
        新しい StyleTemplate。
    """
    data = base.to_dict()
    for key, value in overrides.items():
        if key in data and isinstance(data[key], dict) and isinstance(value, dict):
            data[key] = {**data[key], **value}
        else:
            data[key] = value

    metadata = data.pop("metadata", {})
    return StyleTemplate(
        name=name,
        description=f"{base.name} ベースのバリアント",
        version=data.pop("version", base.version),
        video=data.get("video", base.video),
        subtitle=data.get("subtitle", base.subtitle),
        speaker_colors=data.get("speaker_colors", base.speaker_colors),
        animation=data.get("animation", base.animation),
        bgm=data.get("bgm", base.bgm),
        crossfade=data.get("crossfade", base.crossfade),
        timing=data.get("timing", base.timing),
        validation=data.get("validation", base.validation),
        raw=data,
    )


def save_template(template: StyleTemplate, output_path: Path) -> Path:
    """テンプレートをJSONファイルに保存する。"""
    data = template.to_dict()
    data["$schema"] = "./style_template_schema.json"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    logger.info(f"テンプレート保存: {template.name} → {output_path}")
    return output_path

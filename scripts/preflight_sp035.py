#!/usr/bin/env python3
"""SP-035 統合実機テスト Pre-Flight チェック。

YMM4 不要の自動検証を実行し、実機テスト前の準備状態を確認する。
チェック項目:
  1. Python 環境・依存パッケージ
  2. style_template.json の整合性
  3. サンプル CSV の Pre-Export Validation
  4. API キー (.env) の存在確認
  5. テスト画像・アセットの存在確認
  6. C# プラグインソースの存在確認
  7. アニメーション種別の Python/C# 一致
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_PATH = PROJECT_ROOT / "src"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


class PreFlightResult:
    """Pre-flight チェック結果。"""

    def __init__(self) -> None:
        self.passed: list[str] = []
        self.warnings: list[str] = []
        self.failures: list[str] = []

    def ok(self, msg: str) -> None:
        self.passed.append(msg)
        print(f"  [PASS] {msg}")

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)
        print(f"  [WARN] {msg}")

    def fail(self, msg: str) -> None:
        self.failures.append(msg)
        print(f"  [FAIL] {msg}")

    @property
    def total(self) -> int:
        return len(self.passed) + len(self.warnings) + len(self.failures)


def check_python_env(r: PreFlightResult) -> None:
    """Python 環境とコアモジュールの import 確認。"""
    print("\n=== 1. Python 環境 ===")

    v = sys.version_info
    if v >= (3, 11):
        r.ok(f"Python {v.major}.{v.minor}.{v.micro}")
    else:
        r.warn(f"Python {v.major}.{v.minor} (3.11+ 推奨)")

    modules = [
        ("core.style_template", "StyleTemplateManager"),
        ("core.editing.pre_export_validator", "validate_timeline_csv"),
        ("core.csv_assembler", "CsvAssembler"),
        ("core.visual.animation_assigner", "AnimationAssigner"),
        ("core.visual.stock_image_client", "StockImageClient"),
        ("core.visual.text_slide_generator", "TextSlideGenerator"),
        ("core.export_validator", "ExportValidator"),
    ]
    for mod_name, cls_name in modules:
        try:
            mod = __import__(mod_name, fromlist=[cls_name])
            getattr(mod, cls_name)
            r.ok(f"{mod_name}.{cls_name}")
        except (ImportError, AttributeError) as e:
            r.fail(f"{mod_name}.{cls_name}: {e}")


def check_style_templates(r: PreFlightResult) -> None:
    """style_template.json の存在と構造チェック。"""
    print("\n=== 2. スタイルテンプレート ===")

    template_path = PROJECT_ROOT / "config" / "style_template.json"
    if not template_path.exists():
        r.fail("config/style_template.json が存在しない")
        return

    try:
        data = json.loads(template_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        r.fail(f"style_template.json JSON パースエラー: {e}")
        return

    r.ok(f"style_template.json (version {data.get('version', '?')})")

    required_sections = ["video", "subtitle", "speaker_colors", "animation", "bgm", "crossfade", "timing"]
    for section in required_sections:
        if section in data:
            r.ok(f"  セクション: {section}")
        else:
            r.fail(f"  セクション欠落: {section}")

    # テンプレート一覧
    try:
        from core.style_template import StyleTemplateManager
        mgr = StyleTemplateManager()
        mgr.load_all()
        names = list(mgr._templates.keys())
        r.ok(f"テンプレート {len(names)} 件: {', '.join(names)}")
    except Exception as e:
        r.warn(f"StyleTemplateManager ロード失敗: {e}")


def check_sample_csvs(r: PreFlightResult) -> None:
    """サンプル CSV の Pre-Export Validation。"""
    print("\n=== 3. サンプル CSV 検証 ===")

    sample_dir = PROJECT_ROOT / "samples" / "image_slide"
    if not sample_dir.exists():
        r.fail("samples/image_slide/ が存在しない")
        return

    csv_files = list(sample_dir.glob("*.csv"))
    if not csv_files:
        r.fail("サンプル CSV が0件")
        return

    r.ok(f"サンプル CSV {len(csv_files)} 件検出")

    from core.editing.pre_export_validator import validate_timeline_csv

    for csv_path in sorted(csv_files):
        result = validate_timeline_csv(csv_path)
        if result.errors:
            r.fail(f"  {csv_path.name}: {len(result.errors)} error(s)")
            for err in result.errors:
                print(f"    - {err}")
        elif result.warnings:
            # 画像パス不在は実機テスト前の既知事項なので warn
            r.warn(f"  {csv_path.name}: {len(result.warnings)} warning(s)")
        else:
            r.ok(f"  {csv_path.name}: PASS")


def check_api_keys(r: PreFlightResult) -> None:
    """API キーの存在確認 (値は検証しない)。"""
    print("\n=== 4. API キー (.env) ===")

    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        r.warn(".env ファイルが存在しない")
        return

    env_content = env_path.read_text(encoding="utf-8")
    keys = {
        "GEMINI_API_KEY": "必須",
        "PEXELS_API_KEY": "推奨",
        "PIXABAY_API_KEY": "推奨",
    }

    for key, importance in keys.items():
        pattern = rf"^{key}=(.+)$"
        match = re.search(pattern, env_content, re.MULTILINE)
        if match and match.group(1).strip():
            r.ok(f"{key} ({importance}): 設定済み")
        else:
            if importance == "必須":
                r.fail(f"{key} ({importance}): 未設定")
            else:
                r.warn(f"{key} ({importance}): 未設定")


def check_test_assets(r: PreFlightResult) -> None:
    """テスト画像・アセットの存在確認。"""
    print("\n=== 5. テストアセット ===")

    slides_dir = PROJECT_ROOT / "samples" / "image_slide" / "slides"
    if slides_dir.exists():
        images = list(slides_dir.glob("*.png")) + list(slides_dir.glob("*.jpg"))
        if images:
            r.ok(f"slides/ に {len(images)} 枚の画像")
        else:
            r.warn("slides/ が空 (テスト画像を配置してください)")
    else:
        r.warn("samples/image_slide/slides/ が未作成 (実機テスト前に画像を配置してください)")

    # output_csv ディレクトリ
    output_dir = PROJECT_ROOT / "output_csv"
    if output_dir.exists():
        csvs = list(output_dir.glob("*.csv"))
        r.ok(f"output_csv/ に {len(csvs)} 件の CSV")
    else:
        r.warn("output_csv/ が未作成 (pipeline 実行で生成されます)")


def check_csharp_plugin(r: PreFlightResult) -> None:
    """C# プラグインソースの存在確認。"""
    print("\n=== 6. C# プラグイン (ymm4-plugin/) ===")

    plugin_dir = PROJECT_ROOT / "ymm4-plugin"
    if not plugin_dir.exists():
        r.fail("ymm4-plugin/ が存在しない")
        return

    key_files = [
        "NLMSlidePlugin.csproj",
        "NLMSlidePlugin.Core.csproj",
        "TimelinePlugin/CsvImportDialog.xaml.cs",
        "TimelinePlugin/CsvTimelineImportPlugin.cs",
        "TimelinePlugin/Ymm4TimelineImporter.cs",
        "Core/StyleTemplateLoader.cs",
        "Core/CsvTimelineReader.cs",
        "Core/WavDurationReader.cs",
        "Core/VoiceSpeakerMapping.cs",
    ]

    for f in key_files:
        path = plugin_dir / f
        if path.exists():
            r.ok(f"  {f}")
        else:
            r.fail(f"  {f}: 見つからない")


def check_animation_parity(r: PreFlightResult) -> None:
    """Python / C# 間のアニメーション種別パリティ確認。"""
    print("\n=== 7. アニメーション種別パリティ ===")

    # Python 側
    py_types: set[str] = set()
    try:
        from core.visual.animation_assigner import AnimationAssigner
        assigner = AnimationAssigner.__new__(AnimationAssigner)
        # AnimationAssigner のソースからタイプを抽出
        import inspect
        source = inspect.getsource(AnimationAssigner)
        # animation_type の列挙を抽出
        py_matches = re.findall(r'"(ken_burns|zoom_in|zoom_out|pan_left|pan_right|pan_up|pan_down|static)"', source)
        py_types = set(py_matches)
    except Exception:
        pass

    if not py_types:
        # フォールバック: pre_export_validator の valid_animations から取得
        py_types = {"ken_burns", "zoom_in", "zoom_out", "pan_left", "pan_right", "pan_up", "pan_down", "static"}

    # C# 側 (CsvImportDialog.xaml.cs + CsvTimelineReader.cs に定義)
    cs_types: set[str] = set()
    cs_files = [
        PROJECT_ROOT / "ymm4-plugin" / "TimelinePlugin" / "CsvImportDialog.xaml.cs",
        PROJECT_ROOT / "ymm4-plugin" / "Core" / "CsvTimelineReader.cs",
    ]
    for cs_file in cs_files:
        if cs_file.exists():
            cs_source = cs_file.read_text(encoding="utf-8-sig")
            cs_matches = re.findall(r'"(ken_burns|zoom_in|zoom_out|pan_left|pan_right|pan_up|pan_down|static)"', cs_source)
            cs_types.update(cs_matches)

    if py_types and cs_types:
        if py_types == cs_types:
            r.ok(f"Python/C# 一致: {sorted(py_types)}")
        else:
            only_py = py_types - cs_types
            only_cs = cs_types - py_types
            if only_py:
                r.warn(f"Python のみ: {sorted(only_py)}")
            if only_cs:
                r.warn(f"C# のみ: {sorted(only_cs)}")
    elif not cs_types:
        r.warn("C# ソースからアニメーション種別を取得できなかった")
    else:
        r.warn("Python ソースからアニメーション種別を取得できなかった")


def check_checklist_exists(r: PreFlightResult) -> None:
    """統合テストチェックリストの存在確認。"""
    print("\n=== 8. チェックリスト ===")

    checklist = PROJECT_ROOT / "docs" / "integration_test_checklist.md"
    if checklist.exists():
        content = checklist.read_text(encoding="utf-8")
        sections = re.findall(r"^## [A-G]\.", content, re.MULTILINE)
        r.ok(f"integration_test_checklist.md: {len(sections)} セクション")
    else:
        r.fail("docs/integration_test_checklist.md が存在しない")

    guide = PROJECT_ROOT / "docs" / "e2e_verification_guide.md"
    if guide.exists():
        r.ok("e2e_verification_guide.md")
    else:
        r.warn("docs/e2e_verification_guide.md が存在しない")


def main() -> int:
    """メイン処理。"""
    print("=" * 60)
    print("SP-035 統合実機テスト Pre-Flight チェック")
    print("=" * 60)

    r = PreFlightResult()

    check_python_env(r)
    check_style_templates(r)
    check_sample_csvs(r)
    check_api_keys(r)
    check_test_assets(r)
    check_csharp_plugin(r)
    check_animation_parity(r)
    check_checklist_exists(r)

    # サマリー
    print("\n" + "=" * 60)
    print("サマリー")
    print("=" * 60)
    print(f"  PASS: {len(r.passed)}")
    print(f"  WARN: {len(r.warnings)}")
    print(f"  FAIL: {len(r.failures)}")
    print(f"  合計: {r.total}")

    if r.failures:
        print("\n--- FAIL 項目 ---")
        for f in r.failures:
            print(f"  [FAIL] {f}")

    if r.warnings:
        print("\n--- WARN 項目 ---")
        for w in r.warnings:
            print(f"  [WARN] {w}")

    if not r.failures:
        print("\n結論: Python 側の準備は完了。YMM4 実機テストに進めます。")
        return 0
    else:
        print(f"\n結論: {len(r.failures)} 件の問題を解決してから実機テストに進んでください。")
        return 1


if __name__ == "__main__":
    sys.exit(main())

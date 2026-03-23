#!/usr/bin/env python3
"""
YMM4テンプレート作成用サンプルCSV生成スクリプト

SP-052 テンプレート作成の前準備として、YMM4にインポートして
動作確認できるサンプルCSVを生成する。

使い方:
  python scripts/generate_sample_csv.py [--output-dir OUTPUT_DIR]

出力:
  {output_dir}/sample_timeline.csv     — 4列CSV (speaker, text, image_path, animation_type)
  {output_dir}/sample_overlay_plan.json — テキストオーバーレイ指示
"""
import argparse
import csv
import json
from pathlib import Path


SAMPLE_SEGMENTS = [
    # 導入
    ("ゆっくり霊夢", "皆さんこんにちは。今日はAI技術の最新動向について解説していきます。", "ken_burns"),
    ("ゆっくり魔理沙", "最近AIの話題が多いけど、実際のところどうなっているのか気になるよね。", "zoom_in"),
    # 本論1
    ("ゆっくり霊夢", "まず、大規模言語モデルの進化について見ていきましょう。2024年から2025年にかけて、GPTシリーズやClaudeなど、多くのモデルが大きく進化しました。", "ken_burns"),
    ("ゆっくり魔理沙", "特にマルチモーダル対応が進んだよね。テキストだけでなく、画像や音声も理解できるようになった。", "zoom_out"),
    ("ゆっくり霊夢", "その通りです。例えばGeminiは、テキスト・画像・音声・動画を統合的に処理できます。", "ken_burns"),
    # 本論2
    ("ゆっくり魔理沙", "次に、AIエージェントの話をしようか。自律的にタスクを実行するAIが注目されている。", "zoom_in"),
    ("ゆっくり霊夢", "AIエージェントは、単なる質問応答を超えて、ツールの使用やウェブブラウジング、コード実行まで行えるようになっています。", "ken_burns"),
    ("ゆっくり魔理沙", "実用化も進んでいて、プログラミングの補助や文書作成、データ分析に使われ始めているんだぜ。", "zoom_out"),
    # まとめ
    ("ゆっくり霊夢", "まとめると、AI技術は急速に進化しており、マルチモーダル対応とエージェント能力の2つが大きなトレンドです。", "ken_burns"),
    ("ゆっくり魔理沙", "今後もAIの進化に注目していこう。それでは、また次の動画で会おうぜ。", "zoom_in"),
]

SAMPLE_OVERLAYS = {
    "version": "1.0",
    "overlays": [
        {
            "type": "chapter_title",
            "text": "AI技術の最新動向 2025",
            "segment_index": 0,
            "duration_sec": 4.0,
            "position": "top_center",
            "style": "default",
        },
        {
            "type": "chapter_title",
            "text": "第1章: 大規模言語モデルの進化",
            "segment_index": 2,
            "duration_sec": 4.0,
            "position": "top_center",
            "style": "default",
        },
        {
            "type": "key_point",
            "text": "マルチモーダル対応: テキスト+画像+音声+動画",
            "segment_index": 3,
            "duration_sec": 7.0,
            "position": "lower_third",
            "style": "default",
        },
        {
            "type": "chapter_title",
            "text": "第2章: AIエージェント",
            "segment_index": 5,
            "duration_sec": 4.0,
            "position": "top_center",
            "style": "default",
        },
        {
            "type": "key_point",
            "text": "ツール使用・ウェブブラウジング・コード実行",
            "segment_index": 6,
            "duration_sec": 7.0,
            "position": "lower_third",
            "style": "default",
        },
        {
            "type": "chapter_title",
            "text": "まとめ",
            "segment_index": 8,
            "duration_sec": 4.0,
            "position": "top_center",
            "style": "default",
        },
    ],
}


def main():
    parser = argparse.ArgumentParser(description="YMM4テンプレート作成用サンプルCSV生成")
    parser.add_argument(
        "--output-dir",
        default="data/sample_output",
        help="出力ディレクトリ (default: data/sample_output)",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # CSV生成 (ヘッダーなし4列: speaker, text, image_path, animation_type)
    csv_path = output_dir / "sample_timeline.csv"
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        for speaker, text, anim in SAMPLE_SEGMENTS:
            # image_path は空欄 (テンプレート検証時は画像なしで確認)
            writer.writerow([speaker, text, "", anim])

    # overlay_plan.json 生成
    overlay_path = output_dir / "sample_overlay_plan.json"
    with open(overlay_path, "w", encoding="utf-8") as f:
        json.dump(SAMPLE_OVERLAYS, f, ensure_ascii=False, indent=2)

    print(f"サンプルCSV生成完了:")
    print(f"  CSV:     {csv_path} ({len(SAMPLE_SEGMENTS)}行)")
    print(f"  Overlay: {overlay_path} ({len(SAMPLE_OVERLAYS['overlays'])}件)")
    print()
    print("YMM4テンプレート作成手順:")
    print("  1. YMM4で新規プロジェクト作成 (1920x1080, 30fps)")
    print("  2. キャラクター設定: ゆっくり霊夢 (右下) + ゆっくり魔理沙 (左下)")
    print("  3. 字幕スタイル設定: フォント・色・位置・アウトライン")
    print("  4. 背景ベース色を設定")
    print(f"  5. {csv_path} をCSVインポート")
    print("  6. 音声合成・字幕が正常に配置されるか確認")
    print("  7. テンプレートとして保存: config/video_templates/default/template.y4mmp")


if __name__ == "__main__":
    main()

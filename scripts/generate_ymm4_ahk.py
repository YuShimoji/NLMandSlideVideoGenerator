#!/usr/bin/env python3
"""YMM4 AutoHotkey スクリプト生成ユーティリティ

slides_payload.json と timeline_plan.json を読み込んで、
YMM4 のタイムライン自動構築を行う AutoHotkey スクリプトを生成します。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


def generate_ahk_script(
    project_dir: Path,
    slides_payload: Dict[str, Any],
    timeline_plan: Dict[str, Any],
) -> str:
    """YMM4 操作用の AutoHotkey スクリプトを生成

    Args:
        project_dir: YMM4プロジェクトディレクトリ
        slides_payload: スライド情報
        timeline_plan: タイムライン計画情報

    Returns:
        生成されたAutoHotkeyスクリプトの内容
    """

    # プロジェクトファイルパス
    project_file = project_dir / "project.y4mmp"

    # AutoHotkeyスクリプトのテンプレート
    ahk_template = f'''#NoEnv
#SingleInstance Force
SetWorkingDir %A_ScriptDir%

; YMM4 自動操作スクリプト
; 生成元: {project_dir}

; プロジェクトファイルを開く
projectFile := "{project_file}"

; YMM4 を起動してプロジェクトを開く
Run, "C:\\Program Files\\YMM4\\YMM4.exe" "%projectFile%"
WinWait, YMM4,, 10
if ErrorLevel {{
    MsgBox, YMM4 が起動しませんでした
    ExitApp
}}

; ウィンドウをアクティブ化
WinActivate, YMM4
WinWaitActive, YMM4,, 5

; 少し待機
Sleep, 2000

; タイムライン操作の開始
'''

    # スライド情報の処理
    segments = slides_payload.get("segments", [])
    for i, segment in enumerate(segments):
        speaker = segment.get("speaker", "")
        text = segment.get("text", "")
        start_time = segment.get("start_time", 0.0)
        end_time = segment.get("end_time", 0.0)

        # AutoHotkeyコマンドの追加
        ahk_template += f'''
; セグメント {i+1}: 話者={speaker}, 開始={start_time}s, 終了={end_time}s
; テキスト: {text[:50]}{"..." if len(text) > 50 else ""}

; タイムラインにテキストを配置（簡易実装）
Send, ^{{a}}  ; 全選択解除
Sleep, 100

; テキスト入力（簡易）
SendInput, {text}
Sleep, 500

; 次のセグメントへ
'''

    # スクリプトの終了部分
    ahk_template += '''
; 操作完了
MsgBox, YMM4 タイムライン構築が完了しました

; スクリプト終了
ExitApp

; エラーハンドリング
OnError:
    MsgBox, エラーが発生しました: %A_LastError%
    ExitApp
'''

    return ahk_template


def main():
    """メイン処理"""
    import argparse

    parser = argparse.ArgumentParser(description="YMM4 AutoHotkeyスクリプト生成")
    parser.add_argument("project_dir", help="YMM4プロジェクトディレクトリ")

    args = parser.parse_args()

    project_dir = Path(args.project_dir)

    # JSONファイルの読み込み
    slides_payload_path = project_dir / "slides_payload.json"
    timeline_plan_path = project_dir / "timeline_plan.json"

    if not slides_payload_path.exists():
        print(f"slides_payload.json が見つかりません: {slides_payload_path}")
        sys.exit(1)

    if not timeline_plan_path.exists():
        print(f"timeline_plan.json が見つかりません: {timeline_plan_path}")
        sys.exit(1)

    try:
        with open(slides_payload_path, 'r', encoding='utf-8') as f:
            slides_payload = json.load(f)

        with open(timeline_plan_path, 'r', encoding='utf-8') as f:
            timeline_plan = json.load(f)

    except Exception as e:
        print(f"JSON読み込みエラー: {e}")
        sys.exit(1)

    # AutoHotkeyスクリプト生成
    ahk_script = generate_ahk_script(project_dir, slides_payload, timeline_plan)

    # スクリプト保存
    ahk_path = project_dir / "ymm4_automation.ahk"
    ahk_path.write_text(ahk_script, encoding='utf-8')

    print(f"AutoHotkeyスクリプトを生成しました: {ahk_path}")
    print(f"実行するには: ahk {ahk_path}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""YMM4 AutoHotkey スクリプト生成ユーティリティ

slides_payload.json と timeline_plan.json を読み込んで、
YMM4 のタイムライン自動構築を行う AutoHotkey スクリプトを生成します。

機能:
- YMM4 ウィンドウ検出・起動待ち
- エラーハンドリング・リトライロジック
- タイムアウト戦略
- ログ・デバッグモード
- 音声ファイルインポート
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime


# AutoHotkey スクリプトのコア部分
AHK_HEADER = '''#NoEnv
#SingleInstance Force
#Warn
SetWorkingDir %A_ScriptDir%
SetBatchLines -1
SendMode Input
SetTitleMatchMode, 2

; ============================================
; YMM4 自動操作スクリプト
; 生成日時: {generated_at}
; プロジェクト: {project_dir}
; ============================================

; 設定
global DEBUG_MODE := {debug_mode}
global LOG_FILE := "{log_file}"
global YMM4_EXE := "{ymm4_exe}"
global PROJECT_FILE := "{project_file}"
global WINDOW_TIMEOUT := {window_timeout}
global OPERATION_DELAY := {operation_delay}
global MAX_RETRIES := {max_retries}

; グローバル変数
global CurrentStep := 0
global TotalSteps := {total_steps}

; ============================================
; ユーティリティ関数
; ============================================

Log(message) {{
    global DEBUG_MODE, LOG_FILE
    timestamp := A_Now
    FormatTime, timestamp, %timestamp%, yyyy-MM-dd HH:mm:ss
    logLine := timestamp . " | " . message
    
    if (DEBUG_MODE) {{
        FileAppend, %logLine%`n, %LOG_FILE%
    }}
    
    ; デバッグモードならツールチップも表示
    if (DEBUG_MODE) {{
        ToolTip, %message%
        SetTimer, RemoveToolTip, -2000
    }}
}}

RemoveToolTip:
    ToolTip
return

UpdateProgress(step, message) {{
    global CurrentStep, TotalSteps
    CurrentStep := step
    progress := Round((step / TotalSteps) * 100)
    Log("Progress: " . progress . "% - " . message)
}}

ShowError(message, fatal := false) {{
    Log("ERROR: " . message)
    MsgBox, 16, YMM4 自動操作エラー, %message%
    if (fatal) {{
        ExitApp, 1
    }}
}}

WaitForWindow(title, timeout := 0) {{
    global WINDOW_TIMEOUT
    if (timeout = 0) {{
        timeout := WINDOW_TIMEOUT
    }}
    
    Log("Waiting for window: " . title . " (timeout: " . timeout . "s)")
    WinWait, %title%,, %timeout%
    
    if (ErrorLevel) {{
        Log("Window not found: " . title)
        return false
    }}
    
    Log("Window found: " . title)
    return true
}}

ActivateWindow(title) {{
    Log("Activating window: " . title)
    WinActivate, %title%
    WinWaitActive, %title%,, 5
    
    if (ErrorLevel) {{
        Log("Failed to activate window: " . title)
        return false
    }}
    
    return true
}}

SafeSend(keys, delay := 100) {{
    global OPERATION_DELAY
    Log("Sending keys: " . keys)
    Send, %keys%
    Sleep, %delay%
    Sleep, %OPERATION_DELAY%
}}

SafeClick(x, y, delay := 200) {{
    global OPERATION_DELAY
    Log("Clicking at: " . x . ", " . y)
    Click, %x%, %y%
    Sleep, %delay%
    Sleep, %OPERATION_DELAY%
}}

RetryOperation(funcName, maxRetries := 0) {{
    global MAX_RETRIES
    if (maxRetries = 0) {{
        maxRetries := MAX_RETRIES
    }}
    
    Loop, %maxRetries% {{
        Log("Attempt " . A_Index . "/" . maxRetries . " for: " . funcName)
        result := %funcName%()
        if (result) {{
            return true
        }}
        Sleep, 1000
    }}
    
    return false
}}

; ============================================
; YMM4 操作関数
; ============================================

LaunchYMM4() {{
    global YMM4_EXE, PROJECT_FILE
    
    Log("Launching YMM4: " . YMM4_EXE)
    
    ; 既存のYMM4プロセスをチェック
    Process, Exist, YMM4.exe
    if (ErrorLevel) {{
        Log("YMM4 is already running (PID: " . ErrorLevel . ")")
        return true
    }}
    
    ; YMM4を起動
    try {{
        Run, "%YMM4_EXE%" "%PROJECT_FILE%"
    }} catch e {{
        ShowError("YMM4 の起動に失敗しました: " . e.Message, true)
        return false
    }}
    
    return true
}}

WaitForYMM4Ready() {{
    global WINDOW_TIMEOUT
    
    Log("Waiting for YMM4 to be ready...")
    
    ; メインウィンドウを待機
    if (!WaitForWindow("YukkuriMovieMaker", WINDOW_TIMEOUT)) {{
        if (!WaitForWindow("YMM4", WINDOW_TIMEOUT)) {{
            ShowError("YMM4 ウィンドウが表示されませんでした", true)
            return false
        }}
    }}
    
    ; アクティブ化
    if (!ActivateWindow("YukkuriMovieMaker")) {{
        if (!ActivateWindow("YMM4")) {{
            ShowError("YMM4 ウィンドウをアクティブ化できませんでした", true)
            return false
        }}
    }}
    
    ; UIの安定を待つ
    Log("Waiting for UI stabilization...")
    Sleep, 3000
    
    return true
}}

'''

AHK_AUDIO_IMPORT = '''
; ============================================
; 音声ファイルインポート
; ============================================

ImportAudioFile(audioPath, startTimeMs) {{
    Log("Importing audio: " . audioPath . " at " . startTimeMs . "ms")
    
    ; ファイルの存在確認
    if (!FileExist(audioPath)) {{
        Log("Audio file not found: " . audioPath)
        return false
    }}
    
    ; タイムラインにフォーカス（F6キーでタイムラインパネルへ）
    SafeSend("{{F6}}", 200)
    
    ; ファイルをドラッグ＆ドロップ（代替: Ctrl+Shift+I でインポートダイアログ）
    SafeSend("^+i", 500)
    
    ; ファイル選択ダイアログを待機
    if (WaitForWindow("開く", 5) || WaitForWindow("Open", 5)) {{
        ; パスを入力
        SafeSend(audioPath, 100)
        SafeSend("{{Enter}}", 500)
        Log("Audio import dialog completed")
        return true
    }}
    
    Log("Audio import dialog not found")
    return false
}}

'''

AHK_EXPORT = '''
; ============================================
; 動画エクスポート
; ============================================

ExportVideo(outputPath) {{
    Log("Exporting video to: " . outputPath)
    
    ; 書き出しダイアログを開く（Ctrl+Shift+E）
    SafeSend("^+e", 1000)
    
    ; ダイアログを待機
    if (!WaitForWindow("動画出力", 10)) {{
        if (!WaitForWindow("Export", 10)) {{
            Log("Export dialog not found")
            return false
        }}
    }}
    
    ; 出力パスを設定
    ; （YMM4のUIに依存するため、座標調整が必要な場合あり）
    SafeSend(outputPath, 100)
    SafeSend("{{Enter}}", 500)
    
    ; 書き出し開始ボタン
    SafeSend("{{Enter}}", 1000)
    
    Log("Export started")
    return true
}}

WaitForExportComplete(timeout := 600) {{
    Log("Waiting for export to complete (timeout: " . timeout . "s)")
    
    ; 進捗ダイアログが閉じるのを待つ
    startTime := A_TickCount
    Loop {{
        if (!WinExist("出力中") && !WinExist("Exporting")) {{
            Log("Export completed")
            return true
        }}
        
        elapsed := (A_TickCount - startTime) / 1000
        if (elapsed > timeout) {{
            Log("Export timeout")
            return false
        }}
        
        Sleep, 5000
    }}
}}

'''

AHK_FOOTER = '''
; ============================================
; メイン処理
; ============================================

Main:
    Log("=== YMM4 自動操作開始 ===")
    UpdateProgress(1, "YMM4 起動中...")
    
    ; YMM4を起動
    if (!LaunchYMM4()) {{
        ShowError("YMM4 の起動に失敗しました", true)
    }}
    
    ; YMM4の準備完了を待機
    UpdateProgress(2, "YMM4 準備待機中...")
    if (!WaitForYMM4Ready()) {{
        ShowError("YMM4 の準備が完了しませんでした", true)
    }}
    
{segment_operations}
    
    ; 完了
    UpdateProgress({total_steps}, "完了")
    Log("=== YMM4 自動操作完了 ===")
    
    MsgBox, 64, YMM4 自動操作, タイムライン構築が完了しました。`n`nログファイル: %LOG_FILE%
    
ExitApp, 0

; ============================================
; エラーハンドラ
; ============================================

OnExit:
    Log("Script terminated")
return
'''


def generate_ahk_script(
    project_dir: Path,
    slides_payload: Dict[str, Any],
    timeline_plan: Dict[str, Any],
    config: Optional[Dict[str, Any]] = None,
) -> str:
    """YMM4 操作用の AutoHotkey スクリプトを生成

    Args:
        project_dir: YMM4プロジェクトディレクトリ
        slides_payload: スライド情報
        timeline_plan: タイムライン計画情報
        config: 追加設定（オプション）

    Returns:
        生成されたAutoHotkeyスクリプトの内容
    """
    config = config or {}
    
    # 設定値
    project_file = project_dir / "project.y4mmp"
    log_file = project_dir / "ymm4_automation.log"
    audio_dir = project_dir / "audio" / "segments"
    
    # セグメント情報を取得
    segments = slides_payload.get("segments", [])
    total_steps = len(segments) + 3  # 起動 + 準備 + 各セグメント + 完了
    
    # セグメント操作コードを生成
    segment_operations = []
    for i, segment in enumerate(segments):
        step_num = i + 3
        audio_file = segment.get("audio_file", "")
        if not audio_file:
            # audio_file がない場合は audio_dir から推測
            audio_file = str(audio_dir / f"{i+1:03d}.wav")
        
        start_time_ms = int(segment.get("start_time", 0) * 1000)
        text = segment.get("text", "")[:50]
        speaker = segment.get("speaker", "")
        
        segment_operations.append(f'''
    ; セグメント {i+1}: {speaker}
    UpdateProgress({step_num}, "セグメント {i+1}/{len(segments)} 処理中...")
    Log("Processing segment {i+1}: {text}...")
    
    ; 音声ファイルをインポート
    audioPath := "{audio_file}"
    if (FileExist(audioPath)) {{
        ImportAudioFile(audioPath, {start_time_ms})
    }} else {{
        Log("Audio file not found, skipping: " . audioPath)
    }}
    
    Sleep, 500
''')
    
    # ヘッダー部分を生成
    header = AHK_HEADER.format(
        generated_at=datetime.now().isoformat(),
        project_dir=str(project_dir).replace("\\", "\\\\"),
        debug_mode="true" if config.get("debug", True) else "false",
        log_file=str(log_file).replace("\\", "\\\\"),
        ymm4_exe=config.get("ymm4_exe", "C:\\\\Program Files\\\\YMM4\\\\YMM4.exe"),
        project_file=str(project_file).replace("\\", "\\\\"),
        window_timeout=config.get("window_timeout", 30),
        operation_delay=config.get("operation_delay", 200),
        max_retries=config.get("max_retries", 3),
        total_steps=total_steps,
    )
    
    # フッター部分を生成
    footer = AHK_FOOTER.format(
        segment_operations="\n".join(segment_operations),
        total_steps=total_steps,
    )
    
    # 全体を結合
    return header + AHK_AUDIO_IMPORT + AHK_EXPORT + footer


def main():
    """メイン処理"""
    import argparse

    parser = argparse.ArgumentParser(
        description="YMM4 AutoHotkeyスクリプト生成",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python generate_ymm4_ahk.py /path/to/ymm4_project
  python generate_ymm4_ahk.py /path/to/ymm4_project --debug --timeout 60
  
設定オプション:
  --ymm4-exe: YMM4実行ファイルパス（デフォルト: C:\\Program Files\\YMM4\\YMM4.exe）
  --timeout: ウィンドウ待機タイムアウト秒数（デフォルト: 30）
  --delay: 操作間の遅延ミリ秒（デフォルト: 200）
  --retries: 最大リトライ回数（デフォルト: 3）
        """
    )
    parser.add_argument("project_dir", help="YMM4プロジェクトディレクトリ")
    parser.add_argument("--debug", action="store_true", help="デバッグモード有効化")
    parser.add_argument("--ymm4-exe", default=None, help="YMM4実行ファイルパス")
    parser.add_argument("--timeout", type=int, default=30, help="ウィンドウ待機タイムアウト秒")
    parser.add_argument("--delay", type=int, default=200, help="操作間遅延ミリ秒")
    parser.add_argument("--retries", type=int, default=3, help="最大リトライ回数")
    parser.add_argument("--run", action="store_true", help="生成後に即座に実行")

    args = parser.parse_args()

    project_dir = Path(args.project_dir)

    if not project_dir.exists():
        print(f"プロジェクトディレクトリが見つかりません: {project_dir}")
        sys.exit(1)

    # JSONファイルの読み込み
    slides_payload_path = project_dir / "slides_payload.json"
    timeline_plan_path = project_dir / "timeline_plan.json"

    # slides_payload は必須ではない（空でも動作可能）
    slides_payload = {}
    if slides_payload_path.exists():
        try:
            with open(slides_payload_path, 'r', encoding='utf-8') as f:
                slides_payload = json.load(f)
            print(f"✓ slides_payload.json を読み込みました")
        except Exception as e:
            print(f"⚠ slides_payload.json の読み込みに失敗: {e}")
    else:
        print(f"⚠ slides_payload.json が見つかりません（スキップ）")

    # timeline_plan も必須ではない
    timeline_plan = {}
    if timeline_plan_path.exists():
        try:
            with open(timeline_plan_path, 'r', encoding='utf-8') as f:
                timeline_plan = json.load(f)
            print(f"✓ timeline_plan.json を読み込みました")
        except Exception as e:
            print(f"⚠ timeline_plan.json の読み込みに失敗: {e}")
    else:
        print(f"⚠ timeline_plan.json が見つかりません（スキップ）")

    # 設定
    config = {
        "debug": args.debug or True,  # デフォルトでデバッグモード
        "window_timeout": args.timeout,
        "operation_delay": args.delay,
        "max_retries": args.retries,
    }
    if args.ymm4_exe:
        config["ymm4_exe"] = args.ymm4_exe

    # AutoHotkeyスクリプト生成
    ahk_script = generate_ahk_script(project_dir, slides_payload, timeline_plan, config)

    # スクリプト保存
    ahk_path = project_dir / "ymm4_automation.ahk"
    ahk_path.write_text(ahk_script, encoding='utf-8')

    print(f"\n✓ AutoHotkeyスクリプトを生成しました: {ahk_path}")
    print(f"\n実行コマンド:")
    print(f"  AutoHotkey.exe \"{ahk_path}\"")
    
    # セグメント情報の表示
    segments = slides_payload.get("segments", [])
    if segments:
        print(f"\nセグメント数: {len(segments)}")
        for i, seg in enumerate(segments[:3]):
            print(f"  {i+1}. {seg.get('speaker', 'N/A')}: {seg.get('text', '')[:30]}...")
        if len(segments) > 3:
            print(f"  ... 他 {len(segments) - 3} セグメント")
    
    # 即座に実行
    if args.run:
        import subprocess
        print(f"\nAutoHotkeyスクリプトを実行中...")
        try:
            subprocess.Popen(["AutoHotkey.exe", str(ahk_path)])
            print("✓ 実行を開始しました")
        except FileNotFoundError:
            print("✗ AutoHotkey.exe が見つかりません。PATH に追加してください。")
        except Exception as e:
            print(f"✗ 実行エラー: {e}")


if __name__ == "__main__":
    main()

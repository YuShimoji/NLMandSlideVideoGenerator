; YMM4 自動操作スクリプト (テンプレート)
; ============================================
; このテンプレートは手動操作用の簡易版です。
; 本番用スクリプトは scripts/generate_ymm4_ahk.py で生成されます。
;
; 使用法:
;   AutoHotkey.exe "ymm4_export.ahk" --project "C:\path\to\project.y4mmp"
;
; 注意: YMM4 の UI 座標や操作は環境によって異なるため、
;       必要に応じて座標や操作を調整してください。
; ============================================

#NoEnv
#SingleInstance Force
#Warn
SetWorkingDir %A_ScriptDir%
SetBatchLines -1
SendMode Input
SetTitleMatchMode, 2

; 設定
global DEBUG_MODE := true
global LOG_FILE := A_ScriptDir . "\ymm4_template.log"

; ============================================
; ユーティリティ関数
; ============================================

Log(message) {
    global DEBUG_MODE, LOG_FILE
    timestamp := A_Now
    FormatTime, timestamp, %timestamp%, yyyy-MM-dd HH:mm:ss
    logLine := timestamp . " | " . message
    
    if (DEBUG_MODE) {
        FileAppend, %logLine%`n, %LOG_FILE%
        ToolTip, %message%
        SetTimer, RemoveToolTip, -2000
    }
}

RemoveToolTip:
    ToolTip
return

ShowError(message, fatal := false) {
    Log("ERROR: " . message)
    MsgBox, 16, YMM4 自動操作エラー, %message%
    if (fatal) {
        ExitApp, 1
    }
}

; ============================================
; コマンドライン引数の処理
; ============================================

projectFile := ""
Loop, %0%
{
    param := %A_Index%
    if (param = "--project") {
        nextIndex := A_Index + 1
        projectFile := %nextIndex%
        break
    }
}

if (projectFile = "") {
    MsgBox, 48, YMM4 自動操作, プロジェクトファイルを指定してください:`n`n--project "path\to\project.y4mmp"
    ExitApp, 1
}

Log("プロジェクトファイル: " . projectFile)

; ============================================
; YMM4 起動
; ============================================

; 既存のYMM4プロセスをチェック
Process, Exist, YMM4.exe
if (ErrorLevel) {
    Log("YMM4 は既に実行中です (PID: " . ErrorLevel . ")")
} else {
    ; YMM4 を起動
    Log("YMM4 を起動中...")
    try {
        Run, "C:\Program Files\YMM4\YMM4.exe" "%projectFile%"
    } catch e {
        ShowError("YMM4 の起動に失敗しました: " . e.Message, true)
    }
}

; YMM4 ウィンドウが表示されるまで待機
Log("YMM4 ウィンドウを待機中...")
WinWait, YukkuriMovieMaker,, 30
if ErrorLevel {
    WinWait, YMM4,, 10
    if ErrorLevel {
        ShowError("YMM4 ウィンドウが表示されませんでした", true)
    }
}

; ウィンドウをアクティブ化
Log("ウィンドウをアクティブ化...")
WinActivate, YukkuriMovieMaker
WinWaitActive, YukkuriMovieMaker,, 5
if ErrorLevel {
    WinActivate, YMM4
    WinWaitActive, YMM4,, 5
    if ErrorLevel {
        ShowError("YMM4 ウィンドウをアクティブ化できませんでした", true)
    }
}

; 起動後の安定化待機
Log("UI 安定化待機中...")
Sleep, 3000

; ============================================
; 操作例（コメントアウト）
; ============================================

; タイムラインにフォーカス（F6キー）
; Send, {F6}
; Sleep, 500

; ファイルインポートダイアログ（Ctrl+Shift+I）
; Send, ^+i
; Sleep, 1000

; 動画出力ダイアログ（Ctrl+Shift+E）
; Send, ^+e
; Sleep, 1000

; ============================================
; 完了
; ============================================

Log("=== テンプレートスクリプト完了 ===")
MsgBox, 64, YMM4 自動操作, YMM4 が起動しました。`n`nこれはテンプレートスクリプトです。`n本番用スクリプトは generate_ymm4_ahk.py で生成してください。`n`nログ: %LOG_FILE%

ExitApp, 0

; エラーハンドラ
OnExit:
    Log("スクリプト終了")
return

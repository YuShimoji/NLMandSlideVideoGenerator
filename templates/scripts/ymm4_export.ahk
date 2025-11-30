; YMM4 自動操作スクリプト (テンプレート)
; このスクリプトは YMM4 のプロジェクトを開いてタイムラインを自動構築します
;
; 使用法:
;   AutoHotkey.exe "C:\path\to\ymm4_automation.ahk" --project "C:\path\to\project.y4mmp"
;
; 注意: YMM4 の UI 座標や操作は環境によって異なるため、
;       必要に応じて座標や操作を調整してください。

#NoEnv
#SingleInstance Force
SetWorkingDir %A_ScriptDir%

; コマンドライン引数の処理
projectFile := ""
Loop, %0%
{{
    param := %A_Index%
    if (param = "--project")
    {{
        projectFile := % A_Index + 1
        break
    }}
}}

if (projectFile = "")
{{
    MsgBox, プロジェクトファイルを指定してください: --project "path\to\project.y4mmp"
    ExitApp
}}

; YMM4 を起動
Run, "C:\Program Files\YMM4\YMM4.exe" "%projectFile%"
if ErrorLevel
{{
    MsgBox, YMM4 の起動に失敗しました
    ExitApp
}}

; YMM4 ウィンドウが表示されるまで待機
WinWait, YMM4,, 15
if ErrorLevel
{{
    MsgBox, YMM4 ウィンドウが表示されませんでした
    ExitApp
}}

; ウィンドウをアクティブ化
WinActivate, YMM4
WinWaitActive, YMM4,, 5
if ErrorLevel
{{
    MsgBox, YMM4 ウィンドウをアクティブ化できませんでした
    ExitApp
}}

; 起動後の安定化待機
Sleep, 3000

; ============================================
; ここに具体的な YMM4 操作を記述
; ============================================

; 例: タイムラインにフォーカスを当てる (座標は環境依存)
; MouseClick, left, 100, 200  ; タイムライン領域をクリック

; 例: テキスト入力
; Send, ^{a}  ; 全選択
; Send, こんにちは世界  ; テキスト入力

; 例: 音声ファイルのインポート (ファイル選択ダイアログ操作)
; Send, ^o  ; ファイルを開く
; Sleep, 1000
; Send, C:\path\to\audio\001.wav{Enter}

; ============================================

; 操作完了メッセージ
MsgBox, 64, YMM4 自動操作, YMM4 のタイムライン自動構築が完了しました

ExitApp

; エラーハンドリング
OnExit:
    ; クリーンアップ処理があればここに
return

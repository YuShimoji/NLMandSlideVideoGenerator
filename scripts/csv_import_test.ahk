; TASK_007 Scenario B manual assist script
#NoEnv
#SingleInstance Force
#Warn
SetWorkingDir %A_ScriptDir%
SetBatchLines -1
SendMode Input
SetTitleMatchMode, 2

global LOG_FILE := A_ScriptDir . "\csv_import_test.log"
global YMM4_PATH := "C:\Users\thank\Downloads\.petmpBE8C53\YukkuriMovieMaker.exe"
global CSV_FILE := "C:\Users\thank\Storage\Media Contents Projects\NLMandSlideVideoGenerator\samples\basic_dialogue\timeline.csv"
global AUDIO_DIR := "C:\Users\thank\Storage\Media Contents Projects\NLMandSlideVideoGenerator\samples\basic_dialogue\audio"

Log(message) {
    global LOG_FILE
    timestamp := A_Now
    FormatTime, timestamp, %timestamp%, yyyy-MM-dd HH:mm:ss
    FileAppend, %timestamp% | %message%`n, %LOG_FILE%
}

Log("Scenario B manual test started")

Process, Exist, YukkuriMovieMaker.exe
if (!ErrorLevel) {
    Run, "%YMM4_PATH%"
    WinWait, YukkuriMovieMaker,, 30
}

guideMessage :=
(
Manual Test Checklist:

1. Open YMM4 -> Settings -> Plugin list.
   Confirm "NLMSlidePlugin" is visible.

2. Open Tools menu -> "CSVタイムラインインポート".

3. Select CSV file:
   %CSV_FILE%

4. Select audio directory:
   %AUDIO_DIR%

5. Run import and verify timeline placement/sync.

6. If an exception occurs, save full stack trace.

Log file:
%LOG_FILE%
)

MsgBox, 64, TASK_007 Scenario B Manual Guide, %guideMessage%
Log("Scenario B manual test guide displayed")
ExitApp, 0

# PowerShellでUTF-8エンコーディングを有効化
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001 | Out-Null

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "サンプル動画生成" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# カレントディレクトリ確認
$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectDir

# 仮想環境確認
Write-Host "`n[準備] 仮想環境確認..." -ForegroundColor Yellow
if (-not (Test-Path "venv\Scripts\activate.ps1")) {
    Write-Host "ERROR: 仮想環境が見つかりません" -ForegroundColor Red
    Write-Host "先に emergency_fix.ps1 を実行してください" -ForegroundColor Red
    Read-Host "Enterキーを押して終了"
    exit 1
}

# 仮想環境アクティベート
& ".\venv\Scripts\activate.ps1"

# ディレクトリ作成
Write-Host "`n[準備] 出力ディレクトリ作成..." -ForegroundColor Yellow
python -c "from config.settings import create_directories; create_directories()" 2>$null

# サンプル1: 基本動画生成
Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "サンプル1: 基本動画生成（字幕なし）" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
python run_modular_demo.py --topic "Python入門" --quality 720p
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: サンプル1の生成に失敗しました" -ForegroundColor Red
    Read-Host "Enterキーを押して終了"
    exit 1
}

# サンプル2: サムネイル付き動画
Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "サンプル2: サムネイル付き動画" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
python run_modular_demo.py --topic "機械学習の基礎" --quality 1080p --thumbnail --thumbnail-style modern
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: サンプル2の生成に失敗しました" -ForegroundColor Red
    Read-Host "Enterキーを押して終了"
    exit 1
}

# サンプル3: 教育スタイルのサムネイル
Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "サンプル3: 教育スタイルのサムネイル" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
python run_modular_demo.py --topic "データサイエンス入門" --quality 1080p --thumbnail --thumbnail-style educational
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: サンプル3の生成に失敗しました" -ForegroundColor Red
    Read-Host "Enterキーを押して終了"
    exit 1
}

Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "すべてのサンプル動画生成完了！" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan

Write-Host "`n生成されたファイルは data フォルダに保存されています:" -ForegroundColor White

# 生成されたファイル一覧表示
if (Test-Path "data\videos\") {
    Write-Host "`n動画ファイル:" -ForegroundColor Yellow
    Get-ChildItem "data\videos\*.mp4" | ForEach-Object {
        Write-Host "  $($_.Name)" -ForegroundColor White
    }
}

if (Test-Path "data\thumbnails\") {
    Write-Host "`nサムネイルファイル:" -ForegroundColor Yellow
    Get-ChildItem "data\thumbnails\*.png" | ForEach-Object {
        Write-Host "  $($_.Name)" -ForegroundColor White
    }
}

Write-Host "`n完了しました！生成された動画を確認してください。" -ForegroundColor Green

Read-Host "`nEnterキーを押して終了"

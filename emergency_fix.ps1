# PowerShellでUTF-8エンコーディングを有効化
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001 | Out-Null

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "NLMandSlideVideoGenerator 緊急修復" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# カレントディレクトリ確認
Write-Host "`n[1/5] 作業ディレクトリ確認..." -ForegroundColor Yellow
$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectDir
Write-Host "作業ディレクトリ: $projectDir" -ForegroundColor Green

# Python確認
Write-Host "`n[2/5] Python確認..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Pythonが見つかりました: $pythonVersion" -ForegroundColor Green
    } else {
        throw "Python not found"
    }
} catch {
    Write-Host "ERROR: Python 3.10以上が見つかりません" -ForegroundColor Red
    Write-Host "以下の手順でPythonをインストールしてください：" -ForegroundColor Red
    Write-Host "1. https://www.python.org/downloads/ を開く" -ForegroundColor White
    Write-Host "2. 'Download Python 3.11.x' をクリック" -ForegroundColor White
    Write-Host "3. インストール時に 'Add Python to PATH' にチェック" -ForegroundColor White
    Write-Host "4. インストール完了後、このスクリプトを再実行" -ForegroundColor White
    Read-Host "Enterキーを押して終了"
    exit 1
}

# 仮想環境作成
Write-Host "`n[3/5] 仮想環境作成..." -ForegroundColor Yellow
if (Test-Path "venv") {
    Remove-Item -Recurse -Force "venv" -ErrorAction SilentlyContinue
}
python -m venv venv --clear
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: 仮想環境の作成に失敗しました" -ForegroundColor Red
    Read-Host "Enterキーを押して終了"
    exit 1
}
Write-Host "仮想環境作成完了" -ForegroundColor Green

# 仮想環境アクティベート
Write-Host "`n[4/5] 仮想環境アクティベート..." -ForegroundColor Yellow
& ".\venv\Scripts\activate.ps1"
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: 仮想環境のアクティベートに失敗しました" -ForegroundColor Red
    Read-Host "Enterキーを押して終了"
    exit 1
}

# 依存関係インストール
Write-Host "`n[5/5] 依存関係インストール..." -ForegroundColor Yellow
python -m pip install --upgrade pip --quiet
pip install requests moviepy pillow pysrt python-dotenv loguru google-generativeai --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: 依存関係のインストールに失敗しました" -ForegroundColor Red
    Write-Host "インターネット接続を確認してください" -ForegroundColor Red
    Read-Host "Enterキーを押して終了"
    exit 1
}

Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "✅ 修復完了！" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan

Write-Host "`n次に以下のコマンドを実行してください：" -ForegroundColor White
Write-Host "  .\generate_sample_videos.ps1" -ForegroundColor White
Write-Host "`nこれで3つのサンプル動画が自動生成されます。" -ForegroundColor White

Read-Host "`nEnterキーを押して終了"

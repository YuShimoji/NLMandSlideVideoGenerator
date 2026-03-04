# New Environment Setup Guide (v1.0)

このプロジェクトを別の端末で動作させるためのセットアップ手順です。

## 1. 動作環境の要件 (Prerequisites)

- **OS**: Windows (YMM4を利用するため)
- **Git**: リポジトリのクローン用
- **Python**: 3.10 以上
- **Node.js**: v18 以上 (Electron アプリ用)

## 2. セットアップ手順 (Setup Steps)

### リポジトリの取得

```powershell
git clone <repository_url>
cd NLMandSlideVideoGenerator
```

### Python 環境の構築

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 外部依存ツールの配置

- **ffmpeg**: パスが通っていることを確認 (`ffmpeg -version`)
- **YMM4**: 最新版（v4.33.0.0以降推奨）をインストール

### Electron アプリの準備

プロジェクトルートの `launch_app.bat` を実行すると、初回起動時に自動で `npm install` が行われます。手動で行う場合は以下の通りです：

```powershell
cd desktop
npm install
```

## 3. アプリの起動 (Running the App)

プロジェクトルートの **`launch_app.bat`** をダブルクリックするだけです。

## 4. トラブルシューティング (Troubleshooting)

- **サーバーが起動しない**: `venv` 内に `streamlit` が正しくインストールされているか確認してください。
- **動画が生成されない**: `ffmpeg` のパスを確認してください。
- **YMM4連携**: 設定画面 (`Settings`) で YMM4 のパスやプラグイン設定を確認してください。

# NLM Slide Video Generator - Desktop App

`desktop/` ディレクトリは Electron ベースのデスクトップアプリケーションです。

## クイックスタート

### 方法1: バッチファイル（最も簡単）

プロジェクトルートの `launch_app.bat` をダブルクリックしてください。
初回は自動的に依存関係がインストールされます。

### 方法2: コマンドライン

```powershell
cd desktop
npm install   # 初回のみ
npm start
```

## ビルド（配布用 .exe 作成）

```powershell
cd desktop
npm run build
```

`desktop/dist/` に portable exe が生成されます。

## アーキテクチャ

```
Electron (main.js)
  ├── splash.html      ← 起動中のスプラッシュ画面
  ├── BrowserWindow    ← Streamlit UI を表示
  └── child_process    ← Python/Streamlit サーバーを管理
```

- アプリ起動時に Python venv 内の Streamlit を自動起動
- サーバーが Ready になったらメインウィンドウを表示
- アプリ終了時にサーバーも自動停止

# 🐍 Python正しいインストールガイド

## ⚠️ 現在の状況

**問題:** 現在のシステムでは、Pythonが「Windows Store」のリダイレクトになっており、実際のPythonがインストールされていません。

```powershell
PS> python --version
Python  # ← 何も表示されない = 本体がインストールされていない
```

これは、Windowsの設定で「アプリ実行エイリアス」が有効になっているためです。

---

## ✅ 解決手順（5分程度）

### Step 1: Windows Storeエイリアスを無効化

1. **設定を開く**
   - Windowsキー + I → 「設定」を開く
   - または「スタートメニュー」→「設定」

2. **アプリ実行エイリアスを無効化**
   - 「アプリ」→「アプリと機能」→「アプリ実行エイリアス」
   - または検索バーで「アプリ実行エイリアス」を検索
   
3. **Pythonエイリアスをオフにする**
   - 「App Installer - python.exe」→ **オフ**
   - 「App Installer - python3.exe」→ **オフ**

### Step 2: Python 3.10以上をインストール

1. **公式サイトからダウンロード**
   - ブラウザで開く: https://www.python.org/downloads/
   - 「Download Python 3.11.x」ボタンをクリック（最新の安定版）
   - `python-3.11.x-amd64.exe` がダウンロードされる

2. **インストール実行**
   - ダウンロードしたexeファイルをダブルクリック
   
3. **重要：インストール設定**
   ```
   ⚠️ 最初の画面で必ずチェック：
   
   ✅ Add Python 3.11 to PATH  ← 必須！
   ✅ Install for all users    ← 推奨
   
   その後「Install Now」をクリック
   ```

4. **インストール完了確認**
   - **新しいPowerShellを開く**（重要！）
   - 以下を実行：
   
   ```powershell
   python --version
   # 出力例: Python 3.11.5
   
   pip --version
   # 出力例: pip 23.x.x from ...
   ```

---

## 🚀 インストール後の手順

### Step 3: プロジェクトセットアップ

新しいPowerShellで以下を実行：

```powershell
# プロジェクトフォルダに移動
cd C:\Users\PLANNER007\NLMandSlideVideoGenerator

# 自動セットアップ実行
.\setup_quick.bat
```

これで以下が自動で完了します：
- ✅ 仮想環境作成
- ✅ 依存関係インストール
- ✅ 環境準備完了

### Step 4: サンプル動画生成

```powershell
# 3つのサンプル動画を自動生成
.\generate_sample_videos.bat
```

または手動で：

```powershell
# 仮想環境アクティベート
venv\Scripts\activate

# 基本動画生成
python run_modular_demo.py --topic "Python入門"

# サムネイル付き高品質動画
python run_modular_demo.py --topic "機械学習の基礎" --quality 1080p --thumbnail
```

---

## 🔍 トラブルシューティング

### Q1: インストール後も `python --version` が表示されない

**A:** 環境変数PATHに追加されていません

1. **手動でPATHを追加：**
   - Windowsキー + R → `sysdm.cpl` → Enter
   - 「詳細設定」タブ → 「環境変数」
   - 「システム環境変数」の「Path」を選択 → 「編集」
   - 「新規」をクリック → 以下を追加：
     ```
     C:\Python311
     C:\Python311\Scripts
     ```
   - すべてのウィンドウで「OK」
   - **PowerShellを再起動**

### Q2: `python` は動くが `pip` が使えない

**A:** Pythonインストール時に含まれるはずですが、以下で再インストール：

```powershell
python -m ensurepip --upgrade
```

### Q3: 仮想環境のアクティベートでエラー

**A:** PowerShellの実行ポリシーが制限されています

```powershell
# 管理者としてPowerShellを開く
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# その後、通常のPowerShellで再実行
venv\Scripts\activate
```

---

## 📋 推奨インストール設定まとめ

| 項目 | 設定 |
|------|------|
| Pythonバージョン | 3.10 または 3.11 |
| インストール先 | `C:\Python311` |
| PATH追加 | ✅ 必須 |
| すべてのユーザー | ✅ 推奨 |
| pip | ✅ 自動インストール |
| Documentation | □ オプション |
| Test Suite | □ オプション |

---

## ✨ 完了後の確認コマンド

新しいPowerShellで実行：

```powershell
# Python確認
python --version      # → Python 3.11.x

# pip確認
pip --version         # → pip 23.x.x

# プロジェクトフォルダ移動
cd C:\Users\PLANNER007\NLMandSlideVideoGenerator

# セットアップ実行
.\setup_quick.bat     # → 自動セットアップ

# サンプル生成
.\generate_sample_videos.bat  # → 3つの動画生成
```

---

## 🎯 完了後に生成されるもの

```
data/
├── videos/
│   ├── generated_video_20241231_140000.mp4  # サンプル1
│   ├── generated_video_20241231_140500.mp4  # サンプル2
│   └── generated_video_20241231_141000.mp4  # サンプル3
├── thumbnails/
│   ├── thumbnail_20241231_140000_modern.png
│   ├── thumbnail_20241231_140500_modern.png
│   └── thumbnail_20241231_141000_educational.png
└── audio/
    └── （各動画の音声ファイル）
```

---

## 📞 サポート

正しくインストールできない場合は、以下の情報を確認してください：

```powershell
# システム情報
systeminfo | findstr /B /C:"OS"

# Python検索
where python

# 環境変数PATH確認
$env:Path -split ';' | Select-String python
```

---

**このガイドに従ってPythonをインストール後、`setup_quick.bat` と `generate_sample_videos.bat` を実行してください！**

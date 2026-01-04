# 🚀 セットアップとサンプル動画生成ガイド

## ⚠️ 現在の問題と解決策

### 問題：Pythonが正しくインストールされていない
現在のシステムでは、Pythonが「Windows Store」のリダイレクトになっており、実際のPythonがインストールされていません。

### 解決手順

#### Step 1: Python 3.10以上をインストール

1. **公式サイトからダウンロード**
   - https://www.python.org/downloads/
   - "Download Python 3.10.x" または "Download Python 3.11.x" をクリック

2. **インストール時の重要設定**
   - ✅ **必ずチェック**: "Add Python to PATH"
   - ✅ **推奨**: "Install for all users" 
   - インストール先: `C:\Python310` または `C:\Python311`

3. **インストール確認**
   ```powershell
   # PowerShellで確認
   py -3.10 --version
   # または
   py -3.11 --version
   ```

#### Step 2: 自動セットアップ実行

```batch
# プロジェクトフォルダで実行
setup_quick.bat
```

このスクリプトが自動で：
- ✅ Pythonの確認
- ✅ 仮想環境作成（venv）
- ✅ pipのアップグレード
- ✅ 依存関係インストール

#### Step 3: サンプル動画生成

```batch
# 3つのサンプル動画を自動生成
generate_sample_videos.bat
```

生成されるサンプル：
1. **基本動画** - Python入門（720p）
2. **モダンサムネイル付き** - 機械学習の基礎（1080p）
3. **教育スタイル** - データサイエンス入門（1080p）

---

## 🎬 手動での動画生成

### 基本コマンド

```batch
# 仮想環境アクティベート
venv\Scripts\activate

# 基本的な動画生成
python run_modular_demo.py --topic "あなたのトピック"

# 高品質 + サムネイル
python run_modular_demo.py --topic "あなたのトピック" --quality 1080p --thumbnail

# すべてのオプション
python run_modular_demo.py ^
  --topic "AI技術の最新動向" ^
  --quality 1080p ^
  --thumbnail ^
  --thumbnail-style modern
```

### サムネイルスタイル

- `modern` - モダンなダークブルー背景
- `classic` - クラシックな白背景
- `gaming` - ゲーミングスタイル
- `educational` - 教育向けスタイル

---

## 🔧 トラブルシューティング

### Q: "python: コマンドが見つかりません"

**A:** Pythonが正しくインストールされていません
```powershell
# 確認
py --version

# インストールされていない場合
# https://www.python.org/downloads/ からインストール
```

### Q: "pip: コマンドが見つかりません"

**A:** 仮想環境がアクティベートされていません
```batch
venv\Scripts\activate
```

### Q: "ImportError: No module named 'xxx'"

**A:** 依存関係が正しくインストールされていません
```batch
pip install -r requirements.txt
```

### Q: 動画生成でエラーが発生する

**A:** 以下を確認：
1. MoviePyがインストールされているか
2. ffmpegが利用可能か
3. 十分なディスク容量があるか

```batch
# MoviePyのテスト
python -c "import moviepy.editor as mp; print('OK')"
```

---

## 📊 生成される動画の仕様

| 項目 | 仕様 |
|------|------|
| 解像度 | 480p / 720p / 1080p |
| フレームレート | 30fps |
| コーデック | H.264 + AAC |
| 字幕 | SRT形式（自動生成） |
| サムネイル | 1280x720 PNG |
| 推定時間 | 5-15分 |

---

## 🎯 API連携（オプション）

より高度な動画生成には以下のAPIキーが必要です：

### 必須APIキー（フル機能使用時）

1. **Gemini API** - スクリプト自動生成
   - https://makersuite.google.com/app/apikey
   - `.env`に設定: `GEMINI_API_KEY=your_key`

2. **TTS API**（いずれか1つ）
   - OpenAI: https://platform.openai.com/api-keys
   - ElevenLabs: https://elevenlabs.io/
   - Azure Speech: https://azure.microsoft.com/ja-jp/services/cognitive-services/speech-services/

3. **YouTube API**（アップロード時）
   - Google Cloud Console: https://console.cloud.google.com/
   - YouTube Data API v3を有効化

### .env設定例

```env
# .envファイル
GEMINI_API_KEY=your_gemini_api_key
OPENAI_API_KEY=your_openai_api_key
YOUTUBE_API_KEY=your_youtube_api_key
TTS_PROVIDER=openai
```

---

## 🚀 クイックスタート（APIなし）

APIキーなしでも基本的な動画生成が可能です：

```batch
# セットアップ
setup_quick.bat

# モック音声での動画生成
venv\Scripts\activate
python run_modular_demo.py --topic "テスト動画"
```

この場合、NotebookLMモック実装により以下が生成されます：
- ✅ プレースホルダー音声
- ✅ 自動生成スライド
- ✅ 基本的な動画合成
- ✅ サムネイル生成

---

## 📁 ファイル構造

```
NLMandSlideVideoGenerator/
├── setup_quick.bat              # 自動セットアップ
├── generate_sample_videos.bat   # サンプル動画生成
├── run_modular_demo.py          # メイン実行スクリプト
├── requirements.txt             # 依存関係
├── .env                         # API設定（手動作成）
└── data/                        # 生成物
    ├── audio/                   # 音声ファイル
    ├── videos/                  # 動画ファイル
    ├── thumbnails/              # サムネイル
    └── transcripts/             # 文字起こし
```

---

## 💡 次のステップ

1. ✅ **setup_quick.bat を実行** - 環境準備
2. ✅ **generate_sample_videos.bat を実行** - サンプル生成
3. ✅ **生成された動画を確認** - `data\videos\` フォルダ
4. ⚙️ **APIキーを設定** - より高度な機能を使用
5. 🎬 **カスタム動画を生成** - 独自のトピックで実行

---

## 🆘 サポート

問題が解決しない場合：

1. **ログ確認**: `logs/app.log`
2. **テスト実行**: `python -m pytest tests/test_basic.py -v`
3. **デバッグモード**: `python run_debug_test.py`

---

**セットアップ完了後、`generate_sample_videos.bat` を実行して複数のサンプル動画を生成してください！**

# TASK_007 シナリオA実装設計書

**タスク**: CSVタイムライン読み込み機能（シナリオA）実装  
**作成日**: 2026-02-03  
**ステータス**: 実装完了・テスト待ち  
**関連**: TASK_007_YMM4PluginIntegration.md

---

## 1. 概要

シナリオAは、CSVタイムライン（話者,テキスト形式）と対応するWAV音声ファイル（001.wav, 002.wav...）をYMM4にインポートする機能です。

### 1.1 実装範囲

- ✅ CSVパーサー（UTF-8対応、ダブルクォート対応）
- ✅ WAVファイル紐付け（行番号対応）
- ✅ タイムライン時刻計算（開始・終了時刻）
- ✅ WPFインポートダイアログ
- ⏳ YMM4 API連携（タイムライン追加）- 要実機確認

---

## 2. アーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│                    CSV Import Dialog (WPF)                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ CSV選択     │  │ 音声DIR選択 │  │ プレビュー/インポート│  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              CsvTimelineReader (Core)                        │
│  - UTF-8読み込み                                             │
│  - CSVパース（ダブルクォート対応）                           │
│  - 行番号管理（1→001.wav）                                  │
│  - 時刻計算（開始→終了）                                    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Ymm4TimelineImporter (YMM4連携)                 │
│  - ボイスキャラクター解決                                    │
│  - タイムラインAPI呼び出し（要実機確認）                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. コンポーネント詳細

### 3.1 CsvTimelineItem (モデル)

| プロパティ | 型 | 説明 |
|-----------|-----|------|
| LineNumber | int | CSV行番号（1-based） |
| Speaker | string | 話者名 |
| Text | string | テロップテキスト |
| AudioFileName | string | {LineNumber:D3}.wav |
| AudioFilePath | string? | 音声ファイルフルパス |
| Duration | double? | 音声長（秒） |
| StartTime | double | タイムライン開始時刻（秒） |
| EndTime | double | タイムライン終了時刻（秒） |

### 3.2 CsvTimelineReader (パーサー)

**機能**:
- UTF-8エンコーディング対応
- CSVパース（カンマ区切り、ダブルクォート対応）
- 空行スキップ
- 音声ファイル存在確認
- タイムライン時刻自動計算

**入力**: CSVパス、音声ディレクトリ（オプション）  
**出力**: `List<CsvTimelineItem>`

### 3.3 CsvImportDialog (UI)

**機能**:
- CSVファイル選択（OpenFileDialog）
- 音声ディレクトリ選択
- インポートオプション（字幕追加/スキップ）
- プレビュー表示（DataGrid）
- ステータス表示

---

## 4. CSVフォーマット対応

### 4.1 基本形式

```csv
Speaker1,こんにちは
Speaker2,こんにちは、今日もよろしく
ナレーター,では始めましょう
```

### 4.2 音声ファイル対応

```
audio_folder/
├── 001.wav  ← CSV行1の音声
├── 002.wav  ← CSV行2の音声
├── 003.wav  ← CSV行3の音声
└── ...
```

### 4.3 ダブルクォート対応

```csv
Speaker1,"カンマ,を含むテキスト"
Speaker2,"クォート""エスケープ""対応"
```

---

## 5. 話者→ボイスマッピング

```csharp
var mapping = new Dictionary<string, string>
{
    { "ずんだもん", "Zundamon" },
    { "四国めたん", "ShikokuMetan" },
    { "ナレーター", "Yukari" },
    { "まりさ", "Marisa" },
    { "れいむ", "Reimu" }
};
```

---

## 6. 実装ファイル一覧

| ファイル | 説明 |
|---------|------|
| `Core/CsvTimelineReader.cs` | CSVパーサー、モデル定義 |
| `TimelinePlugin/CsvTimelineImportPlugin.cs` | プラグインエントリ |
| `TimelinePlugin/Ymm4TimelineImporter.cs` | YMM4連携ロジック |
| `TimelinePlugin/CsvImportDialog.xaml` | WPFダイアログUI |
| `TimelinePlugin/CsvImportDialog.xaml.cs` | ダイアロジコードビハインド |
| `VoicePlugin/CsvTimelineVoicePlugin.cs` | 更新済み（IPlugin実装） |

---

## 7. ビルド手順

```powershell
cd ymm4-plugin
dotnet build
```

**成功時**: DLLが `$(YMM4DirPath)user\plugin\NLMSlidePlugin\` にコピーされる

---

## 8. 制限事項・TODO

### 8.1 現在の制限

1. **音声長の計算**: 現在は固定値（3秒）。NAudio等を使用して実測予定
2. **YMM4 API連携**: タイムライン追加部分はシミュレーション。実機で要確認
3. **ボイスマッピング**: ハードコード。設定ファイル化予定

### 8.2 今後の拡張

- [ ] 音声長の自動計算（NAudio統合）
- [ ] YMM4タイムラインAPI実装（実機確認後）
- [ ] 字幕スタイル設定
- [ ] バッチインポート（複数CSV）
- [ ] 進捗表示

---

## 9. テスト手順

### 9.1 単体テスト

```powershell
# ビルド確認
dotnet build

# 構文チェック
dotnet build --verbosity detailed
```

### 9.2 実機テスト（YMM4環境が必要）

1. YMM4起動
2. 設定→プラグイン→CSV Timeline Voiceを確認
3. CSVインポートダイアログを開く
4. サンプルCSVと音声を選択
5. プレビュー確認
6. インポート実行

---

## 10. コミット予定

```
feat(ymm4): シナリオA CSVタイムライン読み込み実装

- CSVパーサー（UTF-8、ダブルクォート対応）
- WAVファイル紐付け（行番号対応）
- タイムライン時刻計算
- WPFインポートダイアログ
- 話者→ボイスマッピング

Relates to TASK_007
```

---

**設計者**: Cascade  
**レビュー待ち**: YMM4実機テスト

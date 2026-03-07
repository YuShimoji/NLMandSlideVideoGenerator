# NLMSlidePlugin - YMM4 プラグイン

YMM4（ゆっくりMovieMaker4）のプラグインAPIを使用して、NotebookLM台本からの自動タイムライン・音声連携を実現するプラグインです。

## ステータス

✅ **シナリオA実装完了** (v0.2.1)

- CSVタイムライン読み込み
- WAVファイル紐付け（001.wav形式）
- タイムライン時刻自動計算
- 話者→ボイスマッピング
- WPFインポートダイアログ
- YMM4プラグインインターフェース実装

## 前提条件

- **Windows 10/11**
- **.NET 9.0 SDK** （YMM4 プラグイン対応）
- **Visual Studio 2022** または互換IDE
- **YMM4** インストール済み（v4.33.0.0以降推奨）

## セットアップ手順

### 1. Directory.Build.props の設定

```powershell
# サンプルをコピー
cp Directory.Build.props.sample Directory.Build.props
```

`Directory.Build.props` を編集し、YMM4のインストールフォルダを設定:

```xml
<Project>
  <PropertyGroup>
    <YMM4DirPath>C:\Users\YourUserName\AppData\Local\YukkuriMovieMaker4\</YMM4DirPath>
  </PropertyGroup>
</Project>
```

### 2. ビルド

```powershell
cd ymm4-plugin
dotnet build
```

ビルド成功後、DLLは `$(YMM4DirPath)user\plugin\NLMSlidePlugin\` にコピーされます。

### 3. 動作確認

1. YMM4を起動
2. `設定` → `プラグイン` → `プラグイン一覧` で「NLM Slide Plugin」を確認
3. `ツール` → `CSV Timeline Import` を確認
4. `ツール` に表示されない場合は `ツール` → `設定` → `CSV Timeline Import` から `Open CSV Import Dialog` を使う

## プロジェクト構成

```
ymm4-plugin/
├── NLMSlidePlugin.csproj        # プロジェクト定義
├── Directory.Build.props.sample # 設定テンプレート
├── PluginInfo.cs                # プラグインメタデータ
├── VoicePlugin/
│   └── CsvTimelineVoicePlugin.cs   # IVoicePlugin実装（スケルトン）
└── TextCompletionPlugin/
    └── CsvScriptCompletionPlugin.cs # テキスト補完・校正（Gemini API）
```

## 実装予定のプラグインインターフェース

| インターフェース | 用途 | ステータス |
|-----------------|------|-----------|
| `IPlugin` | 基本プラグイン情報 | ✅ 実装済み |
| `IToolPlugin` | ツールウィンドウ統合 | ✅ 実装済み |
| `IPluginMenuItem` | 旧メニュー統合（v4.33+非推奨） | ⏸ 廃止 |
| `IVoicePlugin` | ボイス生成 | 🚧 スケルトン |
| `ITextCompletionPlugin` | テキスト補完・校正 | ✅ 実装済み (Gemini API) |
| `IAudioFileSourcePlugin` | 外部WAVインポート | ⏳ 予定 |

## PoC ゴール

1. **Phase 1**: プラグインがYMM4に読み込まれることを確認
2. **Phase 2**: 外部CSVファイルを読み込み、タイムラインにアイテムを追加
3. **Phase 3**: 生成された音声WAVファイルとの連携

## Gemini API キー設定（テキスト補完機能）

CsvScriptCompletionPlugin は Gemini API を利用して台本テキストの校正・補完を行います。

### 1. API キーの取得

1. [Google AI Studio](https://aistudio.google.com/) にアクセス
2. 「Get API key」→「Create API key」でキーを生成
3. 無料枠: 15 RPM / 100万トークン/日（2026年3月時点）

### 2. 環境変数の設定

**PowerShell（一時的）:**
```powershell
$env:GEMINI_API_KEY = "your_api_key_here"
```

**システム環境変数（永続的）:**
```powershell
[Environment]::SetEnvironmentVariable("GEMINI_API_KEY", "your_api_key_here", "User")
```

**YMM4 から使う場合:**
YMM4 はシステム環境変数を読み込むため、上記の永続的な設定が必要です。
設定後、YMM4 を再起動してください。

### 3. フォールバック動作

API キー未設定時やAPI呼び出し失敗時は、入力テキストをそのまま返します（エラーにはなりません）。

## 開発ガイド

### デバッグ方法

1. Visual Studioでソリューションを開く
2. `NLMSlidePlugin` を右クリック → `スタートアッププロジェクトに設定`
3. デバッグプロファイルでYMM4.exeを指定
4. F5でデバッグ開始

### 参照追加

YMM4の追加アセンブリが必要な場合、`.csproj`の`<ItemGroup>`に追加:

```xml
<Reference Include="YukkuriMovieMaker.Controls">
  <HintPath>$(YMM4DirPath)YukkuriMovieMaker.Controls.dll</HintPath>
</Reference>
```

## 関連ドキュメント

- [YMM4 API Docs](https://ymm-api-docs.vercel.app/)
- [プラグインサンプル集](https://github.com/manju-summoner/YukkuriMovieMaker4PluginSamples)
- [本プロジェクトのYMM4連携設計](../docs/ymm4_integration_arch.md)
- [YMM4 PoC計画](../docs/ymm4_poc_plan.md)

## ライセンス

本プロジェクトのライセンスに準拠。

# NLMSlidePlugin - YMM4 プラグイン

YMM4（ゆっくりMovieMaker4）のプラグインAPIを使用して、NotebookLM台本からの自動タイムライン・音声連携を実現するプラグインです。

## ステータス

🚧 **開発中 - スケルトン段階**

現在はプロジェクト構造とスタブ実装のみ。実際の機能は今後のPoCで実装予定。

## 前提条件

- **Windows 10/11**
- **.NET 10 SDK** （YMM4 プラグインサンプルに追随）
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

## プロジェクト構成

```
ymm4-plugin/
├── NLMSlidePlugin.csproj        # プロジェクト定義
├── Directory.Build.props.sample # 設定テンプレート
├── PluginInfo.cs                # プラグインメタデータ
├── VoicePlugin/
│   └── CsvTimelineVoicePlugin.cs   # IVoicePlugin実装（スケルトン）
└── TextCompletionPlugin/
    └── CsvScriptCompletionPlugin.cs # ITextCompletionPlugin実装（スケルトン）
```

## 実装予定のプラグインインターフェース

| インターフェース | 用途 | ステータス |
|-----------------|------|-----------|
| `IPlugin` | 基本プラグイン情報 | ✅ 実装済み |
| `IVoicePlugin` | ボイス生成 | 🚧 スケルトン |
| `ITextCompletionPlugin` | テキスト補完・校正 | 🚧 スケルトン |
| `IAudioFileSourcePlugin` | 外部WAVインポート | ⏳ 予定 |
| `IVideoFileSourcePlugin` | 動画ソース連携 | ⏳ 予定 |

## PoC ゴール

1. **Phase 1**: プラグインがYMM4に読み込まれることを確認
2. **Phase 2**: 外部CSVファイルを読み込み、タイムラインにアイテムを追加
3. **Phase 3**: 生成された音声WAVファイルとの連携

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

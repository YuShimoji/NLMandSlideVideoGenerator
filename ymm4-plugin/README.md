# NLMSlidePlugin - YMM4 プラグイン

YMM4（ゆっくりMovieMaker4）のプラグインAPIを使用して、NotebookLM台本からの自動タイムライン・音声連携を実現するプラグインです。

## ステータス

✅ **シナリオZero実装完了**

基本プラグイン（IPlugin）実装済み。YMM4でのロード確認が可能です。  
音声・字幕連携機能は今後のPoCで実装予定。

## 前提条件

- **Windows 10/11**
- **.NET 10 SDK** （YMM4 プラグインサンプルに追随）
- **Visual Studio 2022** または互換IDE
- **YMM4** インストール済み（v4.33.0.0以降推奨）

## クイックスタート

**詳細なセットアップ手順は [`SETUP_GUIDE.md`](./SETUP_GUIDE.md) を参照してください。**

### 1. 前提条件

- .NET 10 SDK以降
- YMM4 v4.33.0.0以降

### 2. セットアップ（自動）

```cmd
cd ymm4-plugin
setup_build_props.bat
```

YMM4のインストールパスを入力してください。

### 3. ビルド

```cmd
build_plugin.bat
```

### 4. 動作確認

1. YMM4を起動
2. `設定` → `プラグイン` → `プラグイン一覧` で「NLM Slide Plugin」を確認

**トラブルシューティング**: [`SETUP_GUIDE.md`](./SETUP_GUIDE.md) のトラブルシューティングセクションを参照

## プロジェクト構成

```
ymm4-plugin/
├── NLMSlidePlugin.csproj           # プロジェクト定義
├── Directory.Build.props.sample    # 設定テンプレート
├── Directory.Build.props           # ビルド設定（gitignore対象）
├── PluginInfo.cs                   # プラグインメタデータ（IPlugin実装）
├── VoicePlugin/
│   └── CsvTimelineVoicePlugin.cs   # IVoicePlugin実装（スケルトン）
├── TextCompletionPlugin/
│   └── CsvScriptCompletionPlugin.cs # ITextCompletionPlugin実装（スケルトン）
├── setup_build_props.bat           # セットアップスクリプト
├── build_plugin.bat                # ビルドスクリプト
├── SETUP_GUIDE.md                  # 詳細セットアップガイド
└── README.md                       # 本ドキュメント
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

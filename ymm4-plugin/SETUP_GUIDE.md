# YMM4プラグイン セットアップガイド

最終更新: 2025-12-17  
対象: TASK_007 シナリオZero実装

---

## 📋 前提条件

### 必須
- **Windows 10/11** (64-bit)
- **.NET 10 SDK** 以降
  - ダウンロード: https://dotnet.microsoft.com/download
- **YMM4 (ゆっくりMovieMaker4)** v4.33.0.0以降
  - 公式サイト: https://manjubox.net/ymm4/

### 確認コマンド
```powershell
# .NET SDKバージョン確認
dotnet --version

# 期待される出力: 10.x.x 以降
```

---

## 🚀 セットアップ手順

### ステップ1: YMM4インストールパスの確認

YMM4のインストールディレクトリを確認します。通常は以下のいずれか：

```
C:\Users\<ユーザー名>\AppData\Local\YukkuriMovieMaker4\
C:\Program Files\YukkuriMovieMaker4\
```

以下のDLLファイルが存在することを確認：
- `YukkuriMovieMaker.Plugin.dll`
- `YukkuriMovieMaker.Controls.dll`

### ステップ2: ビルド設定ファイルの作成

#### 方法A: セットアップスクリプト使用（推奨）

```cmd
cd ymm4-plugin
setup_build_props.bat
```

プロンプトに従ってYMM4のインストールパスを入力します。

#### 方法B: 手動作成

`Directory.Build.props` をymm4-pluginフォルダに作成：

```xml
<Project>
  <PropertyGroup>
    <YMM4DirPath>C:\Users\YourUserName\AppData\Local\YukkuriMovieMaker4\</YMM4DirPath>
  </PropertyGroup>
</Project>
```

**重要**: パスの末尾に `\` を含めてください。

### ステップ3: ビルド実行

```cmd
cd ymm4-plugin
build_plugin.bat
```

または手動ビルド：

```cmd
dotnet build -c Release
```

**ビルド成功時の出力例**:
```
Build succeeded.
    0 Warning(s)
    0 Error(s)
```

プラグインDLLは以下に自動コピーされます：
```
%YMM4DirPath%\user\plugin\NLMSlidePlugin\NLMSlidePlugin.dll
```

---

## ✅ 動作確認手順

### シナリオZero: プラグインロード確認

1. **YMM4を起動**

2. **プラグイン一覧を開く**
   - メニュー: `設定` → `プラグイン` → `プラグイン一覧`

3. **NLM Slide Pluginを確認**
   - リストに「**NLM Slide Plugin**」が表示されていればOK
   - バージョン: 0.1.0
   - 作者: NLMandSlideVideoGenerator Project

4. **プラグイン詳細を確認**（オプション）
   - プラグインを選択 → 詳細を確認
   - 説明文: "NotebookLM台本からの自動タイムライン・音声連携プラグイン"

### トラブルシューティング

#### プラグインが表示されない

**チェック項目**:
1. ビルドが成功したか確認
   ```cmd
   dir %YMM4DirPath%\user\plugin\NLMSlidePlugin\
   ```
   → `NLMSlidePlugin.dll` が存在するか確認

2. YMM4を再起動
   - プラグインは起動時にロードされます

3. YMM4のログを確認
   - `%AppData%\YukkuriMovieMaker4\logs\` 内のログファイル
   - プラグインロードエラーがないか確認

#### ビルドエラー: YMM4DLLが見つからない

**原因**: `Directory.Build.props` のパスが不正

**解決策**:
1. `Directory.Build.props` を開く
2. `YMM4DirPath` の値を修正
3. パスの末尾に `\` があるか確認
4. 再ビルド

#### .NET SDKエラー

**エラー例**: 
```
error NETSDK1045: The current .NET SDK does not support targeting .NET 10.0
```

**解決策**:
1. .NET 10 SDK以降をインストール
   - https://dotnet.microsoft.com/download/dotnet/10.0
2. インストール後、PowerShellを再起動
3. `dotnet --version` で確認

---

## 📁 プロジェクト構成

```
ymm4-plugin/
├── NLMSlidePlugin.csproj           # プロジェクト定義
├── Directory.Build.props.sample    # 設定テンプレート
├── Directory.Build.props           # ビルド設定（gitignore対象）
├── PluginInfo.cs                   # IPlugin実装
├── VoicePlugin/
│   └── CsvTimelineVoicePlugin.cs  # IVoicePlugin（スケルトン）
├── TextCompletionPlugin/
│   └── CsvScriptCompletionPlugin.cs # ITextCompletionPlugin（スケルトン）
├── setup_build_props.bat           # セットアップスクリプト
├── build_plugin.bat                # ビルドスクリプト
├── SETUP_GUIDE.md                  # 本ドキュメント
└── README.md                       # プラグイン概要
```

---

## 🔧 開発者向け情報

### デバッグ実行

Visual Studio 2022を使用する場合：

1. `NLMSlidePlugin.csproj` を開く
2. プロジェクト → プロパティ → デバッグ
3. 起動プロファイルを設定：
   - 実行ファイル: `%YMM4DirPath%\YukkuriMovieMaker.exe`
4. F5でデバッグ開始

### プラグインAPI仕様

- **公式ドキュメント**: https://ymm-api-docs.vercel.app/
- **サンプルリポジトリ**: https://github.com/manju-summoner/YukkuriMovieMaker4PluginSamples

### 実装ステータス

| インターフェース | 実装状態 | 備考 |
|----------------|---------|------|
| `IPlugin` | ✅ 完了 | シナリオZero対象 |
| `IVoicePlugin` | 🚧 スケルトン | 詳細仕様調査中 |
| `ITextCompletionPlugin` | 🚧 スケルトン | 詳細仕様調査中 |

---

## 📚 関連ドキュメント

- [TASK_007: YMM4プラグイン連携実装](../docs/tasks/TASK_007_YMM4PluginIntegration.md)
- [YMM4連携アーキテクチャ](../docs/ymm4_integration_arch.md)
- [YMM4 PoC計画](../docs/ymm4_poc_plan.md)

---

## ⚠️ 注意事項

1. **Directory.Build.propsはGit管理対象外**
   - `.gitignore` に含まれています
   - 各開発者が個別に作成する必要があります

2. **YMM4バージョン互換性**
   - v4.33.0.0以降を推奨
   - 古いバージョンでは動作しない可能性があります

3. **プラグイン自動コピー**
   - ビルド時に自動的にYMM4のプラグインフォルダにコピーされます
   - YMM4を終了してからビルドすることを推奨

---

## 📝 次のステップ

シナリオZero完了後の予定：

- [ ] IVoicePlugin詳細仕様の調査
- [ ] CSVタイムライン読み込み機能の実装
- [ ] 音声ファイルインポート機能の実装
- [ ] タイミング情報の適用

詳細は `docs/tasks/TASK_007_YMM4PluginIntegration.md` を参照してください。

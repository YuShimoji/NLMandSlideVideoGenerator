# Task: YMM4プラグイン連携実装
Status: IN_PROGRESS
Tier: 2
Branch: feature/ymm4-plugin
Owner: Worker
Created: 2026-02-02T03:59:00Z
Report: docs/inbox/REPORT_TASK_007_YMM4Plugin_2026-02-02.md

## 完了した作業

### シナリオZero（Y4）完了
- [x] Directory.Build.props 自動化スクリプト作成
- [x] ビルドプロセス自動化（build_plugin.bat）
- [x] セットアップガイド作成（SETUP_GUIDE.md）
- [x] README更新（クイックスタート追加）
- [x] .NET 9.0対応確認
- [x] Git反映完了（コミット: 556591d）

## Objective
- YMM4（ゆっくりムービーメーカー4）プラグインを実装し、CSV タイムラインから自動的に音声・字幕をインポートできる仕組みを構築する
- プラグインAPI（.NET 9）を優先し、必要に応じてAutoHotkeyを代替手段として検討する

## Context
- プロジェクト構成は既に準備済み（`ymm4-plugin/` ディレクトリ）
- `NLMSlidePlugin.csproj`、`PluginInfo.cs`、スケルトン実装が存在
- YMM4 API Docs: https://ymm-api-docs.vercel.app/
- サンプル: https://github.com/manju-summoner/YukkuriMovieMaker4PluginSamples

## Focus Area
- **シナリオZero（Y4）**: プラグイン動作確認
  - `Directory.Build.props.sample` → `Directory.Build.props` にコピー
  - YMM4DirPath を設定
  - `dotnet build` 実行
  - YMM4起動 → 設定 → プラグイン一覧で確認
- **音声プラグイン実装**: `VoicePlugin/CsvTimelineVoicePlugin.cs` を実装
  - CSV タイムラインから音声ファイル（WAV）をインポート
  - タイミング情報（開始時刻、duration）を適用
- **字幕プラグイン実装**: `TextCompletionPlugin/CsvScriptCompletionPlugin.cs` を実装
  - CSV タイムラインからテキストをインポート
  - 音声と同期した字幕表示

## Forbidden Area
- 既存のCSV生成・WAV生成フローの挙動変更
- YMM4本体のインストールを必須にする（開発環境のみ必須）

## Constraints
- プラグインは.NET 9対応
- YMM4がインストールされていない環境でもビルドエラーにならないこと
- CSV タイムライン仕様との互換性を維持

## DoD
- [ ] プラグインがYMM4で正常にロードされる
- [ ] CSV タイムラインから音声ファイルをインポートできる
- [ ] タイミング情報が正しく反映される
- [ ] 動作確認手順とスクリーンショットをドキュメント化
- [ ] テストケース追加（可能な範囲で）
- [ ] README.md にセットアップ手順を記載

## Notes
- YMM4がない環境でも開発できるよう、モックやスタブを検討
- 長期的にはAutoHotkey代替も視野に入れる

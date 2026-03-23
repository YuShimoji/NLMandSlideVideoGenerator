# Worker A: YMM4 Plugin & テンプレート

## 担当範囲
- SP-035 統合テスト (60% -> 100%): YMM4実機テスト
- SP-052 YMM4品質テンプレート (0% -> draft -> partial): テンプレート設計・作成
- ymm4-plugin/ の .NET/C# コード保守

## 前提知識
- プロジェクト: NLMandSlideVideoGenerator (YouTube長尺解説動画の半自動制作パイプライン)
- YMM4 = ゆっくりMovieMaker4。最終動画レンダリングを担当する出力層
- Python側はCSV (speaker/text/image/animation 4列) を生成し、YMM4にインポートする
- 設計公理: docs/DESIGN_FOUNDATIONS.md を必ず読むこと

## 現状
### SP-035 統合テスト
- チェックリスト整備済み: scripts/preflight_sp035.py (自動チェック)
- YMM4実機で以下を検証する必要がある:
  1. CSVインポート → タイムライン生成が正しいか
  2. 音声合成が期待通り動作するか
  3. アニメーション8種が正しく適用されるか
  4. 最終MP4出力の品質 (FFprobe検証項目はSP-039で定義済み)
- 仕様: docs/specs/ 内の ymm4 関連ファイル

### SP-052 YMM4品質テンプレート
- 現状 draft (0%)。テンプレート設計が未着手
- 目標: 「ゆっくり解説」ジャンルのYouTubeで通用するテンプレートパターン
- 参考: config/thumbnail_templates/sample_yukkuri.y4mmp (サムネイル用テンプレート)
- DECISION LOG: サムネイルはYMM4テンプレートベースに転換済み (2026-03-21)

### ymm4-plugin/
- NLMSlidePlugin: C# / .NET 10.0
- Core/ と Tests/ に分離済み (CI対応)
- CsvImportDialog, Ymm4TimelineImporter, VoiceSpeakerDiscovery が主要クラス
- VoiceSpeakerMapping.cs: 話者→YMM4ボイス設定のマッピング

## 作業手順
1. docs/DESIGN_FOUNDATIONS.md を読む
2. docs/specs/ymm4_video_quality_template.md (SP-052) を読む
3. scripts/preflight_sp035.py を実行して自動チェック結果を確認
4. YMM4実機でCSVインポート→レンダリングのE2Eテスト
5. テンプレートパターン (レイアウト・フォント・色・キャラ配置) を設計

## 成果物
- SP-035 テスト結果レポート
- SP-052 テンプレート .y4mmp ファイル (複数パターン)
- ymm4-plugin/ のバグ修正があれば PR

## 参照ファイル
- docs/DESIGN_FOUNDATIONS.md
- docs/specs/ymm4_video_quality_template.md
- docs/ymm4_export_spec.md
- docs/ymm4_final_workflow.md
- docs/ymm4_integration_arch.md
- config/thumbnail_templates/sample_yukkuri.y4mmp
- ymm4-plugin/Core/
- scripts/preflight_sp035.py

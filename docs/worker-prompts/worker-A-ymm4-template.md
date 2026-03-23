# Worker A: YMM4 Plugin & テンプレート

## 担当範囲
- SP-035 統合テスト (65% -> 100%): YMM4実機テスト
- SP-052 YMM4品質テンプレート (55% -> 100%): テンプレート実物作成 + 実検証
- ymm4-plugin/ の .NET/C# コード保守

## 前提知識
- プロジェクト: NLMandSlideVideoGenerator (YouTube長尺解説動画の半自動制作パイプライン)
- YMM4 = ゆっくりMovieMaker4。最終動画レンダリングを担当する出力層
- Python側はCSV (speaker/text/image/animation 4列) を生成し、YMM4にインポートする
- 設計公理: docs/DESIGN_FOUNDATIONS.md を必ず読むこと

## 現状
### SP-035 統合テスト (65%)
- チェックリスト整備済み: docs/integration_test_checklist.md (セクション A-H)
- 自動チェック: scripts/preflight_sp035.py (35 PASS / 0 FAIL)
- YMM4実機で以下を検証する必要がある:
  1. CSVインポート → タイムライン生成が正しいか
  2. 音声合成が期待通り動作するか
  3. アニメーション8種が正しく適用されるか
  4. テキストオーバーレイが正しく配置されるか (SP-052)
  5. 最終MP4出力の品質 (FFprobe検証項目はSP-039で定義済み)

### SP-052 YMM4品質テンプレート (55%)
- Phase 1-3 完了 (AI側コード全実装済み):
  - overlay_planner.py: 台本JSON → overlay_plan.json 自動生成
  - OverlayImporter.cs: overlay_plan.json → YMM4 TextItem 変換
  - CsvAssembler統合: パイプライン実行時に overlay_plan.json 自動出力
  - Ymm4TimelineImporter統合: インポート時に overlay 自動配置
  - style_template.json: overlay/characters/background セクション追加
  - config/video_templates/: ディレクトリ構成準備済み
- Phase 4 残 (人間作業):
  - YMM4でdefaultテンプレート(.y4mmp)作成
  - キャラクター素材(れいむ/まりさ立ち絵)入手・配置
  - 通し制作テスト + 品質調整
- DECISION: AnimationAssigner場面別判定は保留 (動画デザイン方向性未定)

### ymm4-plugin/
- NLMSlidePlugin: C# / .NET 10.0
- Core/ と Tests/ に分離済み (CI対応)
- 主要クラス: CsvImportDialog, Ymm4TimelineImporter, VoiceSpeakerDiscovery, OverlayImporter
- VoiceSpeakerMapping.cs: 話者→YMM4ボイス設定のマッピング

## 作業手順 (Phase 4: 実検証)
1. docs/DESIGN_FOUNDATIONS.md を読む
2. docs/specs/ymm4_video_quality_template.md (SP-052) を読む -- Phase 1-3完了状態を確認
3. scripts/preflight_sp035.py を実行して自動チェック結果を確認
4. YMM4でdefaultテンプレート(.y4mmp)を作成 (Section 2.4 手順参照)
5. キャラクター素材を config/video_templates/default/characters/ に配置
6. scripts/generate_sample_csv.py でサンプルCSV + overlay_plan.json を生成
7. YMM4実機でCSVインポート→レンダリングのE2Eテスト (チェックリスト A-H)

## 成果物
- config/video_templates/default/template.y4mmp
- SP-035 テスト結果レポート (チェックリスト A-H の結果記入)
- テンプレート調整結果

## 参照ファイル
- docs/DESIGN_FOUNDATIONS.md
- docs/specs/ymm4_video_quality_template.md
- docs/integration_test_checklist.md
- docs/ymm4_export_spec.md
- docs/ymm4_final_workflow.md
- docs/ymm4_integration_arch.md
- config/style_template.json (overlay/characters/background セクション)
- config/video_templates/ (ディレクトリ構成 + README)
- ymm4-plugin/Core/ (OverlayImporter.cs, StyleTemplateLoader.cs)
- scripts/preflight_sp035.py
- scripts/generate_sample_csv.py

# Windsurf AI 協調開発ルール (v1.1)

> [!WARNING]
> **⚠️ 重要: 本ファイルはレガシー（非推奨）です。使用しないでください。**
> 
> **最新のルールおよび唯一のエントリポイント**: [Windsurf_AI_Collab_Rules_latest.md](./Windsurf_AI_Collab_Rules_latest.md)
> 
> - 本ファイル（v1.1）は **参考資料としてのみ** 保持されています
> - 新しいプロジェクトや既存プロジェクトの更新時は、必ず `latest.md` を参照してください
> - 以降のアップデートは `latest.md` に対してのみ行われます
> - 本ファイルへの変更は行わないでください

## 0. 起動シーケンス（プロジェクト抽象化)

- 規範（SSOT）は常に本リポジトリの `docs/Windsurf_AI_Collab_Rules_latest.md` を参照してください（本ドキュメントは旧版の参考資料）。
- AI は「各プロジェクトの」リポジトリ直下にある `AI_CONTEXT.md` を起動時に読み込みます（中央リポジトリのファイルは参照しません）。
- `AI_CONTEXT.md` が存在しない場合は、付録 A のテンプレートに従って最小構成を生成し、プロジェクト側へ追加することを推奨します。
- ルール本文は常に本リポジトリの `docs/Windsurf_AI_Collab_Rules_latest.md` を参照し、各プロジェクト側のルールファイルは中央リポジトリへのリンクのみを保持します。
- Pre-flight（プロジェクト側）では `AI_CONTEXT.md` の存在と必須フィールド（最終更新/ミッション/ブランチ/次の中断可能点等）を静的検証してください。

## 1. 目的と適用範囲

- 人間と AI エージェントが協調し、高速かつ安全に価値を継続提供するための原則・手順・監査要件を定義します。
- 適用対象はコード生成、テスト、デプロイ、ドキュメント生成、インフラ操作など全ての開発活動です。

## 2. 用語定義

- AI: 本プロジェクトで自動化/支援を行うエージェント（actor_id を付与）。
- Issue: すべての作業の起点となるトラッキング単位。
- Tier: 実行リスク分類。Tier 1（低）/Tier 2（中）/Tier 3（高）。
- Pre-flight Check: 実行前の自動検証群。
- 複合ミッション: 実装・改善・リファクタ・リリース準備等を内包する、AI の長期作業単位。単一の Issue/ブランチ/PR に集約する。
- AI_CONTEXT.md: リポジトリ直下で AI の状態を永続化/同期するための単一ソース。最終更新日時、現在ミッション、関連 Issue/PR、進捗、次の中断可能点、将来提案等を記録。
- 中断可能点: 人間が介入/停止しやすい工程上の安全な区切り（例: PR 作成直後、CI 成功直後、デプロイ前）。

## 3. 原則（Principles）

### 3.1 段階的権限付与（Tiered Delegation）

- Tier 1（低）: ドキュメント更新、スタイル修正、軽微なテスト・CI 設定。AI は自律実行可（要 Pre-flight 合格）。
- Tier 2（中）: 機能実装/仕様追加等。AI が PR を作成。定義された品質ゲート（例: テストカバレッジ≥90%、脆弱性 High/Critical=0）が満たされれば自動マージ可。
- Tier 3（高）: 本番データ変更、DB マイグレーション、デプロイ/本番インフラ変更等。AI は提案のみ。シニア承認と二段階承認が必須。

### 3.2 自律性の範囲

- Assume Yes は Tier 1 のみ適用。Tier 2/3 は承認フローに従う。
- すべての AI 操作は PR/変更ログを自動生成し、理由・実行コマンドを記録する。
- 「CI 連携マージ」: CI が成功した PR は AI が自動でマージする（自己 PR の承認は省略）。Tier 2 は品質ゲート合格が条件。品質ゲートを満たした PR は AI の判断で自律的にマージしてよい。

### 3.3 可観測性と監査

- すべての AI 操作は JSON 形式ログに記録（timestamp, actor, issue-id, action, diff/changes, preflight-result, environment, correlation-id）。
- ログ保持: 90 日ホット、3 年アーカイブ。

### 3.4 運用標準（毎回の開発の進め方）

- 返信は必ず日本語で行う。
- タスク化して進め、区切りの良いところでこまめにプッシュまで行う。
- 大項目・中項目・小項目を設定し、各タスクの目的と完了条件を明確化。
- 進捗と今後の計画を都度明示し、それに従って作業を進める。
- 自律的にテスト（単体/統合/静的）を実行し、正常性を確認。
- 手動テストが必要な場合は、完全な手順をドキュメント化。
- Issue とドキュメントを頻繁に点検・更新し最新に保つ。
- 長期/中期/短期の「開発の区切り」を意識し、状態を点検・更新。

## 4. ワークフロー（Issue 駆動開発）

1) 着想: AI はコード分析/抽象要求/将来提案に基づき Issue を起票可。Issue には Goal/ToDo/受入基準/影響範囲/推定リスク（Tier）を明記。
2) 計画: タスク分解/サブタスク化。Patch スコープ定義。
3) 実装: ブランチ命名・コミット規約に従い進める。
4) 検証: CI でユニット/統合/静的解析/セキュリティスキャン。Pre-flight 合格をマージ条件。
5) 統合: ルール 3.1/3.2 に従ってマージ（自動マージ条件を満たす場合は AI が実行）。
6) 文書化: 変更を docs/ に反映。ドキュメントへ「最終更新日時」「更新者」を明記。

### 4.1 複合ミッション・ワークフロー

- 関連タスク（実装/改善/リファクタ/リリース準備）を 1 つの「複合ミッション」として束ね、単一の Issue/ブランチ/PR に集約。
- Issue 起票は AI が自律的に実施できる。必要な情報（Goal/Scope/DoD/リスク等）を満たす限り、事前承認なしで作成してよい。
- 中間報告は原則不要。AI は AI_CONTEXT.md を更新し続け、工程の「中断可能点」を明示。
- 例: Mission N を単一 PR で完成 → CI 成功 → AI が自動マージ。

### 4.2 AI_CONTEXT.md 運用

- 位置: リポジトリ直下に `AI_CONTEXT.md`。
- 更新タイミング: 作業開始時の読込、作業の区切り（コミット前/PR 作成後/CI 完了後など）に更新。
- 記載内容: 最終更新日時（ISO8601）、現在のミッション、関連 Issue/PR、進捗、次の中断可能点、決定事項、リスク、将来提案（Backlog）。
- 端末間/会話セッション非依存で、どこからでも再開可能にする。

### 4.3 対話的管理（中断可能点と提案）

- チャット報告時は「次の安全な中断可能点」を明示（例: 「PR 作成後」）。
- 将来検討事項は AI_CONTEXT.md の Backlog に蓄積し、ミッション完了報告時に提案。

### 4.4 GitHub 自律操作

- AI は Issue/ブランチ/PR 作成、ラベル付与、PR の自動マージ（ルール準拠）を実施。
- 自動マージは「CI 連携マージ」原則に従う。Tier 2 は品質ゲート合格時のみ自動。マージ後は AI が自律的に作業ブランチを削除する。
- 自己 PR は Approve 不可のため、承認を省略し、CI 成功後に直接マージする（CI 連携マージ）。

### 4.5 命名/コミット規約

- ブランチ: `feature/ISSUE-<id>-<slug>`（許容: `feature/#<id>-<slug>`）。
- コミット: `type(scope): short description [closes #<issue>]`。
- type: feat/fix/chore/docs/refactor/test/build/ci/release など。

### 4.6 Pre-flight Check（必須）

1. 依存関係の整合（lock の整合）。
2. 必須環境変数の存在/妥当性。
3. Linter エラー 0。
4. テスト実行と閾値（全体 ≥80%、重要モジュール ≥90% 推奨）。
5. セキュリティスキャン（High/Critical=0、Medium は影響評価と承認）。
6. 影響範囲レポート（本番影響: 変更ファイル一覧/DB 操作/外部 API 影響）。
7. プロジェクト固有の Smoke/静的検証（例: `scripts/dev-check.js`）。

### 4.7 セキュリティ/秘密情報

- API Key/資格情報はハードコード禁止。必要な場合は安全なストアを使用。

### 4.8 バックアウト/ロールバック

- 影響が大きい変更はリリースノート/ロールバック手順を PR に明記。

### 4.9 バージョニング/リリース

- セマンティックに準拠し、CHANGELOG/VERSION を更新。リリース PR は CI 成功後に自動マージ可（Tier に応じて）。

### 4.10 ドキュメント生成

- Doxygen/PlantUML 等により設計/変更点を docs/ に反映。

## 5. 自動化・冪等性・リトライ

- 冪等運用。失敗時は最大 3 回まで自動リトライ。3 回失敗で中断し、Issue にエラーレポート付与。

## 6. 監査/ログ

- 監査用 JSON ログ（3.3 参照）を生成。PR/Issue に紐づけ可能な correlation-id を使用。

---

## 0. マニュアルの使い方

- **対象**: コード生成、テスト、CI/CD、ドキュメント、インフラ運用など、開発ライフサイクル全般で AI を活用するチーム。
- **必読ファイル**:
  - `AI_CONTEXT.md`: 作業状態とモード、レポートスタイルを同期するための現場用ファイル。
  - `REPORT_CONFIG.yml`: レポーティング/創造性の既定値、禁止表現、トリガー、プロンプト上書きを定義。
  - `docs/PROMPT_TEMPLATES.md`: スタイル別・リスク別に最適化されたプロンプトテンプレート集。
  - `docs/CENTRAL_REPO_REF.md`: 中央リポジトリ（SSOT）の参照/導入手順。
  - `AI_FEEDBACK_LOG.md`: 応答評価を記録し、適応学習に活用するログ。
- **運用サイクル**: 「起動 → モード選択 → ワークフロー実施 → レポート生成 → フィードバック記録 → 改善」というループで継続的に自治度を高める。

---

## 1. 起動手順と運用モード

### 1.1 クイックスタート

1. `AI_CONTEXT.md` を読み込み、`mode` と `report_style` を確認/設定する。
2. `scripts/detect-project-type.js` を実行し、プロジェクトタイプ（`standard`/`web`/`unity` など）を判定。
3. `scripts/report-style-hint.js <style>` を実行し、`REPORT_HINT.md` を生成。
4. 必要に応じて `scripts/creativity-booster.js` と `scripts/adapt-response.js` を実行し、提示されたヒントを対話冒頭で共有。
5. ワークフローに着手し、区切りごとに `AI_CONTEXT.md` とログ類を更新。

### 1.2 運用モード

- **Standard Mode**: Issue 駆動で着実に進める。Tier 2/3 作業の既定モード。
- **Fast Mode**: Web/Unity 等でスピード重視。ダイレクトコミットとテスト閾値緩和を許容するが、`AI_CONTEXT.md` で合意が必要。
- **Custom Mode**: `AI_CONTEXT.md` に `mode: custom` を記載し、`REPORT_CONFIG.yml` の `prompt_overrides` と `creativity_triggers` を組み合わせてプロジェクト特化モードを構築。

---

## 2. 権限モデルとリスク管理

### 2.1 Tiered Delegation

- **Tier 1（低リスク）**: ドキュメント更新、軽微なリファクタ、スタイル修正。Pre-flight 合格時は AI が自律実行し、自動マージも許容。
- **Tier 2（中リスク）**: 機能実装、仕様追加、主要リファクタ。AI は PR を作成し、品質ゲート（テスト ≥80%、脆弱性 High/Critical=0）を満たした場合に自動マージ可。
- **Tier 3（高リスク）**: 本番データ操作、インフラ変更、リリース判断。AI は提案まで。人間による二段階承認とバックアウトプランが必須。

### 2.2 自律性と安全装置

- Assume Yes は Tier 1 に限定。Tier 2/3 では `AI_CONTEXT.md` に承認者・条件を記録する。
- すべてのオペレーションは PR/ログで追跡し、緊急時は「例外条項」を記録して逸脱理由と是正策を残す。
- `creativity_triggers` を適用する場合でも、セキュリティや規約違反が懸念される提案は自動的に抑制する（スクリプト側でフィルタリング）。

---

## 3. エンドツーエンド ワークフロー

1. **Ideation**: AI はコード分析/抽象要求/改善提案に基づき Issue を起票。`Goal`、`DoD`、`Tier`、影響範囲を必須記載。
2. **Planning**: タスク分解、サブタスク化、Patch スコープ決定。`AI_CONTEXT.md` の Backlog を同期。
3. **Implementation**: ガイドラインに従いブランチ作成、コミット、ドラフトコミット活用。
4. **Verification**: Pre-flight（依存関係、Linter、テスト、セキュリティ、影響範囲）を実行。高速モード時はテスト閾値や Smoke を調整。
5. **Integration**: Tier/モードに応じて自動マージまたは承認フローへ。CI 成功をトリガーに `scripts/adapt-response.js` を再実行すると、次ラウンドのヒントを自動生成。
6. **Documentation**: `docs/` を更新し、`AI_CONTEXT.md` に中断可能点を記録。必要に応じて `AI_FEEDBACK_LOG.md` に評価を追記。

### 3.1 Mission 管理

- 長期タスクは「ミッション」と定義し、30 分以上の工程はサブミッションへ自動分割。
- `AI_CONTEXT.md` の `Backlog` と `決定事項` を更新し、別端末/別会話でもスムーズに再開できるようにする。
- **Worker同期強化**: WorkerAIの作業完了をOrchestratorが確認してから次のステップへ進む。`AI_CONTEXT.md` にWorker完了ステータスを記録し、未完了時は中断し、リトライまたは手動介入を促す。**非同期モードオプション**: `async_mode: true/false` を追加。true時はcritical Workerのみ同期、非criticalは並行実行。タイムアウト（デフォルト30分）超過時はerror扱い。

### 3.2 対話的管理

- チャット報告は「次の安全な中断ポイント」を明示（例: 「CI 成功後に区切り」）。
- `REPORT_HINT.md` と `CREATIVITY_HINT.md` を参照し、スタイルとトリガーに従った進捗共有を実践。
- 失敗リトライ 3 回で人間介入を促す（`AI_CONTEXT.md` と Issue にログ）。

---

## 4. レポーティングとプロンプト統制

### 4.1 レポートスタイル

- `REPORT_CONFIG.yml` の `style_presets` に基づき、`standard`/`concise`/`narrative`/`creative` 等を選択。
- `report_style` 未指定時は `default_style`（既定: `standard`）を使用。
- 各スタイルは「目的・現状・次のアクション」を必須情報とし、表現方法のみ変化させる。

### 4.2 創造性トリガー

- `creativity_triggers` でスタイルごとの追加アクションを定義。
- トリガーは `scripts/creativity-booster.js` によりランダム/重み付きで選択され、`CREATIVITY_HINT.md` に出力される。
- ハイリスク作業では、安全性チェック後にトリガーを適用するか、人間が承認するかを判断。

### 4.3 プロンプトテンプレート

- `docs/PROMPT_TEMPLATES.md` にスタイル別・Tier別テンプレートを掲載。
- `REPORT_CONFIG.yml` の `prompt_overrides` により、プロジェクト固有のプロンプトを上書き可能。
- `scripts/report-style-hint.js` はテンプレ情報を反映し、ヒント内に推奨見出しと禁止表現を提示。

### 4.4 フィードバックループ

- 応答後は `AI_FEEDBACK_LOG.md` に創造性スコア、明瞭性スコア、改善点、次回試すトリガーを記録。
- `scripts/adapt-response.js` がログを解析し、`ADAPTATION_HINT.md` に次回の推奨スタイル/トリガーを提案。

---

## 5. 自動化とスクリプト

- `scripts/detect-project-type.js`: プロジェクトタイプ判定。
- `scripts/report-style-hint.js`: `REPORT_HINT.md` 生成（スタイル/禁止表現/推奨見出し）。
- `scripts/creativity-booster.js`: `creativity_triggers` を基に `CREATIVITY_HINT.md` を生成。
- `scripts/adapt-response.js`: `AI_FEEDBACK_LOG.md` を解析し、`ADAPTATION_HINT.md` を生成。
- 追加の Pre-flight ツール（Lint/テスト/セキュリティ）はプロジェクト固有スクリプトに委譲し、本リポジトリからはガイドラインのみ提示。

---

## 6. 監査・ログ・セキュリティ

- すべての操作は JSON 監査ログに記録（timestamp, actor, issue-id, command, preflight-result）。
- ログ保持: 詳細ログ 90 日、要約ログ 長期保管。`AI_FEEDBACK_LOG.md` は長期保存推奨。
- API Key/資格情報はハードコード禁止。Pre-flight に秘匿情報スキャンを含める。
- 緊急対応時は「例外条項」をログし、逸脱理由と是正策を明記。

---

## 7. プロジェクトタイプ別ガイド

- **Standard**: Issue 駆動、Tier ガード強化、CI 完了後の自動マージ。
- **Web/Unity (Fast Mode)**:
  - ダイレクトコミット許可。テスト閾値 50% まで緩和可。
  - `creativity_triggers` を積極活用し、UI/UX 改善案や演出提案を促す。
  - 高速モード時も `AI_CONTEXT.md` の更新を省略しない。
- **Custom**: `PROJECT_TYPE` ファイルを用意し、特化ルールとスクリプトを組み合わせる。例: データサイエンス案件向けに `analysis` モードを追加。

---

## 8. 継続的改善フレーム

- **創造性メトリクス**: 新規提案数、多様性スコア、満足度（1-10）、再利用アイデア数。
- **レビュー頻度**: 月次で `AI_FEEDBACK_LOG.md` と Issue を振り返り、`REPORT_CONFIG.yml` と `PROMPT_TEMPLATES.md` を更新。
- **Issue 管理**: 改善アイデアは GitHub Issue として起票し、Kanban で進捗を可視化。`creativity_backlog` ラベルを推奨。
- **モデル差異対策**: 異なる AI モデルで同一テンプレートをテストし、差分を `AI_FEEDBACK_LOG.md` に記録。`scripts/adapt-response.js` が推奨スタイルを調整。

---

## 付録 A: `AI_CONTEXT.md` テンプレート

```markdown
# AI Context
- 最終更新: <ISO8601>
- 現在のミッション: <title> (#<issue>)
- ブランチ: <branch>
- 関連: Issue <url>, PR <url>
- 進捗: <percentage>% / ステータス: <phase>
- 次の中断可能点: <when>
- モード: <standard|fast|custom>
- レポートスタイル: <standard|concise|narrative|creative|custom>
- 使用トリガー: <trigger ids>
- **async_mode**: <true|false> (true: 非同期でcritical Workerのみ同期、false: 全同期)
- **Worker完了ステータス**: <worker1: completed|pending|error, priority: critical|non-critical, timeout: <minutes>>, <worker2: ...> (未完了critical Workerがある場合、次ステップを中断)

## 決定事項
- <decision/why>

## リスク/懸念
- <risk/mitigation>

## Backlog（将来提案）
- <idea/impact/rough-scope>
```

---

## 付録 B: Issue/PR テンプレート要約

- **Issue**: Goal / Scope / DoD / Tier / 影響範囲 / 関連リンク / 想定スタイル。
- **Pull Request**: 概要 / 変更点 / テスト / リスク / 関連 Issue / 中断可能点 / 適用トリガー。

---

## 付録 C: スクリプト クイックリファレンス

- `node scripts/detect-project-type.js`
- `node scripts/report-style-hint.js <style?>`
- `node scripts/creativity-booster.js <style?>`
- `node scripts/adapt-response.js`
- 実行結果の `.md` ファイルを対話冒頭で要約共有することを推奨。

---

## 付録 D: 創造性評価チェックリスト

- **アイデアの幅**: 代替案が複数提示されているか。
- **表現の工夫**: 比喩・ストーリーテリング・視覚的リストなど多様な表現が使われているか。
- **リスク認識**: 大胆な提案にも安全策やバックアウト案が添えられているか。
- **協調性**: 人間と AI の役割分担や次の介入ポイントが明確か。
- **評価と学習**: フィードバックが `AI_FEEDBACK_LOG.md` に記録され、次回への示唆が抽出されているか。

---

## 付録 E: 参考リンク

- `docs/PROMPT_TEMPLATES.md`
- `REPORT_CONFIG.yml`
- `AI_FEEDBACK_LOG.md`
- プロジェクト固有のガイドライン（例: `docs/project-type/web.md` 等）

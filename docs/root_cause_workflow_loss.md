# 根本原因分析: 根本ワークフローの暗黙的消失

日付: 2026-03-22
ステータス: 分析完了

---

## 問題

プロジェクト開始時から存在していた根本ワークフロー:

```
NotebookLM ソース投入 → Audio Overview 音声生成 → 音声を再投入 → テキスト化 → 台本整形 → YMM4
```

が、AI セッションの蓄積により、以下に暗黙的に置換された:

```
Gemini プロンプトで台本生成 → CSV → YMM4
```

この置換は DECISION LOG に記録されず、48仕様が誤った前提の上に積み上がった。

---

## 時系列

| 日付 | 出来事 | 影響 |
|---|---|---|
| プロジェクト開始 | `docs/workflow_specification.md` Step 2.1.2-2.1.3 に根本ワークフローを記載 | 正しい設計前提が文書化された |
| 2025-11-26 | commit `b78d25e`: "Gemini+TTS alternative workflow for NotebookLM audio generation" | Gemini が「代替」として導入。名目上は NLM のための補助 |
| 2025-12-01 | CSV 駆動動画生成モード実装 | パイプラインが CSV 中心に移行 |
| 2026-03-04 | DECISION: YMM4 一本化 | NLM の位置づけに言及なし |
| 2026-03-07 | DECISION: Gemini API 統合 | Gemini が台本「生成」の公式手段に。**NLM 放棄の決定が未記録** |
| 2026-03-08 | audio_generator.py no-op スタブ化 | NLM 音声経路が完全に無効化 |
| 2026-03-19 | ドリフト分析 (notebooklm_drift_analysis.md) | ドリフトを検出したが、audio→text ループは復元できなかった |
| 2026-03-22 | ユーザー指摘により根本ワークフローを再発見 | 本文書を作成 |

---

## 根本原因

### 1. 「代替」が「本流」に昇格した（Decision Gap）

commit `b78d25e` のメッセージ "alternative workflow **for** NotebookLM" が象徴的。
Gemini は NLM の「ための」代替として導入されたが、NLM 本体の統合が実現しないまま、
いつの間にか Gemini が本流になった。

この移行に対応する DECISION LOG エントリが存在しない:
- 「NotebookLM Audio Overview + テキスト化ループを放棄する」
- 「Gemini が台本生成の主手段になる」
これらの決定は暗黙的に行われた。

### 2. AI セッション間での根本前提の非継承

各 AI セッションは、直近のコード状態・ドキュメント状態を「真実」として受け取る。
根本ワークフローが `workflow_specification.md` に存在していても、
その文書が他の文書によって事実上 superseded されていれば、
AI は superseded 後の状態を正として作業を進める。

15セッション × 48仕様の蓄積が、根本前提からの乖離を加速させた。

### 3. ドリフト検出の限界

2026-03-19 のドリフト分析は NotebookLM の「役割」消失を正しく検出したが、
具体的なワークフロー（audio → 再投入 → text）は git 履歴から復元できなかった。

分析が見た粒度:
- NotebookLM の台本品質 >> Gemini の台本品質 （正しい）
- NotebookLM のスライド生成 >> PIL のスライド生成 （正しい）

分析が見なかった粒度:
- NotebookLM は音声を生成し、その音声を再投入してテキスト化する（具体的なワークフロー）
- Gemini の役割は台本「生成」ではなく台本「構造化」（責務の定義）

### 4. 仕様の積み上がりが検出を困難にした

48仕様が Gemini 台本生成を前提として整合している状態では、
「全体が間違っている」可能性は見えにくい。
個々の仕様は内部的に矛盾がなく、テスト（1262件）も全て通る。
問題は「何が正しいか」ではなく「何が前提になっているか」にあった。

---

## 教訓

1. **DECISION LOG には「何を放棄したか」も記録すべき**
   「Gemini API 統合」だけでなく「NLM Audio Overview ループの放棄」を記録すべきだった

2. **根本前提は最上位文書に明記すべき**
   `workflow_specification.md` は通常の仕様文書の1つとして埋もれた。
   根本前提は `DESIGN_FOUNDATIONS.md` のように最上位権威を持つ文書に配置すべき

3. **AI セッション間の継承には「公理」が必要**
   セッション開始時に読む文書（CLAUDE.md, AI_CONTEXT.md）に根本ワークフローが明記されていなかった。
   公理的な前提は、セッション間で継承される文書に配置する必要がある

4. **テスト全緑 ≠ 正しい方向**
   1262テストが全て通っていても、根本前提が誤っていれば全て無意味。
   テストは「コードが意図通り動くか」を検証するが、「意図が正しいか」は検証しない

---

## 対応

1. `docs/DESIGN_FOUNDATIONS.md` Section 0 に根本ワークフローを復元済み
2. `docs/specs/e2e_workflow_spec.md` (SP-050) を根本ワークフロー準拠で起草済み
3. CLAUDE.md DECISION LOG に復元の決定を記録済み
4. 今後: SP-050 の未決定事項を確定後、SP-045 (チェックリスト) を更新
5. 今後: Gemini の役割を「台本生成」から「台本構造化」に限定するコード変更

---

## 参照

- `docs/DESIGN_FOUNDATIONS.md` — 復元された根本ワークフロー
- `docs/workflow_specification.md` — 元の記載（git 履歴）
- `docs/notebooklm_drift_analysis.md` — 先行するドリフト分析
- `docs/specs/e2e_workflow_spec.md` (SP-050) — 根本ワークフロー準拠の E2E 仕様

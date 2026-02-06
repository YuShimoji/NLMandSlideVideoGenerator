---
description: セッション終了チェック（作業完了時の手順）
---

## セッション終了ワークフロー

shared-workflows v3 準拠の作業終了手順。

### 1. git status 確認

// turbo

```powershell
git status -sb
```

- クリーン（`M`/`??` が無い）であることを確認。未コミットがあればコミットする。

### 2. 終了時チェックスクリプト

// turbo

```powershell
node .shared-workflows/scripts/session-end-check.js --project-root .
```

- `Result: OK` であることを確認。

### 3. 終了テンプレ提示（必須）

完了でも未完了でも、以下のテンプレを提示する（SSOT: `.shared-workflows/docs/windsurf_workflow/EVERY_SESSION.md` の「5. 終了時テンプレ」）:

```text
【確認】完了判定: 完了 / 未完了

【状況】（1-3行）
- いま何が終わっていて、何が残っているか:

【次に私（ユーザー）が返す内容】以下から1つ選んで返信します:

### 推奨アクション
1) ★★★ 「選択肢1を実行して」: <選択肢1> - <理由>
2) ★★ 「選択肢2を実行して」: <選択肢2> - <理由>

### その他の選択肢
3) ★ 「選択肢3を実行して」: <選択肢3> - <理由>
```

### 4. push（必要時）

```powershell
git push origin master
```

- push 後は `git status -sb` で再確認。

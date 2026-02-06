---
description: Worker委譲（タスクをWorkerに委譲する手順）
---

## Worker 委譲ワークフロー

shared-workflows v3 のショートカット運用に準拠。

### 方法A: 1行指定（推奨）

Worker スレッドに以下を貼るだけ:

```text
TASK_XXX を実行してください。Worker Metaprompt: .shared-workflows/prompts/every_time/WORKER_METAPROMPT.txt
```

Worker が `docs/tasks/TASK_XXX*.md` を読み取り、WORKER_METAPROMPT に従って実行し、固定3セクションで報告する。

### 方法B: スクリプト生成

// turbo

```powershell
node .shared-workflows/scripts/worker-dispatch.js --ticket docs/tasks/TASK_XXX.md
```

オプション:
- `--unity`: Unity版テンプレート使用
- `--dry-run`: 確認のみ（実行しない）
- `--output <path>`: ファイル出力

### Worker 完了後の確認

// turbo

```powershell
node .shared-workflows/scripts/report-validator.js docs/inbox/REPORT_XXX.md
```

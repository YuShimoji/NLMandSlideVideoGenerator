---
description: Orchestrator起動（毎回のセッション開始手順）
---

## Orchestrator 起動ワークフロー

shared-workflows v3 準拠の毎回のセッション開始手順。

### 1. サブモジュール更新チェック

// turbo

```powershell
node .shared-workflows/scripts/sw-update-check.js
```

- `Behind origin/main: 0` なら最新。N>0 なら `git submodule update --remote .shared-workflows` を実行。

### 2. 環境診断

// turbo

```powershell
node .shared-workflows/scripts/sw-doctor.js --profile shared-orch-bootstrap --format text
```

- ERROR が無いことを確認。WARN は理由が明確なもののみ許容。

### 3. SSOT 補完（必要時）

// turbo

```powershell
node .shared-workflows/scripts/ensure-ssot.js --project-root .
```

### 4. Orchestrator Driver をチャットに貼る

- `.shared-workflows/prompts/every_time/ORCHESTRATOR_DRIVER.txt` の内容をチャットに貼る。
- Driver が MISSION_LOG.md を読み、現在フェーズのモジュールを読み込んで実行する。

### 5. 参照先

- 運用SSOT: `.shared-workflows/docs/windsurf_workflow/EVERY_SESSION.md`
- 入口: `.shared-workflows/docs/windsurf_workflow/OPEN_HERE.md`
- 表示ポリシー: `.shared-workflows/data/presentation.json`

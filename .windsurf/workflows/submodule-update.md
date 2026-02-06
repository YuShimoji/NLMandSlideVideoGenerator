---
description: サブモジュール更新（shared-workflowsを最新に同期）
---

## サブモジュール更新ワークフロー

### 1. 更新チェック

// turbo

```powershell
node .shared-workflows/scripts/sw-update-check.js
```

- `Behind origin/main: 0` なら最新。以降の手順は不要。

### 2. リモート取得

```powershell
git -C .shared-workflows fetch origin
```

### 3. 差分確認

// turbo

```powershell
git -C .shared-workflows log --oneline HEAD..origin/main
```

### 4. 最新に更新

```powershell
git -C .shared-workflows reset --hard origin/main
```

### 5. 親リポジトリでコミット

```powershell
git add .shared-workflows
git commit -m "chore(submodule): update .shared-workflows to latest"
git push origin master
```

### 6. 更新後の環境診断

// turbo

```powershell
node .shared-workflows/scripts/sw-doctor.js --profile shared-orch-bootstrap --format text
```

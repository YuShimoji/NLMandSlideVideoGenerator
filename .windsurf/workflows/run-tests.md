---
description: テスト実行（プロジェクトのテストスイートを実行）
---

## テスト実行ワークフロー

### 1. 基本テスト（高速）

// turbo

```powershell
.\venv\Scripts\python.exe -m pytest -q -m "not slow and not integration" --tb=short
```

### 2. CSV パイプラインテスト

```powershell
.\venv\Scripts\python.exe -m pytest -q tests\test_csv_pipeline_mode.py --tb=short
```

### 3. 全テスト（時間がかかる場合あり）

```powershell
.\venv\Scripts\python.exe -m pytest -q --tb=short
```

### 4. カバレッジ付き

```powershell
.\venv\Scripts\python.exe -m pytest --cov=src --cov-report=term-missing -q -m "not slow and not integration"
```

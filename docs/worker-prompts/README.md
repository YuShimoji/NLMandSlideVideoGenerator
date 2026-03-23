# Worker Prompts

並列開発のためのWorker分担定義。各Workerは独立した領域を担当し、コア開発者が統合する。

## 分担一覧

| Worker | 領域 | 対象SP | 依存関係 |
|--------|------|--------|----------|
| **Core** | パイプライン信頼性・GUI・Gemini構造化 | SP-050, SP-053 | なし (統合者) |
| **A** | YMM4 Plugin & テンプレート | SP-035, SP-052 | Core のCSV出力に依存 |
| **B** | YouTube公開パイプライン | SP-038, SP-045 | Core のメタデータ出力に依存 |
| **C** | Feed/RSS統合 | SP-048 | Core のresearch_cli入力に依存 |
| **D** | NotebookLM自動化 | SP-047, SP-051 | 独立 (入力層) |
| **E** | Google Slides API | 新規 | Core のCSV image_pathに出力 |

## 依存関係図

```
[Worker D: NLM自動化]     独立
        |
        v (テキスト出力)
[Core: パイプライン] <--- [Worker C: Feed] (トピック入力)
        |
        +---> CSV出力 ---> [Worker A: YMM4]
        +---> メタデータ --> [Worker B: YouTube]
        +---> image_path <-- [Worker E: Slides API]
```

## 共通ルール
1. docs/DESIGN_FOUNDATIONS.md を最初に読むこと
2. 変更は自分の担当ファイルに限定すること
3. インターフェース変更が必要な場合はコア開発者に相談
4. テストを追加すること (既存テストを壊さない)
5. CLAUDE.md の DECISION LOG に該当する判断があれば記録すること

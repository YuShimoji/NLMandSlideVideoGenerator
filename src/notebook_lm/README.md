# src/notebook_lm/

## ディレクトリ名について

このディレクトリ名は歴史的遺産である。
プロジェクト初期に NotebookLM 統合を想定して作成されたが、
NotebookLM API が非公開だったため、実際には Gemini 統合・ソース収集・台本処理のコードが格納されている。

**NotebookLM 固有のコードはゼロ。**

## 実際の内容

| ファイル | 内容 |
|---|---|
| `gemini_integration.py` | Gemini API による台本生成 |
| `source_collector.py` | Brave Search API による Web ソース収集 |
| `transcript_processor.py` | 台本テキストのフォーマット変換 |
| `script_alignment.py` | ソースと台本のアライメント |
| `audio_generator.py` | レガシースタブ (常に無音WAV、YMM4が音声担当) |

## 参照

- `docs/DESIGN_FOUNDATIONS.md` — 三層モデルと責務境界
- `docs/notebooklm_drift_analysis.md` — NotebookLM→Gemini ドリフトの経緯

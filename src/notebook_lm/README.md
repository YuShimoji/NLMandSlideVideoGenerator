# src/notebook_lm/

## 概要

NotebookLM + Gemini 統合のPython変換層。
DESIGN_FOUNDATIONS.md 三層モデルの「変換層」に相当する。

## 現行ファイル

| ファイル | 内容 | 状態 |
|---|---|---|
| `gemini_integration.py` | Gemini API による台本構造化 (speaker/text分離) | 現行 |
| `audio_transcriber.py` | Gemini Audio API による音声→構造化JSON (SP-051) | 現行 |
| `script_alignment.py` | ソースと台本のアライメント | 現行 |
| `transcript_processor.py` | TranscriptInfo データクラスのみ有効。シミュレーション機能は撤去済み | レガシー残存 |
| `audio_generator.py` | AudioInfo データクラスのみ有効。音声生成機能は撤去済み | レガシー残存 |
| `source_collector.py` | 廃止。コード残存だが未使用 (Brave Search廃止済) | レガシー残存 |

## レガシー境界

`docs/DESIGN_FOUNDATIONS.md` Section 5 参照。
- Python側の音声合成/TTS: 全削除済み
- SourceCollector (Brave Search): 廃止
- Gemini台本「生成」: フォールバックのみ。正規はNotebookLMテキストの「構造化」
- 音声生成: YMM4が唯一の音声合成環境

## 参照

- `docs/DESIGN_FOUNDATIONS.md` -- 三層モデルと責務境界
- `docs/DELIVERABLE_MAP.md` -- 成果物駆動の開発優先順位

# NotebookLM→Gemini ドリフト分析

日付: 2026-03-19
ステータス: 分析完了

---

## 問題の要約

プロジェクト名 "**NLM**andSlideVideoGenerator" の NLM = NotebookLM。
本来 NotebookLM の台本/スライド生成を基盤とする設計だったが、現在は Gemini プロンプト駆動による独自台本生成に完全移行している。

**この移行は明示的な設計判断として記録されていない。** DECISION LOG に「NotebookLMを廃止してGeminiに移行する」という決定エントリが存在しない。

---

## 時系列

| 時期 | 出来事 | 影響 |
|------|--------|------|
| プロジェクト初期 | NotebookLM Audio Overview を台本生成の基盤として構想 | プロジェクト名に "NLM" が入る |
| 2025-11-26 | コミット b78d25e: "Gemini+TTS alternative workflow for NotebookLM audio generation" | NotebookLM API の代替として Gemini+TTS を実装。名目上は NotebookLM のための代替ワークフロー |
| 2025-12-01 | CSV駆動動画生成モード実装 | パイプラインが CSV 中心に移行 |
| 2026-02-03 | コミット 550ddd6: "Complete NotebookLM/Gemini API implementation verification" (TASK_003) | Gemini API が正式に検証完了。NotebookLM との組み合わせ検証として報告されているが、実態は Gemini 単独使用 |
| 2026-03-04 | DECISION: YMM4一本化 (Path A primary) | Python は前処理・素材準備、YMM4 が最終レンダラー。NotebookLM の位置づけに言及なし |
| 2026-03-07 | DECISION: Gemini API統合 (CsvScriptCompletionPlugin) | Gemini が台本生成の公式手段に。NotebookLM に関する検討なし |
| 2026-03-07 | DECISION: Path B (MoviePy) 完全削除 | 外部TTS連携不要。NotebookLM 音声も事実上不要に |
| 2026-03-08 | DECISION: Path B完全削除 + TTS no-opスタブ化 | audio_generator.py: _tts_is_available() が常に False を返す |
| 2026-03-17 | DECISION: Geminiモデルフォールバックチェーン | Gemini が台本生成の唯一のLLMプロバイダーとして確定 |
| 2026-03-18 | SP-043 Multi-LLM Provider 100%完成 | 5プロバイダー (Gemini/OpenAI/Claude/DeepSeek/Mock) 対応。NotebookLM はプロバイダーに含まれない |

---

## ドリフトの原因分析

### 1. NotebookLM API の非公開性

NotebookLM の Audio Overview / スライド生成は Web UI 経由の機能であり、公開 API が存在しなかった (2025年11月時点)。ブラウザ自動操作が必要で、信頼性が低い。

### 2. 「代替」が「本流」に昇格した

b78d25e のコミットメッセージ "Gemini+TTS **alternative** workflow **for** NotebookLM audio generation" が象徴的。Gemini は NotebookLM のための代替手段として導入されたが、NotebookLM 本体の統合が実現しないまま、代替手段がいつの間にか本流になった。

### 3. 決定の不在

DECISION LOG に以下の決定が記録されるべきだったが、されなかった:
- "NotebookLM の直接統合を断念し、Gemini プロンプト駆動に移行する"
- "NotebookLM のスライド生成を使用せず、PIL でスライドを独自生成する"

これらの決定が暗黙的に行われたため、元の設計意図（NotebookLM ベース）との乖離が検出されなかった。

### 4. 能力の置換なしの廃止

NotebookLM が提供していた（提供するはずだった）以下の能力が、同等品質で置換されないまま廃止された:
- **台本品質**: NotebookLM の対話生成品質 >> Gemini プロンプトの対話生成品質
- **スライド生成**: NotebookLM のスライド生成 >> PIL/Pillow の箇条書きスライド
- **情報統合力**: NotebookLM のソース理解力 >> Gemini の単発プロンプト

---

## 現在のコード状態

| パス | 状態 | 内容 |
|------|------|------|
| src/notebook_lm/ | 歴史的遺産としてのディレクトリ名のみ | Gemini統合、ソース収集、アライメント等が格納されているが NotebookLM 固有のコードはゼロ |
| src/notebook_lm/gemini_integration.py | Gemini プロンプト駆動の台本生成 | notebook_lm ディレクトリにあるが NotebookLM とは無関係 |
| src/notebook_lm/audio_generator.py | TTS スタブ (常に False) | _tts_is_available() が常に False。NotebookLM 音声は使用不可 |
| src/core/providers/script/notebook_lm_provider.py | 存在するが内容未確認 | 名前のみ NotebookLM |

---

## 推奨アクション

### 即時 (SP-047 Phase 1)

1. NotebookLM の現在の API/統合オプションを再調査する (2026年3月時点)
2. NotebookLM のスライド生成機能の入出力仕様を確認する
3. 現行パイプラインへの統合方法を設計する

### 設計判断 (HUMAN_AUTHORITY)

1. NotebookLM をどのレベルで再統合するか
   - A: 台本 + スライド の両方を NotebookLM に委譲
   - B: 台本のみ NotebookLM、スライドは別手段
   - C: NotebookLM の出力を「ベース」とし、Gemini で後処理/カスタマイズ

2. `src/notebook_lm/` ディレクトリのリネーム
   - 現在は歴史的遺産。実態に合わせてリネームするか、NotebookLM 再統合に備えて維持するか

---

## DECISION LOG 追記候補

```
| 2026-03-19 | NotebookLM→Gemini ドリフトを検出。NotebookLM ベースへの回帰を決定 | Gemini維持/NotebookLM回帰/ハイブリッド | プロジェクト本来の設計意図。Gemini プロンプトの台本品質が YouTube 公開水準に達していない (docs/video_quality_diagnosis.md) |
```

# TASK_017: Multi-Language Alignment Improvement

## 背景・目的

現在の Research パッケージによる情報収集(英語中心)と、NotebookLMによる台本生成(日本語中心)のアライメント処理において、`key_claims`の言語の壁によりmissing(未照合)が多発している。これを解決するために、多言語(英・日)間の照合精度向上を図る。

## 作業分類

A. 目標直結 / B. 生産性向上

## Done 条件

- [ ] 英語 `key_claims` と 日本語台本の照合において、意味的な一致を高精度で判定できるロジック（翻訳APIの噛ませ込み、または判定用プロンプトの改修）を実装する
- [ ] 既存のテストシナリオ(`test_script_alignment.py`等)をパスし、追加の多言語照合テストを記述・パスすること
- [ ] 手動による `adopted` 扱いを極力減らし、自動での `supported` 判定率を向上させること

## 背景コンテキスト

- `src/notebook_lm/script_alignment.py` の改修が主となる。
- 現在の利用LLM(Gemini等)に照合ロジックを委ねるか、事前にDeepLや無償の翻訳APIで `key_claims` を日本語化してから照合させるかのアーキテクチャ選定を含む。

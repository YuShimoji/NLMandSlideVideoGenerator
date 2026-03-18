# マルチLLMプロバイダー対応 (SP-043)

**最終更新**: 2026-03-18
**ステータス**: partial (Phase 1-3 完了, Phase 4 未着手)

---

## 1. 目的

Gemini API への単一依存を解消し、複数の LLM プロバイダー (Claude / OpenAI / DeepSeek 等) を
選択可能にする。「一晩3本」の制作ワークフローを API クォータ制約に左右されない設計にする。

### 1.1 現状 (As-Is)

- 全 LLM 呼び出しが `google.genai` (Gemini API) にハードコード
- 無料枠: 20 req/day → 1動画でほぼ枯渇
- 有料プランへの移行に技術的問題あり
- 依存箇所: 4ファイル (gemini_integration, script_alignment, segment_classifier, stock_image_client)
- 画像生成 (Imagen 4): 有料プランのみ → 別問題として扱う

### 1.2 目標 (To-Be)

- `.env` の `LLM_PROVIDER` で使用プロバイダーを切替
- 台本生成・alignment・キーワード抽出・セグメント分類が全て抽象化
- ユーザーが手持ちの API キーで即座に動作

---

## 2. LLM 呼び出しの分類

パイプラインで LLM が使われる箇所と要求:

| 用途 | ファイル | 入力 | 出力 | 品質要求 |
|------|---------|------|------|---------|
| 台本生成 | gemini_integration.py | トピック+ソース+プリセット | ScriptBundle (JSON) | 高 (創造性) |
| Alignment | script_alignment.py | セグメント+ソース | supported/orphaned/conflict | 中 (分析) |
| セグメント分類 | segment_classifier.py | セグメントテキスト | visual/textual | 低 (分類) |
| キーワード抽出 | segment_classifier.py | セグメント+トピック | 英語キーワード | 低 (抽出) |
| クエリ翻訳 | stock_image_client.py | 日本語クエリ | 英語クエリ | 低 (翻訳) |

---

## 3. ILLMProvider インターフェース

```python
class ILLMProvider(Protocol):
    """LLM プロバイダーの共通インターフェース。"""

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        """テキスト生成。台本生成・alignment 等で使用。"""
        ...

    @property
    def model_name(self) -> str:
        """使用中のモデル名。"""
        ...
```

---

## 4. プロバイダー実装

### 4.1 GeminiLLMProvider (既存)

- SDK: `google-genai`
- モデル: `gemini-2.5-flash`
- 料金: 無料枠 20 req/day、有料は $0.15/1M input tokens
- 備考: 既存コードをラップ

### 4.2 OpenAILLMProvider

- SDK: `openai`
- モデル: `gpt-4o-mini` (低コスト) / `gpt-4o` (高品質)
- 料金: gpt-4o-mini $0.15/$0.60 per 1M tokens (input/output)
- 画像生成: DALL-E 3 対応可能 (別途)

### 4.3 ClaudeLLMProvider

- SDK: `anthropic`
- モデル: `claude-haiku-4-5` (低コスト) / `claude-sonnet-4-6` (高品質)
- 料金: haiku $1/$5 per 1M tokens
- 備考: 日本語品質が高い

### 4.4 DeepSeekLLMProvider

- SDK: `openai` (OpenAI互換API)
- モデル: `deepseek-chat`
- 料金: $0.07/$0.28 per 1M tokens (最安級)
- 備考: OpenAI互換のため実装コスト低

---

## 5. コスト試算 (30分動画 1本)

1動画あたりの推定トークン消費:
- 台本生成: ~2K input + ~3K output = ~5K tokens
- Alignment: ~30 x 0.5K = ~15K tokens
- キーワード抽出: ~30 x 0.3K = ~9K tokens
- 分類: ~30 x 0.2K = ~6K tokens
- 合計: ~35K tokens/動画

| プロバイダー | モデル | 1動画コスト | 3動画/日コスト | 月30動画 |
|-------------|--------|-----------|-------------|---------|
| Gemini | 2.5-flash (無料) | $0 (20req制限) | 不可 | 不可 |
| Gemini | 2.5-flash (有料) | ~$0.01 | ~$0.03 | ~$0.30 |
| OpenAI | gpt-4o-mini | ~$0.01 | ~$0.03 | ~$0.30 |
| Claude | haiku-4-5 | ~$0.05 | ~$0.15 | ~$1.50 |
| DeepSeek | deepseek-chat | ~$0.005 | ~$0.015 | ~$0.15 |

---

## 6. 実装方針

### Phase 1: 抽象化レイヤー (完了)

- `src/core/llm_provider.py` — ILLMProvider Protocol + 5プロバイダー + ファクトリ
- `.env` の `LLM_PROVIDER` / `LLM_MODEL` / `LLM_API_KEY` 対応
- 25 テスト全 PASS

### Phase 2: プロバイダー実装 (完了)

- OpenAILLMProvider: `openai.AsyncOpenAI` SDK
- ClaudeLLMProvider: `anthropic.AsyncAnthropic` SDK
- DeepSeekLLMProvider: OpenAI互換 (`base_url="https://api.deepseek.com"`)
- GeminiLLMProvider: `asyncio.to_thread` で sync→async 変換
- MockLLMProvider: テスト・フォールバック用

### Phase 3: 既存コードの移行 (完了)

- gemini_integration.py → ILLMProvider 注入 (後方互換: api_key のみでも動作)
- segment_classifier.py → ILLMProvider 注入 + `_run_async` sync-async ブリッジ
- stage_runners.py → `create_llm_provider()` ファクトリ経由
- gemini_provider.py → ILLMProvider 注入対応
- helpers.py → `LLM_PROVIDER` env var 対応
- research_cli.py → fallback_used / actual_provider 追跡
- pipeline_stats.py → record_llm_provider / record_fallback 追加
- 1105 テスト全 PASS / 0 failed

### Phase 4: 設定 UI + 追加プロバイダー (未着手)

- 設定 UI (Streamlit)
- 実 API キーでの統合テスト
- プロバイダー別プロンプトチューニング

---

## 7. 影響範囲

- `src/core/llm_provider.py` — 新規
- `src/notebook_lm/gemini_integration.py` — 移行
- `src/notebook_lm/script_alignment.py` — 移行
- `src/core/visual/segment_classifier.py` — 移行
- `src/core/visual/stock_image_client.py` — 移行
- `config/settings.py` — LLM 設定追加
- `.env.example` — LLM 設定追加

---

## 8. 受け入れ条件

- [ ] `LLM_PROVIDER=openai` でパイプラインが完走する
- [ ] `LLM_PROVIDER=claude` でパイプラインが完走する
- [ ] 既存の `LLM_PROVIDER=gemini` が引き続き動作する
- [ ] 既存テスト全 PASS
- [ ] 台本品質が Gemini と同等以上 (目視確認)

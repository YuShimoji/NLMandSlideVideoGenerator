# E2E Pipeline Test Results (2026-03-17)

## Test Configuration
- Topic: 「2026年の量子コンピュータ最新動向」
- Style: news
- Duration: 300s (5min)
- Auto-images: ON
- APIs: Gemini=SET, Pexels=SET, Pixabay=SET, Google CSE=MISSING

## Results

### Pipeline Execution
| Step | Status | Duration | Notes |
|------|--------|----------|-------|
| 1. collect | OK | 0.5s | Google Search API未設定 → シミュレーションフォールバック |
| 2. script | OK | 30.7s | Gemini 2.5-flash、12セグメント生成 |
| 3. align | OK | 15.5s | supported=3, orphaned=9, conflict=0 |
| 4. review | OK | - | auto mode: 9 adopted |
| 5. orchestrate | OK | 35.9s | stock=3, ai=0, generated=9 |
| 6. assemble | OK | - | 12行CSV出力、Pre-Export 0 errors |

### Output
- timeline.csv: 12行、4列 (speaker, text, image, animation)
- stock_images/: 3枚 (Pexels)
- generated_slides/: 9枚 (TextSlideGenerator)
- image_credits.txt: 3件

### Issues Found

#### P1: Imagen 3.0 モデル名エラー (FIXED)
- `imagen-3.0-generate-002` → 404 NOT_FOUND
- Fix: `imagen-3.0-generate-001` に変更 + IMAGEN_MODEL env var

#### P2: Gemini 2.0-flash クォータ枯渇 (429)
- キーワード分類時にフォールバックモデルが枯渇
- フォールバックチェーンは機能したが分類精度低下
- 対策: Gemini有料プランまたはクォータリセット後の再テスト

#### P3: Google Search API未設定 (RESOLVED — Brave Search移行済み)
- ソース収集が全て Simulated source → 台本の情報密度低下
- ~~.env の GOOGLE_SEARCH_API_KEY / GOOGLE_SEARCH_CX が未設定~~
- **解決済み**: 2026-03-18に Brave Search API へ移行。BRAVE_SEARCH_API_KEY を設定すればソース収集が動作する

#### P4: 画像ヒット率 25% (3/12)
- Pexels: 3/5 (日本語クエリのマッチ率)
- AI (Imagen): 0/2 (モデル名エラーで全失敗)
- TextSlide fallback: 9枚生成
- 対策: Imagen修正後に再テスト、Pexelsクエリ英語翻訳の改善

#### P5: TextSlide内のspeaker名が変換前 (Host1)
- speaker_mapping はCsvAssembler段階で適用
- TextSlideGeneratorはOrchestrator段階で生成されるため変換前の名前
- 最終動画ではYMM4字幕が表示されるため実害は限定的
- 改善案: OrchestratorにもspeakerMapping渡し (HUMAN_AUTHORITY)

#### P6: ログ文字化け (Windows cp1252)
- 日本語ログがconsoleで文字化け
- SimpleLoggerのエンコーディング問題 (既知)

#### P7: GOOGLE_API_KEY重複警告
- .envにGOOGLE_API_KEY (placeholder) + GEMINI_API_KEY (実キー)
- google-genai SDKが毎回警告を出力 (9回)
- 対策: .envからGOOGLE_API_KEYのプレースホルダーを削除

## Re-test #2 (after .env fix + speaker_mapping)
- Google Search API: 403 (API key or Custom Search Engine ID issue)
- Pexels: 3/3 (100% hit rate)
- Segments: 7 (appropriate for 5min)
- Speaker mixing in segment: STILL PRESENT (P5 confirmed as major issue)

## Re-test #3 (after prompt fix)
- **1-segment-1-speaker: FIXED** — prompt constraints enforced
- **Speaker names in text: FIXED** — "れいむさん" instead of "Host1さん"
- Pexels: 3/3 (100%)
- Pre-Export: 0 errors
- Google Search: still 403 (Cloud Console config needed)
- Pipeline time: 40s

## 30min E2E Test (2026-03-18, Brave Search)
- Brave Search: 5 real sources (kpmg, arakiplaw, a-x, fidx, omake)
- Segments: 29 (within 25-35 target range)
- Stock images: 11/12 (92%)
- TextSlide fallback: 18
- Image coverage: 100%
- Alignment: supported=24, orphaned=4, conflict=1
- Pipeline time: 338s (align=253s is 75% bottleneck)

## API Status Investigation (2026-03-18)
- Imagen 3: **SHUTDOWN** (all variants 404/deprecated)
- Imagen 4: 3 models available (standard/fast/ultra) but **paid plans only** (400 error)
- Gemini 2.5-flash: working (free tier still available)
- Gemini 2.0-flash: **FREE TIER EXHAUSTED** (429, `free_tier` in error)
- API key is on **free plan project** — billing activation needed at ai.dev/projects

## Remaining Issues
- Gemini billing: API key on free plan. Need to activate billing at ai.dev/projects
- Imagen 4: requires paid plan (400 INVALID_ARGUMENT)
- Alignment bottleneck: 75% of pipeline time (252s for 30min video)

## Next Steps
1. ~~Google Cloud Console でCustom Search APIの有効化を確認~~ → Brave Search移行済み (BRAVE_SEARCH_API_KEY設定で動作)
2. YMM4でCSVインポート → Voice生成 → mp4レンダリング (手動)
3. mp4出力のMP4QualityChecker検証
4. Gemini有料プラン検討 (バッチ制作に必要)

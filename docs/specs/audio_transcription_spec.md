# 音声自動文字起こし + 構造化パイプライン

SP-051 | Status: partial | pct: 70 | 作成: 2026-03-22
準拠: SP-050 E2E ワークフロー仕様 / DESIGN_FOUNDATIONS.md Section 0

---

## 目的

NotebookLM Audio Overview の音声ファイル (.mp3) を入力し、
**文字起こし + 台本構造化を自動で行う** モジュールを新設する。

現行フローの Phase 2（人間が NLM に音声を再投入してテキスト化）を自動化し、
手動操作を「NLM Audio Overview のダウンロード」1回のみに削減する。

---

## 現行フロー vs 新フロー

### 現行 (手動5ステップ)

```
人間: NLM → ソース投入 → Audio Overview 生成 → 音声DL
人間: NLM → 音声を再投入 → テキスト化 → .txt にコピー保存
CLI:  --transcript transcript.txt → Gemini 構造化 → CSV
```

### 新フロー (手動1ステップ)

```
人間: NLM → ソース投入 → Audio Overview 生成 → 音声DL
CLI:  --audio overview.mp3 → Gemini 音声→構造化JSON → CSV
```

手動操作: NLM Audio Overview DL のみ (1回)
自動化: 文字起こし + 構造化 + CSV (全自動)

---

## アーキテクチャ選択

### 方式A: 1段階方式 (Gemini Audio → 構造化JSON) ← 採用

音声ファイルを Gemini に直接送り、構造化 JSON を1回の API コールで取得。

```
audio.mp3 → Gemini 2.5 Flash (音声入力 + 構造化プロンプト) → JSON
```

**利点:**
- API コール 1回 = コスト半減、レイテンシ半減
- 中間テキストの劣化・情報損失がない
- 既存 `google-generativeai` SDK で完結 (新依存なし)
- 話者分離を音声特徴から直接推定可能 (テキストのみより精度が高い可能性)

**リスク:**
- Gemini が音声を意訳・要約するリスク (→ プロンプトで「忠実な文字起こし」を強制)
- テキスト中間出力がないため、文字起こし品質の個別検証が難しい

### 方式B: 2段階方式 (Whisper → Gemini 構造化) ← フォールバック

```
audio.mp3 → Whisper API → transcript.txt → Gemini 構造化 → JSON
```

**利点:**
- 文字起こし精度が最も高い (Whisper は専用ASRモデル)
- 中間テキストの確認・手動修正が可能
- 既存の `--transcript` パスをそのまま利用

**リスク:**
- API コール 2回 = コスト倍
- OpenAI API キーが追加で必要
- Whisper API のファイルサイズ制限 (25MB)

### 方式C: 2段階方式 (Gemini 文字起こし → Gemini 構造化) ← 中間案

```
audio.mp3 → Gemini (文字起こしのみ) → transcript.txt → Gemini (構造化) → JSON
```

**利点:**
- 中間テキスト確認可能 + API キー統一 (Gemini のみ)

**リスク:**
- API コール 2回 = 方式A の倍コスト
- 方式A で十分なら不要な複雑化

### 決定

**方式A を採用。方式B/C は方式A の品質が不十分な場合のフォールバック。**

中間テキスト出力はオプション (`--save-transcript`) として対応する。

---

## 新モジュール設計

### 1. AudioTranscriber クラス

**配置**: `src/notebook_lm/audio_transcriber.py`

```python
class AudioTranscriber:
    """NLM Audio Overview → 構造化JSON 変換。

    Gemini Audio API を使い、音声ファイルから直接
    speaker/text/key_points の構造化JSONを生成する。
    """

    SUPPORTED_FORMATS = {".mp3", ".wav", ".aac", ".ogg", ".flac"}
    MAX_FILE_SIZE_MB = 200  # Gemini File API 上限は 2GB だが実用上の制限

    async def transcribe_and_structure(
        self,
        audio_path: Path,
        topic: str,
        target_duration: float = 300.0,
        language: str = "ja",
        style: str = "default",
        speaker_mapping: Optional[Dict[str, str]] = None,
        save_transcript: Optional[Path] = None,  # 中間テキスト保存先
    ) -> ScriptInfo:
        """音声ファイルから構造化台本を生成。

        1. Gemini File API で音声をアップロード
        2. 構造化プロンプト + 音声で generate_content
        3. JSON レスポンスを ScriptInfo に変換
        4. (オプション) 中間テキストを保存
        """
        ...

    async def transcribe_only(
        self,
        audio_path: Path,
        language: str = "ja",
    ) -> str:
        """音声ファイルをテキストに文字起こしのみ。

        --save-transcript 用、またはデバッグ用。
        """
        ...
```

### 2. プロンプト設計

#### 1段階プロンプト (音声 → 構造化JSON)

```
あなたは音声対話の文字起こしと構造化の専門家です。

添付された音声ファイルを聞き、以下の JSON 形式で構造化してください。

【重要な制約】
- 音声の内容を忠実に文字起こししてください。要約・意訳・省略は禁止です。
- 話者を音声の特徴（声質・トーン）から識別し、「Host1」「Host2」に割り当ててください
- 1セグメント = 1話者の連続発話
- セグメントは50-150文字程度で分割
- 元の対話の論理構造（導入→本論→まとめ等）を維持

【出力形式】
{JSON形式 (既存の _build_structure_prompt と同一)}
```

#### 文字起こしのみプロンプト

```
添付された音声ファイルを忠実に文字起こししてください。
要約や意訳は行わず、話された内容をそのまま書き起こしてください。
話者の交代が明らかな箇所には空行を入れてください。
```

### 3. CLI 拡張

`research_cli.py` の `pipeline` コマンドに `--audio` オプションを追加:

```
python scripts/research_cli.py pipeline \
  --topic "AIの最新動向" \
  --audio data/topics/ai_latest/audio/overview.mp3 \
  --auto-images \
  --duration 300
```

**オプション:**

| オプション | 説明 | デフォルト |
|---|---|---|
| `--audio PATH` | 音声ファイルパス (.mp3/.wav 等) | None |
| `--save-transcript` | 中間テキストを transcript/ に保存 | False |
| `--transcript PATH` | テキストファイル直接投入 (既存、変更なし) | None |

**優先順位:** `--audio` と `--transcript` が両方指定された場合、`--audio` を優先。

### 4. パイプライン統合

`run_pipeline()` の Step 2 を拡張:

```python
# --- Step 2: script generation ---
if audio_path:
    # 1段階方式: 音声→構造化JSON (SP-051)
    transcriber = AudioTranscriber(...)
    script_info = await transcriber.transcribe_and_structure(
        audio_path, topic, target_duration, language, style, speaker_mapping,
        save_transcript=work_dir / "transcript" / "transcript.txt" if save_transcript else None,
    )
elif transcript_text:
    # 既存: テキスト→構造化JSON (session 19)
    script_info = await provider.generate_script(topic, sources, transcript_text=transcript_text)
else:
    # フォールバック: ソースから生成
    script_info = await provider.generate_script(topic, sources)
```

### 5. 依存関係

| パッケージ | バージョン | 用途 | 新規/既存 |
|---|---|---|---|
| `google-generativeai` | >=0.8.0 | Gemini Audio API | 既存 |

**新規依存なし。** 既存の `google-generativeai` SDK が音声入力をネイティブサポート。

---

## Gemini File API の利用

NLM Audio Overview は通常 5-15分 の音声 (MP3 で 5-15MB 程度)。
20MB 以下なら inline data で送信可能だが、安定性のため File API を使用する。

```python
from google import genai

client = genai.Client(api_key=api_key)

# 1. 音声ファイルをアップロード
uploaded = client.files.upload(file=audio_path)

# 2. 構造化プロンプト + 音声で生成
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=[structure_prompt, uploaded],
)

# 3. JSON パース
script_data = json.loads(response.text)
```

---

## 品質ゲート

| チェック項目 | 基準 | 自動/手動 |
|---|---|---|
| 音声ファイル形式 | SUPPORTED_FORMATS に含まれる | 自動 |
| ファイルサイズ | MAX_FILE_SIZE_MB 以下 | 自動 |
| セグメント数 | > 0 | 自動 |
| セグメント粒度 | 平均 15-25 秒/セグメント | 自動 |
| speaker 名 | 2名以上 | 自動 |
| text 非空 | 全セグメント | 自動 |
| 出力言語 | 指定言語と一致 | 自動 (サンプリング) |

---

## テスト戦略

### ユニットテスト

1. `AudioTranscriber` のファイル形式バリデーション
2. プロンプト構築 (1段階 / 文字起こしのみ)
3. JSON パース + ScriptInfo 変換
4. CLI `--audio` オプション解析
5. `--audio` と `--transcript` の優先順位

### 統合テスト (モック)

6. Gemini File API アップロード → generate_content のモック実行
7. パイプライン `run_pipeline()` の `--audio` パス通過確認

### E2E テスト (要 API キー)

8. 短い音声ファイル (10秒程度のサンプル) で実 API コール
   - テスト音声は `tests/fixtures/` に配置 (著作権クリアの短い音声)

---

## SP-050 との関係

SP-050 Phase 2 の手順を以下に更新する:

**現行:**
```
Phase 2: NotebookLM テキスト化 (人間操作)
  1. NLM に音声を再投入
  2. テキスト化
  3. テキストをコピーしてファイル保存
```

**更新後:**
```
Phase 2: 音声文字起こし + 構造化 (Python 自動)
  入力: Audio Overview 音声ファイル (.mp3)
  処理: Gemini Audio API で文字起こし + 構造化 (1回のAPIコール)
  出力: 構造化台本 JSON

  フォールバック: --transcript でテキストを手動投入
```

Phase 2 が自動化されることで、人間の操作は Phase 0-1 (ソース選定 + NLM Audio Overview DL) のみになる。

---

## 実装フェーズ

### Phase 1: コアモジュール + CLI
- `AudioTranscriber` クラス実装
- `--audio` CLI オプション追加
- ユニットテスト + モック統合テスト
- SP-050 Phase 2 更新

### Phase 2: 品質検証 + 調整
- 実音声での E2E 実行
- プロンプト調整 (忠実性 vs 構造化品質のバランス)
- `--save-transcript` 実装
- 発見事項の記録

### Phase 3: (必要に応じて) フォールバック強化
- 方式B (Whisper) の実装 (Gemini 品質不十分の場合のみ)
- 音声前処理 (ノイズ除去等、必要に応じて)

---

## リスクと緩和策

| リスク | 影響 | 緩和策 |
|---|---|---|
| Gemini が音声を要約・意訳する | 台本の忠実性が低下 | プロンプトで「忠実な文字起こし」を強制。`--save-transcript` で中間確認可能に |
| Gemini 無料枠の制限 (20req/day) | 試行回数が限られる | 短い音声でテスト。本番は1日数本で十分 |
| 長時間音声 (30分+) での品質低下 | 後半のセグメント精度が落ちる | 初回は短尺 (5-10分) で検証。必要なら分割処理を追加 |
| File API アップロード失敗 | パイプライン停止 | リトライ (3回) + inline data フォールバック |

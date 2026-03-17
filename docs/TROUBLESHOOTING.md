# Troubleshooting Guide

**Version**: 2.0
**Last Updated**: 2026-03-17
**Project**: NLMandSlideVideoGenerator

---

## Quick Navigation

- [Audio Issues](#audio-issues)
- [YMM4 Plugin Issues](#ymm4-plugin-issues)
- [Video Generation Issues](#video-generation-issues)
- [Gemini API Issues](#gemini-api-issues)
- [Stock Image / Visual Resource Issues](#stock-image--visual-resource-issues)
- [Pipeline Resume Issues](#pipeline-resume-issues)
- [Environment Setup Issues](#environment-setup-issues)
- [CI/CD Issues](#cicd-issues)

---

## Audio Issues

### Problem: No audio output device detected

**Symptoms:**
- Audio diagnostic tool reports "No devices detected"
- Video generation completes but has no audio
- ffmpeg errors about audio device

**Diagnosis:**
```bash
# Run audio diagnostics
python scripts/test_audio_output.py
```

**Solutions:**

| Solution | Steps | When to Use |
|----------|-------|-------------|
| **Update Audio Drivers** | 1. Open Device Manager<br>2. Expand "Sound, video and game controllers"<br>3. Right-click audio device → Update driver | Default audio device not showing |
| **Enable Disabled Device** | 1. Right-click speaker icon in taskbar<br>2. Open Sound settings<br>3. Check if device is disabled<br>4. Enable and set as default | Device shows as disabled |
| **Check FFMPEG** | 1. Verify ffmpeg is in PATH<br>2. Run `ffmpeg -version`<br>3. Set `FFMPEG_EXE` environment variable if needed | ffmpeg not found |

> **注**: 外部TTS連携コードは 2026-03-04 に全削除されました。音声生成は YMM4 内蔵ゆっくりボイスのみを使用してください。

---

## YMM4 Plugin Issues

### Problem: YMM4 Plugin not appearing in plugin list

**Symptoms:**
- NLMSlidePlugin not visible in YMM4 Tools menu
- YMM4 starts normally but plugin missing
- Error: "Plugin could not be loaded"

**Diagnosis:**
```powershell
# Check plugin deployment
$ymm4Path = "C:\Users\$env:USERNAME\AppData\Local\YukkuriMovieMaker4"
Test-Path "$ymm4Path\user\plugin\NLMSlidePlugin\NLMSlidePlugin.dll"

# Check YMM4 version
$ymm4Exe = "$ymm4Path\YukkuriMovieMaker.exe"
(Get-Item $ymm4Exe).VersionInfo
```

**Solutions:**

| Solution | Steps | When to Use |
|----------|-------|-------------|
| **Deploy Plugin** | 1. Run `.\scripts\deploy_ymm4_plugin.ps1 -Configuration Release`<br>2. Verify deployment summary<br>3. Restart YMM4 | Plugin not deployed |
| **Update YMM4 Version** | 1. Check YMM4 version (must be 4.33+)<br>2. Download latest from [official site](https://manjubox.net/ymm4/)<br>3. Reinstall | YMM4 version too old |
| **Check .NET Version** | 1. Verify .NET 10.0 is installed<br>2. Run `dotnet --list-runtimes`<br>3. Install .NET 10.0 SDK if missing | .NET runtime missing |
| **Fix Directory.Build.props** | 1. Open `ymm4-plugin/Directory.Build.props`<br>2. Update `<YMM4DirPath>` to your YMM4 installation path<br>3. Rebuild plugin | Wrong YMM4 path |

**Expected Plugin Structure:**
```
C:\Users\<USER>\AppData\Local\YukkuriMovieMaker4\
└── user\
    └── plugin\
        └── NLMSlidePlugin\
            └── NLMSlidePlugin.dll
```

---

### Problem: CSV Import Dialog freezes or crashes

**Symptoms:**
- Dialog becomes unresponsive during import
- YMM4 crashes when importing large CSV
- Progress bar stops updating

**Diagnosis:**
```powershell
# Check YMM4 plugin logs
$logPath = "$env:LOCALAPPDATA\NLMSlidePlugin\logs\csv_import_runtime.log"
Get-Content $logPath -Tail 50
```

**Solutions:**

| Solution | Steps | When to Use |
|----------|-------|-------------|
| **Close YMM4 Before Deployment** | 1. Close all YMM4 instances<br>2. Redeploy plugin<br>3. Restart YMM4 | Plugin file locked |
| **Reduce CSV Size** | 1. Split large CSV into smaller batches (e.g., 100 rows)<br>2. Import in multiple passes<br>3. Use "Preview" to validate before import | Large CSV (>500 rows) |
| **Check Audio Files** | 1. Verify all audio files exist<br>2. Check file encoding (should be WAV)<br>3. Use "Log/Error" tab to see missing files | Missing audio warnings |
| **Force Redeploy** | 1. Run `.\scripts\deploy_ymm4_plugin.ps1 -Force`<br>2. This will deploy even if YMM4 is running (risky) | Urgent deployment needed |

---

### Problem: Animation not applied or rendering incorrectly

**Symptoms:**
- ImageItem shows no animation (static when expecting motion)
- Opacity is 0% (image invisible)
- Image zoomed excessively or cropped

**Diagnosis:**
```powershell
# Check runtime log for animation details
$logPath = "$env:LOCALAPPDATA\NLMSlidePlugin\logs\csv_import_runtime.log"
Select-String "ApplyAnimationDirect" $logPath | Select-Object -Last 10
```

**Solutions:**

| Solution | Steps | When to Use |
|----------|-------|-------------|
| **style_template.json の確認** | 1. `config/style_template.json` の `animation` セクションを確認<br>2. `pan_zoom_ratio`, `ken_burns_zoom_ratio` 等の値が妥当か確認 | テンプレート値が不正 |
| **CSV 4列目の確認** | 有効値: `ken_burns`, `zoom_in`, `zoom_out`, `pan_left`, `pan_right`, `pan_up`, `pan_down`, `static`<br>省略時は `ken_burns` | 不正なアニメーション種別 |
| **画像サイズの確認** | fitZoom の計算にソース画像サイズが必要。極端に小さい/大きい画像は回避する | fitZoom が極端な値 |

> **注**: `Animation.From` / `Animation.To` は YMM4 の非推奨API。Values in-place 方式 (`ApplyAnimationDirect`) のみ使用すること。

---

## Video Generation Issues

### Problem: MoviePy removed / CSV pipeline deleted

**Note:** MoviePy バックエンド と run_csv_pipeline.py は 2026-03-08 に完全削除されました。

**現在のワークフロー:**
- YMM4 を使用した動画生成が唯一のサポート方法です
- CSV → YMM4（NLMSlidePlugin でインポート → 音声生成 → 動画レンダリング）

**制作手順:**
1. YMM4 を起動し、新規プロジェクトを作成
2. NLMSlidePlugin の「CSVタイムラインをインポート」からCSVを読み込む
3. YMM4 内でゆっくりボイス音声を自動生成
4. レイアウト・音声を確認・調整
5. YMM4 で動画をレンダリング（書き出し）→ 最終 mp4

**関連ドキュメント:**
- `docs/user_guide_manual_workflow.md` - YMM4 ワークフロー詳細
- `docs/ymm4_export_spec.md` - YMM4 エクスポート仕様
- `docs/integration_test_checklist.md` - 統合検証チェックリスト

---

## Gemini API Issues

### Problem: Gemini API quota exceeded

**Symptoms:**
- `429 Too Many Requests` エラー
- スクリプト生成が途中で停止
- `ResourceExhausted` 例外

**Diagnosis:**
```bash
# 環境変数確認
echo $GEMINI_API_KEY  # 設定されているか
echo $GEMINI_MODEL    # モデル指定 (任意)
```

**Solutions:**

| Solution | Steps | When to Use |
|----------|-------|-------------|
| **フォールバックチェーン確認** | `gemini-2.5-flash` → `gemini-2.0-flash` → モックの順に自動フォールバック | 自動 (設定不要) |
| **モデル指定切替** | `GEMINI_MODEL=gemini-2.0-flash` に設定 (高クォータモデル) | 2.5-flash のクォータ消費が激しいとき |
| **翌日リセットを待つ** | 無料枠は20 req/day。翌日リセット後に再実行 | 急ぎでない場合 |
| **モック実行** | `--mock` オプションでGemini呼び出しをスキップ | テスト・検証目的 |

**フォールバックチェーン:**
```
gemini-2.5-flash (高品質)
  ↓ 失敗時
gemini-2.0-flash (高クォータ)
  ↓ 失敗時
モック (固定テンプレート出力)
```

---

### Problem: Gemini 分類・キーワード抽出が不正確

**Symptoms:**
- セグメント分類が `visual` / `textual` で不適切
- 英語キーワードが的外れ
- 日本語クエリの翻訳品質が低い

**Solutions:**

| Solution | Steps | When to Use |
|----------|-------|-------------|
| **手動CSV修正** | 生成されたCSVの4列目を手動で修正 | 個別セグメントの修正 |
| **`--no-classify` オプション** | research_cli.py に `--no-classify` で分類をスキップ | 全セグメントにストック画像を適用したい場合 |
| **プロンプト確認** | `src/core/visual/resource_orchestrator.py` 内の分類プロンプトを確認 | 体系的に分類品質を改善したい場合 |

---

## Stock Image / Visual Resource Issues

### Problem: ストック画像が取得できない

**Symptoms:**
- `source=none` が大量に出る
- Pexels/Pixabay からの画像ヒット率が低い
- `ConnectionError` や `Timeout`

**Diagnosis:**
```bash
# API キー確認
echo $PEXELS_API_KEY
echo $PIXABAY_API_KEY

# パイプライン実行ログ確認
# research_cli.py の出力に「Stock image hit rate」が表示される
```

**Solutions:**

| Solution | Steps | When to Use |
|----------|-------|-------------|
| **API キー設定** | `.env` に `PEXELS_API_KEY=xxx` を追加 | キー未設定 |
| **フォールバック確認** | Pexels → Pixabay → Gemini Imagen → TextSlideGenerator の順で自動フォールバック | 自動 (設定不要) |
| **レート制限回避** | Pexels: 200 req/hour, Pixabay: 5000 req/hour。大量実行時は間隔を空ける | 429エラー頻発 |
| **テキストスライド許容** | `source=none` のセグメントは TextSlideGenerator で自動生成される | 画像不要の場合 |

**4層フォールバック:**
```
Pexels/Pixabay ストック画像
  ↓ 失敗時
Gemini Imagen (AI生成画像)
  ↓ 失敗時
TextSlideGenerator (テキストスライドPNG)
  ↓ 設定なし
source=none (画像なし)
```

---

## Pipeline Resume Issues

### Problem: パイプラインが途中で失敗し、最初からやり直したくない

**Symptoms:**
- `research_cli.py pipeline` が途中で中断
- Gemini クォータ切れで停止
- ネットワークエラーで一部ステージ失敗

**Solutions:**

| Solution | Steps | When to Use |
|----------|-------|-------------|
| **`--resume` で再開** | `research_cli.py pipeline --topic "..." --resume` で前回の続きから | ステージ単位で再開したい場合 |
| **PipelineState確認** | `output_csv/<topic>/pipeline_state.json` で完了済みステップを確認 | どこまで進んだか確認 |
| **ステート削除** | `pipeline_state.json` を削除して最初からやり直す | 完全リセットしたい場合 |

---

## Environment Setup Issues

### Problem: Python venv activation fails

**Symptoms:**
- `venv\Scripts\activate` doesn't work
- ImportError for missing packages
- Wrong Python version

**Diagnosis:**
```bash
# Check Python version
python --version

# Check if venv exists
Test-Path .\venv

# Check installed packages
.\venv\Scripts\python.exe -m pip list
```

**Solutions:**

| Solution | Steps | When to Use |
|----------|-------|-------------|
| **Create venv** | 1. `python -m venv venv`<br>2. `.\venv\Scripts\activate`<br>3. `pip install -r requirements.txt` | venv missing |
| **Fix Python Version** | 1. Install Python 3.11<br>2. Use `py -3.11 -m venv venv`<br>3. Activate and reinstall packages | Wrong Python version |
| **Reinstall Dependencies** | 1. `pip install --force-reinstall -r requirements.txt`<br>2. Verify installation: `pip check` | Broken packages |
| **Use PowerShell (not CMD)** | 1. Open PowerShell (not Command Prompt)<br>2. Run `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`<br>3. Retry activation | Execution policy error |

**Expected Environment:**
```
Python 3.11.x
google-genai (Gemini SDK — 旧 google-generativeai から移行済み)
fastapi, uvicorn (API server)
streamlit (Web UI)
pillow, numpy (画像処理)
```

---

### Problem: Git merge conflicts

**Symptoms:**
- `git pull` fails with conflicts
- Merge conflict markers in files

**Solutions:**

| Solution | Steps | When to Use |
|----------|-------|-------------|
| **Resolve Conflicts** | 1. Edit conflicting files<br>2. Remove `<<<<`, `====`, `>>>>` markers<br>3. `git add <file>`<br>4. `git commit` | Code conflicts |
| **Accept Remote Changes** | `git checkout --theirs <file>` → `git add` → `git commit` | Always use remote version |
| **Accept Local Changes** | `git checkout --ours <file>` → `git add` → `git commit` | Always use local version |

---

## CI/CD Issues

### Problem: CI pipeline fails

**Symptoms:**
- GitHub Actions workflow fails
- ローカルCIは通るがリモートで失敗
- mypy / ruff でエラー

**Diagnosis:**
```bash
# Run full CI pipeline locally
.\scripts\ci.ps1

# Individual stages
.\venv\Scripts\python.exe -m pytest tests/ -q -m "not slow and not integration" --tb=short
.\venv\Scripts\python.exe -m mypy src/ --ignore-missing-imports
.\venv\Scripts\python.exe -m ruff check src/
```

**Solutions:**

| Solution | Steps | When to Use |
|----------|-------|-------------|
| **ローカルCI実行** | `.\scripts\ci.ps1` で5ステージ全実行 | push前確認 |
| **mypy エラー** | `mypy src/ --ignore-missing-imports` で個別確認。`mypy.ini` で除外設定可能 | 型エラー |
| **ruff エラー** | `ruff check src/ --fix` で自動修正可能 | lint エラー |
| **テスト失敗** | `pytest -v --tb=long` で詳細出力。`-m "not slow"` でマーカー絞り込み | テスト失敗 |

**CI 5ステージ構成:**
```
Stage 1: Python Unit Tests (920 tests, markers: not slow and not integration)
Stage 2: Type Check (mypy src/)
Stage 3: Lint Check (ruff check src/)
Stage 4: Task Report Consistency (node scripts/check_task_reports.js)
Stage 5: YMM4 Plugin Consistency (optional, skips if YMM4 not installed)
```

---

### Problem: CI Rollback workflow

**Note:** ci-rollback.yml は通知専用モード (auto-revert 無効化済み、2026-03-17)。CI失敗時は手動で修正すること。

---

## General Debugging Tips

### Enable Verbose Logging

```python
# In Python scripts
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check System Requirements

| Component | Requirement | Check Command |
|-----------|------------|---------------|
| Python | 3.11+ | `python --version` |
| .NET | 10.0 | `dotnet --list-runtimes` |
| ffmpeg | Latest | `ffmpeg -version` |
| YMM4 | 4.33+ | Check app version |
| Git | 2.30+ | `git --version` |

### Log Locations

- Python: `logs/`
- YMM4 Plugin: `%LOCALAPPDATA%\NLMSlidePlugin\logs\`
- CI: `.github/workflows/` output
- Pipeline state: `output_csv/<topic>/pipeline_state.json`

---

## Manual Testing Checklist

基本E2E は `docs/e2e_verification_guide.md` を、統合検証は `docs/integration_test_checklist.md` を参照。

| Test | Steps | Expected Result |
|------|-------|-----------------|
| **YMM4 Plugin Load** | Deploy plugin → Open YMM4 → Check Tools menu | Plugin appears in menu |
| **CSV Import** | Open CSV Import Dialog → Select test CSV → Preview → Import | Items appear on timeline |
| **8種アニメーション** | CSV 4列目に各種別を指定してインポート | 各アニメーションが視覚的に確認可能 |
| **字幕テンプレート** | 複数話者CSVをインポート → レンダリング | 話者ごとに色分け表示 |
| **BGMテンプレート** | style_template.json にBGM設定 → インポート | BGM AudioItem が配置される |
| **CI Pipeline** | `.\scripts\ci.ps1` | All 5 stages pass |

---

## Appendix: Quick Diagnostics

```bash
# Full system check
.\scripts\ci.ps1

# Python environment
.\venv\Scripts\python.exe -m pip check

# Test with coverage
.\venv\Scripts\python.exe -m pytest --cov=src --cov-report=html

# YMM4 plugin build
dotnet build ymm4-plugin/TimelinePlugin/NLMSlidePlugin.csproj -c Release
```

### Emergency Recovery
```bash
# Reset venv
Remove-Item -Recurse -Force venv
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

# Reset git state
git stash
git pull origin master
git stash pop

# Clean build artifacts
Remove-Item -Recurse -Force ymm4-plugin\bin, ymm4-plugin\obj
```

---

**Document Status**: Complete (v2.0)
**Next Review**: When new issues are identified

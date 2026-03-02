# Troubleshooting Guide

**Version**: 1.0
**Last Updated**: 2026-03-02
**Project**: NLMandSlideVideoGenerator

---

## Quick Navigation

- [Audio Issues](#audio-issues)
- [YMM4 Plugin Issues](#ymm4-plugin-issues)
- [Video Generation Issues](#video-generation-issues)
- [Environment Setup Issues](#environment-setup-issues)
- [CI/CD Issues](#cicd-issues)

---

## Audio Issues

### 🔴 Problem: No audio output device detected

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
| **Reinstall Audio Drivers** | 1. Uninstall audio driver from Device Manager<br>2. Restart computer<br>3. Windows will auto-install driver | Persistent detection issues |
| **Check FFMPEG** | 1. Verify ffmpeg is in PATH<br>2. Run `ffmpeg -version`<br>3. Set `FFMPEG_EXE` environment variable if needed | ffmpeg not found |

**Expected Output:**
```
Audio Environment Diagnostic Report
====================================
Platform: Windows
Default Device: Realtek High Definition Audio [DEFAULT]
ffmpeg Available: ✅ Yes
Audio Playback Test: ✅ Passed
```

---

### 🟡 Problem: SofTalk/TTS audio generation fails

**Symptoms:**
- `tts_batch_softalk_aquestalk.py` exits with errors
- Generated audio files are missing or corrupt
- Error: "SofTalk executable not found"

**Diagnosis:**
```bash
# Check SofTalk installation
$env:SOFTALK_EXE
Get-Command SofTalk.exe

# Test audio generation (dry-run)
python scripts/tts_batch_softalk_aquestalk.py --engine softalk --csv samples/basic_dialogue/timeline.csv --out-dir samples/audio --dry-run
```

**Solutions:**

| Solution | Steps | When to Use |
|----------|-------|-------------|
| **Install SofTalk** | 1. Download from [SofTalk website](https://w.atwiki.jp/softalk/)<br>2. Extract to `C:\Program Files\SofTalk\`<br>3. Set `SOFTALK_EXE` env var | SofTalk not installed |
| **Set Environment Variable** | 1. Open System Properties → Environment Variables<br>2. Add `SOFTALK_EXE` = `C:\Path\To\SofTalk.exe`<br>3. Restart terminal | SofTalk installed but not detected |
| **Check CSV Format** | 1. Verify CSV has "Speaker" and "Text" columns<br>2. Ensure UTF-8 encoding<br>3. Remove empty lines | CSV parsing errors |
| **Use Alternative TTS** | 1. Consider VOICEVOX (better quality)<br>2. See [SofTalk Assessment](technical/SOFTALK_INTEGRATION_ASSESSMENT.md) | Quality/compatibility issues |

**Alternative Solution (VOICEVOX):**
```bash
# Install VOICEVOX via Docker
docker pull voicevox/voicevox_engine:cpu-ubuntu20.04-latest
docker run -d -p 50021:50021 voicevox/voicevox_engine:cpu-ubuntu20.04-latest

# Use VOICEVOX API (future implementation)
python scripts/tts_batch_voicevox.py --csv timeline.csv --out-dir audio
```

---

## YMM4 Plugin Issues

### 🔴 Problem: YMM4 Plugin not appearing in plugin list

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
| **Check .NET Version** | 1. Verify .NET 9 is installed<br>2. Run `dotnet --list-runtimes`<br>3. Install .NET 9 SDK if missing | .NET runtime missing |
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

### 🟡 Problem: CSV Import Dialog freezes or crashes

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

**Performance Expectations:**
- **100 rows**: ~5 seconds
- **500 rows**: ~20 seconds
- **1000 rows**: ~30 seconds (DoD target)

---

## Video Generation Issues

### 🔴 Problem: Video generation fails with MoviePy errors

**Symptoms:**
- `run_csv_pipeline.py` crashes during video composition
- Error: "ffmpeg not found"
- Error: "Codec not supported"

**Diagnosis:**
```bash
# Check ffmpeg installation
ffmpeg -version

# Test basic video composition
python -c "from moviepy.editor import *; clip = ColorClip(size=(1280, 720), color=(255, 0, 0), duration=1); clip.write_videofile('test.mp4', fps=30)"
```

**Solutions:**

| Solution | Steps | When to Use |
|----------|-------|-------------|
| **Install ffmpeg** | 1. Download ffmpeg from [official site](https://ffmpeg.org/download.html)<br>2. Extract to `C:\ffmpeg\`<br>3. Add `C:\ffmpeg\bin` to PATH<br>4. Restart terminal | ffmpeg not found |
| **Update MoviePy** | 1. Run `pip install --upgrade moviepy`<br>2. Verify version: `pip show moviepy` | Old MoviePy version |
| **Check Codec** | 1. Use libx264 codec (default)<br>2. Add `codec='libx264'` to write_videofile()<br>3. Verify ffmpeg supports codec: `ffmpeg -codecs \| grep 264` | Codec errors |
| **Reduce Video Resolution** | 1. Set resolution to 720p instead of 1080p<br>2. Update `video_config.yaml`<br>3. Reduces memory usage | Out of memory errors |

**Codec Compatibility Matrix:**
| Codec | Support | Quality | Speed | Recommendation |
|-------|---------|---------|-------|----------------|
| libx264 | ✅ Universal | High | Medium | **Recommended** |
| h264_nvenc | ⚠️ NVIDIA GPU | High | Fast | If NVIDIA GPU available |
| libx265 | ✅ Universal | Very High | Slow | For archival quality |
| mpeg4 | ✅ Universal | Medium | Fast | For quick previews |

---

### 🟡 Problem: Subtitles not appearing in video

**Symptoms:**
- Video plays but subtitles missing
- Subtitle timing incorrect
- Text encoding issues (garbled characters)

**Diagnosis:**
```bash
# Verify subtitle generation
python scripts/run_csv_pipeline.py --csv samples/basic_dialogue/timeline.csv --slides samples/slides --audio samples/audio --output output/test.mp4 --generate-srt

# Check SRT file
cat output/test.srt
```

**Solutions:**

| Solution | Steps | When to Use |
|----------|-------|-------------|
| **Check CSV Encoding** | 1. Open CSV in Notepad<br>2. Save As → Encoding: UTF-8<br>3. Regenerate subtitles | Garbled Japanese text |
| **Verify Subtitle Settings** | 1. Check `SUBTITLE_SETTINGS` in `video_composer.py`<br>2. Ensure `add_subtitles=True` in pipeline config<br>3. Verify font supports Japanese (MS Gothic) | Subtitles not enabled |
| **Adjust Timing** | 1. Check audio file durations<br>2. Verify CSV timeline has correct timestamps<br>3. Use `duration` column in CSV | Subtitle timing off |
| **Check Font Installation** | 1. Verify font exists: `C:\Windows\Fonts\msgothic.ttc`<br>2. Install missing fonts<br>3. Update `fontsize` if text too small | Font errors |

**Subtitle Configuration Example:**
```python
SUBTITLE_SETTINGS = {
    "fontsize": 48,
    "font": "MS-Gothic",
    "color": "white",
    "stroke_color": "black",
    "stroke_width": 2,
    "method": "caption",
    "align": "South",
}
```

---

## Environment Setup Issues

### 🔴 Problem: Python venv activation fails

**Symptoms:**
- `venv\Scripts\activate` doesn't work
- ImportError: No module named 'moviepy'
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
Python 3.11.0
moviepy==1.0.3
pillow>=9.0.0
pandas>=1.5.0
```

---

### 🟡 Problem: Git merge conflicts

**Symptoms:**
- `git pull` fails with conflicts
- Merge conflict markers in files
- Build artifacts causing conflicts

**Diagnosis:**
```bash
# Check conflict status
git status

# See conflicting files
git diff --name-only --diff-filter=U
```

**Solutions:**

| Solution | Steps | When to Use |
|----------|-------|-------------|
| **Resolve Conflicts** | 1. Edit conflicting files<br>2. Remove `<<<<`, `====`, `>>>>` markers<br>3. `git add <file>`<br>4. `git commit` | Code conflicts |
| **Accept Remote Changes** | 1. `git checkout --theirs <file>`<br>2. `git add <file>`<br>3. `git commit` | Always use remote version |
| **Accept Local Changes** | 1. `git checkout --ours <file>`<br>2. `git add <file>`<br>3. `git commit` | Always use local version |
| **Ignore Build Artifacts** | 1. Add to `.gitignore`<br>2. `git rm --cached <file>`<br>3. `git commit` | Build files conflicting |

**Common Conflict Files:**
```
ymm4-plugin/obj/Debug/...
ymm4-plugin/bin/Release/...
logs/
*.log
```

---

## CI/CD Issues

### 🔴 Problem: CI pipeline fails with orchestrator-audit warnings

**Symptoms:**
- `orchestrator-audit.js` reports errors
- GitHub Actions workflow fails
- Report integrity issues

**Diagnosis:**
```bash
# Run audit locally
node .shared-workflows/scripts/orchestrator-audit.js

# Run full CI pipeline
.\scripts\ci.ps1
```

**Solutions:**

| Solution | Steps | When to Use |
|----------|-------|-------------|
| **Fix Report Links** | 1. Ensure all task files reference existing reports<br>2. Update `Report:` field in task markdown<br>3. Create missing report files | Report link errors |
| **Update Task Status** | 1. Change `Status:` field in task markdown<br>2. Ensure status is valid (OPEN/IN_PROGRESS/DONE/CLOSED)<br>3. Run audit again | Status validation errors |
| **Check File Encoding** | 1. Verify all markdown files are UTF-8<br>2. Use UTF-8 BOM for Windows compatibility<br>3. Re-save files with correct encoding | Encoding errors |
| **Run sw-doctor** | 1. `node .shared-workflows/scripts/sw-doctor.js`<br>2. Follow recommendations<br>3. Fix environment issues | Environment validation fails |

**Expected Audit Output:**
```
Orchestrator Audit Results
- tasks: 18
- reports: 5

OK
```

---

### 🟡 Problem: pytest tests fail

**Symptoms:**
- `pytest` reports test failures
- Tests pass locally but fail in CI
- Import errors in tests

**Diagnosis:**
```bash
# Run tests with verbose output
.\venv\Scripts\python.exe -m pytest -v

# Run specific test
.\venv\Scripts\python.exe -m pytest tests/test_video_composer.py::test_create_clip -v

# Check test coverage
.\venv\Scripts\python.exe -m pytest --cov=src --cov-report=html
```

**Solutions:**

| Solution | Steps | When to Use |
|----------|-------|-------------|
| **Update Test Data** | 1. Check if test fixtures exist<br>2. Regenerate test data if needed<br>3. Update test expectations | Test data outdated |
| **Fix Import Paths** | 1. Ensure `src` is in PYTHONPATH<br>2. Use relative imports in tests<br>3. Add `__init__.py` to test directories | Import errors |
| **Skip Slow Tests** | 1. Mark tests with `@pytest.mark.slow`<br>2. Run `pytest -m "not slow"`<br>3. Run slow tests separately | CI timeout |
| **Mock External Dependencies** | 1. Use `unittest.mock` for external calls<br>2. Mock ffmpeg, YMM4, etc.<br>3. Ensure tests are isolated | Integration tests failing |

**Test Markers:**
```python
@pytest.mark.slow  # Skip in CI
@pytest.mark.integration  # Requires external tools
@pytest.mark.unit  # Fast unit tests
```

---

## General Debugging Tips

### 📊 Enable Verbose Logging

```python
# In Python scripts
import logging
logging.basicConfig(level=logging.DEBUG)

# In PowerShell scripts
$VerbosePreference = "Continue"
```

### 🔍 Check System Requirements

| Component | Requirement | Check Command |
|-----------|------------|---------------|
| Python | 3.11+ | `python --version` |
| .NET | 9.0 | `dotnet --list-runtimes` |
| ffmpeg | Latest | `ffmpeg -version` |
| YMM4 | 4.33+ | Check app version |
| Git | 2.30+ | `git --version` |

### 📞 Getting Help

1. **Check Logs:**
   - Python: `logs/`
   - YMM4 Plugin: `%LOCALAPPDATA%\NLMSlidePlugin\logs\`
   - CI: `.github/workflows/` output

2. **Search Issues:**
   - Check [GitHub Issues](https://github.com/anthropics/claude-code/issues)
   - Search project documentation

3. **Ask Questions:**
   - Provide error message
   - Include system info (OS, Python version, etc.)
   - Share relevant log excerpts

---

## Manual Testing Checklist

When you need to perform manual verification, use this checklist:

| Test | Steps | Expected Result | Status |
|------|-------|-----------------|--------|
| **Audio Diagnostics** | Run `python scripts/test_audio_output.py` | ✅ All checks pass, no warnings | ⬜ |
| **YMM4 Plugin Load** | 1. Deploy plugin<br>2. Open YMM4<br>3. Check Tools menu | Plugin appears in menu | ⬜ |
| **CSV Import** | 1. Open CSV Import Dialog<br>2. Select test CSV<br>3. Click Preview<br>4. Click Import | Items appear on timeline | ⬜ |
| **Video Generation** | Run `python scripts/run_csv_pipeline.py` with sample data | Video generated successfully | ⬜ |
| **Subtitle Display** | Play generated video | Subtitles visible and synchronized | ⬜ |
| **CI Pipeline** | Run `.\scripts\ci.ps1` | All checks pass | ⬜ |

**How to Use This Checklist:**
1. Copy checklist to a new file
2. Mark ✅ for passed tests
3. Mark ❌ for failed tests
4. Document failures in issue tracker

---

## Appendix: Useful Commands

### Quick Diagnostics
```bash
# Full system check
.\scripts\ci.ps1

# Audio only
python scripts/test_audio_output.py -json

# YMM4 plugin check
.\scripts\test_task007_scenariob.ps1 -SkipBuild

# Python environment
.\venv\Scripts\python.exe -m pip check
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

### Performance Profiling
```python
# Profile Python script
python -m cProfile -o output.prof scripts/run_csv_pipeline.py
python -m pstats output.prof

# Memory profiling
python -m memory_profiler scripts/run_csv_pipeline.py
```

---

**Document Status**: ✅ Complete
**Next Review**: When new issues are identified
**Feedback**: Report issues or improvements to this guide via GitHub Issues

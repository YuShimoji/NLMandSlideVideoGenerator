"""
Shared utility functions for UI pages
"""
import streamlit as st


def load_markdown_file(filepath):
    """Load markdown content from file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except (OSError, UnicodeError, TypeError, ValueError) as e:
        return f"Error loading file: {str(e)}"
    except Exception as e:
        return f"Error loading file: {str(e)}"


def update_progress(progress_placeholder, status_placeholder, phase, progress, message):
    """プログレス更新"""
    progress_placeholder.progress(progress / 100)
    status_placeholder.info(f"{phase}: {message}")


def _run_environment_check():
    """環境チェックを実行"""
    import subprocess
    import shutil

    results = {
        "essential": {},
        "optional": {},
    }

    # Python パッケージ
    packages = [
        ("moviepy", "MoviePy"),
        ("PIL", "Pillow"),
        ("streamlit", "Streamlit"),
    ]
    for module, name in packages:
        try:
            __import__(module)
            results["essential"][name] = (True, "インストール済み")
        except ImportError:
            results["essential"][name] = (False, "未インストール")

    # FFmpeg
    from core.utils.ffmpeg_utils import detect_ffmpeg
    ffmpeg_info = detect_ffmpeg()
    if ffmpeg_info.available:
        display = f"ffmpeg {ffmpeg_info.version}" if ffmpeg_info.version else (ffmpeg_info.path or "インストール済み")
        results["optional"]["FFmpeg"] = (True, display[:40])
    else:
        results["optional"]["FFmpeg"] = (False, "未インストール（winget install FFmpeg）")

    # pysrt
    try:
        import pysrt
        results["optional"]["pysrt"] = (True, "字幕ハードサブ可能")
    except ImportError:
        results["optional"]["pysrt"] = (False, "未インストール（pip install pysrt）")

    # AutoHotkey (Windows only)
    from core.utils.tool_detection import find_autohotkey_exe
    ahk_exe = find_autohotkey_exe()
    if ahk_exe:
        results["optional"]["AutoHotkey"] = (True, "YMM4連携可能")
    else:
        results["optional"]["AutoHotkey"] = (False, "YMM4自動操作に必要")

    return results

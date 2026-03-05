"""
FFmpegユーティリティモジュール

FFmpegの検出、バージョン確認、インストール案内を提供
"""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

from .logger import logger
from .tool_detection import find_ffmpeg_exe


@dataclass
class FFmpegInfo:
    """FFmpeg情報"""
    available: bool
    path: Optional[str] = None
    version: Optional[str] = None
    has_libx264: bool = False
    has_aac: bool = False


# インストール案内メッセージ
FFMPEG_INSTALL_GUIDE = """
================================================================================
FFmpegがインストールされていません。

動画出力を有効にするには、FFmpegをインストールしてください。

【Windows】
  方法1: winget (推奨)
    winget install FFmpeg

  方法2: Chocolatey
    choco install ffmpeg

  方法3: 手動インストール
    1. https://www.gyan.dev/ffmpeg/builds/ からダウンロード
    2. ffmpeg-release-essentials.zip を解凍
    3. bin フォルダを PATH に追加

【macOS】
  brew install ffmpeg

【Linux (Ubuntu/Debian)】
  sudo apt update && sudo apt install ffmpeg

インストール後、コマンドプロンプト/ターミナルを再起動してください。
================================================================================
"""


def detect_ffmpeg() -> FFmpegInfo:
    """
    FFmpegを検出し、情報を返す
    
    Returns:
        FFmpegInfo: FFmpegの検出結果
    """
    ffmpeg_path = shutil.which("ffmpeg")

    if not ffmpeg_path:
        detected = find_ffmpeg_exe()
        if detected:
            ffmpeg_path = str(detected)
    
    if not ffmpeg_path:
        return FFmpegInfo(available=False)
    
    # バージョン情報を取得
    version = None
    has_libx264 = False
    has_aac = False
    
    try:
        result = subprocess.run(
            [ffmpeg_path, "-version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            output = result.stdout
            # バージョン抽出
            for line in output.split("\n"):
                if line.startswith("ffmpeg version"):
                    version = line.split()[2] if len(line.split()) > 2 else "unknown"
                    break
            
            # コーデック確認
            has_libx264 = "--enable-libx264" in output or "libx264" in output
            has_aac = "--enable-aac" in output or "aac" in output
            
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
        logger.debug(f"FFmpegバージョン取得エラー: {e}")
    
    return FFmpegInfo(
        available=True,
        path=ffmpeg_path,
        version=version,
        has_libx264=has_libx264,
        has_aac=has_aac,
    )


def check_ffmpeg_with_warning() -> Tuple[bool, Optional[str]]:
    """
    FFmpegをチェックし、見つからない場合は警告を表示
    
    Returns:
        Tuple[bool, Optional[str]]: (利用可能か, FFmpegパス)
    """
    info = detect_ffmpeg()
    
    if not info.available:
        logger.warning(FFMPEG_INSTALL_GUIDE)
        return False, None
    
    logger.debug(f"FFmpeg検出: {info.path} (version: {info.version})")
    return True, info.path


def get_ffmpeg_path() -> Optional[str]:
    """
    FFmpegパスを取得（見つからない場合はNone）
    
    Returns:
        Optional[str]: FFmpegのパス
    """
    info = detect_ffmpeg()
    return info.path if info.available else None


def print_ffmpeg_status():
    """FFmpegの状態を表示（デバッグ用）"""
    info = detect_ffmpeg()
    
    if info.available:
        print(f"✅ FFmpeg: {info.path}")
        print(f"   Version: {info.version}")
        print(f"   libx264: {'✅' if info.has_libx264 else '❌'}")
        print(f"   AAC: {'✅' if info.has_aac else '❌'}")
    else:
        print("❌ FFmpegが見つかりません")
        print(FFMPEG_INSTALL_GUIDE)

"""MP4出力品質自動検証 (SP-039)

FFprobeでMP4ファイルを検証し、品質項目をチェックする。
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .logger import logger


@dataclass
class CheckItem:
    """個別検証項目の結果。"""

    name: str
    category: str  # codec, resolution, duration, audio, file, frame
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    expected: str
    actual: str
    passed: bool
    message: str = ""


@dataclass
class MP4CheckResult:
    """MP4品質検証の結果。"""

    file_path: Path
    passed: bool = True
    checks: List[CheckItem] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    @property
    def critical_failures(self) -> List[CheckItem]:
        return [c for c in self.checks if not c.passed and c.severity == "CRITICAL"]

    @property
    def warnings(self) -> List[CheckItem]:
        return [c for c in self.checks if not c.passed and c.severity != "CRITICAL"]

    def summary(self) -> str:
        total = len(self.checks)
        passed = sum(1 for c in self.checks if c.passed)
        status = "PASS" if self.passed else "FAIL"
        lines = [f"[{status}] {self.file_path.name}: {passed}/{total} checks passed"]
        for c in self.checks:
            mark = "OK" if c.passed else "NG"
            lines.append(f"  [{mark}] {c.name}: {c.actual} (expected: {c.expected})")
            if not c.passed and c.message:
                lines.append(f"        {c.message}")
        return "\n".join(lines)


def _find_ffprobe() -> Optional[str]:
    """FFprobeのパスを検出する。"""
    import shutil

    path = shutil.which("ffprobe")
    if path:
        return path

    # FFmpegと同じディレクトリにある場合
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        ffprobe_candidate = Path(ffmpeg).parent / "ffprobe.exe"
        if ffprobe_candidate.exists():
            return str(ffprobe_candidate)
        ffprobe_candidate = Path(ffmpeg).parent / "ffprobe"
        if ffprobe_candidate.exists():
            return str(ffprobe_candidate)

    return None


def _run_ffprobe(file_path: Path) -> Dict[str, Any]:
    """FFprobeでメタデータを取得する。"""
    ffprobe = _find_ffprobe()
    if not ffprobe:
        raise FileNotFoundError("FFprobe not found. Install FFmpeg to use MP4 quality checker.")

    cmd = [
        ffprobe,
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(file_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"FFprobe failed: {result.stderr}")

    data: Dict[str, Any] = json.loads(result.stdout)
    return data


def check_mp4(
    file_path: Path,
    expected_duration: Optional[float] = None,
    expected_resolution: tuple[int, int] = (1920, 1080),
) -> MP4CheckResult:
    """MP4ファイルの品質を検証する。

    Args:
        file_path: MP4ファイルパス。
        expected_duration: 期待される総再生時間 (秒)。Noneの場合スキップ。
        expected_resolution: 期待される解像度 (width, height)。

    Returns:
        MP4CheckResult。
    """
    result = MP4CheckResult(file_path=file_path)

    # ファイル存在確認
    if not file_path.exists():
        result.passed = False
        result.error = f"File not found: {file_path}"
        return result

    # ファイルサイズチェック
    file_size = file_path.stat().st_size
    result.checks.append(CheckItem(
        name="file_size_min",
        category="file",
        severity="CRITICAL",
        expected="> 1MB",
        actual=f"{file_size / 1024 / 1024:.1f}MB",
        passed=file_size > 1_000_000,
        message="File too small — may be empty or corrupt" if file_size <= 1_000_000 else "",
    ))

    result.checks.append(CheckItem(
        name="file_size_max",
        category="file",
        severity="LOW",
        expected="< 256GB",
        actual=f"{file_size / 1024 / 1024 / 1024:.1f}GB",
        passed=file_size < 256 * 1024 * 1024 * 1024,
        message="Exceeds YouTube upload limit" if file_size >= 256 * 1024 * 1024 * 1024 else "",
    ))

    # FFprobe実行
    try:
        probe_data = _run_ffprobe(file_path)
    except (FileNotFoundError, RuntimeError, subprocess.TimeoutExpired, json.JSONDecodeError) as e:
        result.passed = False
        result.error = str(e)
        logger.warning(f"FFprobe failed for {file_path}: {e}")
        return result

    result.metadata = probe_data

    # ストリーム解析
    streams = probe_data.get("streams", [])
    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]

    # 映像コーデック
    if video_streams:
        vcodec = video_streams[0].get("codec_name", "unknown")
        result.checks.append(CheckItem(
            name="video_codec",
            category="codec",
            severity="CRITICAL",
            expected="h264 or hevc",
            actual=vcodec,
            passed=vcodec in ("h264", "hevc"),
        ))

        # 解像度
        width = int(video_streams[0].get("width", 0))
        height = int(video_streams[0].get("height", 0))
        exp_w, exp_h = expected_resolution
        result.checks.append(CheckItem(
            name="resolution",
            category="resolution",
            severity="CRITICAL",
            expected=f"{exp_w}x{exp_h}",
            actual=f"{width}x{height}",
            passed=(width == exp_w and height == exp_h),
        ))

        # アスペクト比
        if height > 0:
            ratio = width / height
            is_16_9 = abs(ratio - 16 / 9) < 0.05
            result.checks.append(CheckItem(
                name="aspect_ratio",
                category="resolution",
                severity="CRITICAL",
                expected="16:9",
                actual=f"{ratio:.3f}",
                passed=is_16_9,
            ))

        # FPS
        fps_str = video_streams[0].get("r_frame_rate", "0/1")
        try:
            num, den = fps_str.split("/")
            fps = float(num) / float(den) if float(den) > 0 else 0
        except (ValueError, ZeroDivisionError):
            fps = 0
        result.checks.append(CheckItem(
            name="fps",
            category="frame",
            severity="MEDIUM",
            expected="30 or 60",
            actual=f"{fps:.1f}",
            passed=abs(fps - 30) < 1 or abs(fps - 60) < 1,
        ))
    else:
        result.checks.append(CheckItem(
            name="video_stream",
            category="codec",
            severity="CRITICAL",
            expected="1 video stream",
            actual="0",
            passed=False,
            message="No video stream found",
        ))

    # 音声ストリーム
    result.checks.append(CheckItem(
        name="audio_stream_count",
        category="audio",
        severity="CRITICAL",
        expected=">= 1",
        actual=str(len(audio_streams)),
        passed=len(audio_streams) >= 1,
        message="No audio stream found" if not audio_streams else "",
    ))

    if audio_streams:
        acodec = audio_streams[0].get("codec_name", "unknown")
        result.checks.append(CheckItem(
            name="audio_codec",
            category="codec",
            severity="CRITICAL",
            expected="aac",
            actual=acodec,
            passed=acodec == "aac",
        ))

        sample_rate = int(audio_streams[0].get("sample_rate", 0))
        result.checks.append(CheckItem(
            name="sample_rate",
            category="audio",
            severity="MEDIUM",
            expected="44100 or 48000",
            actual=str(sample_rate),
            passed=sample_rate in (44100, 48000),
        ))

    # 総再生時間
    format_data = probe_data.get("format", {})
    duration = float(format_data.get("duration", 0))
    if expected_duration and expected_duration > 0:
        tolerance = expected_duration * 0.1  # ±10%
        duration_ok = abs(duration - expected_duration) <= tolerance
        result.checks.append(CheckItem(
            name="duration",
            category="duration",
            severity="HIGH",
            expected=f"{expected_duration:.0f}s (±10%)",
            actual=f"{duration:.1f}s",
            passed=duration_ok,
            message=f"Duration mismatch: diff={abs(duration - expected_duration):.1f}s" if not duration_ok else "",
        ))
    elif duration > 0:
        result.checks.append(CheckItem(
            name="duration",
            category="duration",
            severity="HIGH",
            expected="(no reference)",
            actual=f"{duration:.1f}s",
            passed=True,
        ))

    # 総合判定
    result.passed = not any(
        not c.passed and c.severity == "CRITICAL" for c in result.checks
    )

    logger.info(f"MP4 check: {file_path.name} — {'PASS' if result.passed else 'FAIL'}")
    return result

"""FFmpegユーティリティ テスト"""
from unittest.mock import patch, MagicMock
from pathlib import Path

from core.utils.ffmpeg_utils import (
    FFmpegInfo,
    detect_ffmpeg,
    check_ffmpeg_with_warning,
    get_ffmpeg_path,
    FFMPEG_INSTALL_GUIDE,
)


class TestFFmpegInfo:
    def test_creation_unavailable(self):
        info = FFmpegInfo(available=False)
        assert info.available is False
        assert info.path is None
        assert info.version is None
        assert info.has_libx264 is False
        assert info.has_aac is False

    def test_creation_available(self):
        info = FFmpegInfo(
            available=True,
            path="/usr/bin/ffmpeg",
            version="6.0",
            has_libx264=True,
            has_aac=True,
        )
        assert info.available is True
        assert info.path == "/usr/bin/ffmpeg"
        assert info.version == "6.0"


class TestDetectFfmpeg:
    @patch("core.utils.ffmpeg_utils.find_ffmpeg_exe", return_value=None)
    @patch("shutil.which", return_value=None)
    def test_not_found(self, mock_which, mock_find):
        info = detect_ffmpeg()
        assert info.available is False
        assert info.path is None

    @patch("core.utils.ffmpeg_utils.find_ffmpeg_exe", return_value=None)
    @patch("shutil.which", return_value="/usr/bin/ffmpeg")
    @patch("subprocess.run")
    def test_found_via_which(self, mock_run, mock_which, mock_find):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="ffmpeg version 6.0 Copyright (c) 2000-2023\n--enable-libx264 --enable-aac",
        )
        info = detect_ffmpeg()
        assert info.available is True
        assert info.path == "/usr/bin/ffmpeg"
        assert info.version == "6.0"
        assert info.has_libx264 is True
        assert info.has_aac is True

    @patch("core.utils.ffmpeg_utils.find_ffmpeg_exe", return_value=Path("C:/tools/ffmpeg.exe"))
    @patch("shutil.which", return_value=None)
    @patch("subprocess.run")
    def test_found_via_tool_detection(self, mock_run, mock_which, mock_find):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="ffmpeg version 5.1.2\n",
        )
        info = detect_ffmpeg()
        assert info.available is True
        assert info.version == "5.1.2"

    @patch("core.utils.ffmpeg_utils.find_ffmpeg_exe", return_value=None)
    @patch("shutil.which", return_value="/usr/bin/ffmpeg")
    @patch("subprocess.run", side_effect=FileNotFoundError("not found"))
    def test_version_check_fails(self, mock_run, mock_which, mock_find):
        info = detect_ffmpeg()
        assert info.available is True
        assert info.version is None

    @patch("core.utils.ffmpeg_utils.find_ffmpeg_exe", return_value=None)
    @patch("shutil.which", return_value="/usr/bin/ffmpeg")
    @patch("subprocess.run")
    def test_no_codecs(self, mock_run, mock_which, mock_find):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="ffmpeg version 6.0\nbasic build",
        )
        info = detect_ffmpeg()
        assert info.has_libx264 is False
        assert info.has_aac is False

    @patch("core.utils.ffmpeg_utils.find_ffmpeg_exe", return_value=None)
    @patch("shutil.which", return_value="/usr/bin/ffmpeg")
    @patch("subprocess.run")
    def test_nonzero_returncode(self, mock_run, mock_which, mock_find):
        mock_run.return_value = MagicMock(returncode=1, stdout="error")
        info = detect_ffmpeg()
        assert info.available is True
        assert info.version is None


class TestCheckFfmpegWithWarning:
    @patch("core.utils.ffmpeg_utils.detect_ffmpeg")
    def test_available(self, mock_detect):
        mock_detect.return_value = FFmpegInfo(
            available=True, path="/usr/bin/ffmpeg", version="6.0"
        )
        ok, path = check_ffmpeg_with_warning()
        assert ok is True
        assert path == "/usr/bin/ffmpeg"

    @patch("core.utils.ffmpeg_utils.detect_ffmpeg")
    def test_not_available(self, mock_detect):
        mock_detect.return_value = FFmpegInfo(available=False)
        ok, path = check_ffmpeg_with_warning()
        assert ok is False
        assert path is None


class TestGetFfmpegPath:
    @patch("core.utils.ffmpeg_utils.detect_ffmpeg")
    def test_available(self, mock_detect):
        mock_detect.return_value = FFmpegInfo(
            available=True, path="/usr/bin/ffmpeg"
        )
        assert get_ffmpeg_path() == "/usr/bin/ffmpeg"

    @patch("core.utils.ffmpeg_utils.detect_ffmpeg")
    def test_not_available(self, mock_detect):
        mock_detect.return_value = FFmpegInfo(available=False)
        assert get_ffmpeg_path() is None


class TestInstallGuide:
    def test_guide_contains_platform_info(self):
        assert "Windows" in FFMPEG_INSTALL_GUIDE
        assert "macOS" in FFMPEG_INSTALL_GUIDE
        assert "Linux" in FFMPEG_INSTALL_GUIDE

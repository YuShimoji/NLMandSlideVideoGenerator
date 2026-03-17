"""MP4品質チェッカーテスト (SP-039)"""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from core.utils.mp4_checker import (
    CheckItem,
    MP4CheckResult,
    check_mp4,
    _find_ffprobe,
)


class TestCheckItem:
    def test_defaults(self):
        item = CheckItem(
            name="test", category="codec", severity="CRITICAL",
            expected="h264", actual="h264", passed=True,
        )
        assert item.passed
        assert item.message == ""


class TestMP4CheckResult:
    def test_passed_result(self):
        result = MP4CheckResult(file_path=Path("test.mp4"))
        result.checks = [
            CheckItem("a", "codec", "CRITICAL", "h264", "h264", True),
            CheckItem("b", "audio", "MEDIUM", "44100", "48000", False),
        ]
        assert result.critical_failures == []
        assert len(result.warnings) == 1

    def test_failed_result(self):
        result = MP4CheckResult(file_path=Path("test.mp4"), passed=False)
        result.checks = [
            CheckItem("a", "codec", "CRITICAL", "h264", "vp9", False, "wrong codec"),
        ]
        assert len(result.critical_failures) == 1

    def test_summary_pass(self):
        result = MP4CheckResult(file_path=Path("ok.mp4"))
        result.checks = [
            CheckItem("a", "codec", "CRITICAL", "h264", "h264", True),
        ]
        summary = result.summary()
        assert "[PASS]" in summary
        assert "ok.mp4" in summary
        assert "[OK]" in summary

    def test_summary_fail(self):
        result = MP4CheckResult(file_path=Path("bad.mp4"), passed=False)
        result.checks = [
            CheckItem("a", "codec", "CRITICAL", "h264", "vp9", False, "wrong codec"),
        ]
        summary = result.summary()
        assert "[FAIL]" in summary
        assert "[NG]" in summary
        assert "wrong codec" in summary


class TestFindFfprobe:
    @patch("shutil.which", return_value="/usr/bin/ffprobe")
    def test_found_in_path(self, mock_which):
        assert _find_ffprobe() == "/usr/bin/ffprobe"

    @patch("shutil.which", return_value=None)
    def test_not_found(self, mock_which):
        assert _find_ffprobe() is None


class TestCheckMp4:
    def test_file_not_found(self, tmp_path: Path):
        result = check_mp4(tmp_path / "nonexistent.mp4")
        assert not result.passed
        assert result.error is not None
        assert "not found" in result.error

    def test_file_too_small(self, tmp_path: Path):
        small_file = tmp_path / "tiny.mp4"
        small_file.write_bytes(b"x" * 100)

        # FFprobeをモックしてエラーを返す
        with patch("core.utils.mp4_checker._run_ffprobe", side_effect=RuntimeError("not a valid mp4")):
            result = check_mp4(small_file)

        # ファイルサイズチェックは実行されるがFFprobeで失敗
        assert not result.passed
        assert any(c.name == "file_size_min" and not c.passed for c in result.checks)

    def test_valid_mp4_all_pass(self, tmp_path: Path):
        """正常なMP4のモックテスト。"""
        mp4_file = tmp_path / "good.mp4"
        mp4_file.write_bytes(b"x" * 2_000_000)  # 2MB

        probe_data = {
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1920,
                    "height": 1080,
                    "r_frame_rate": "30/1",
                },
                {
                    "codec_type": "audio",
                    "codec_name": "aac",
                    "sample_rate": "48000",
                },
            ],
            "format": {
                "duration": "300.5",
            },
        }

        with patch("core.utils.mp4_checker._run_ffprobe", return_value=probe_data):
            result = check_mp4(mp4_file)

        assert result.passed
        assert all(c.passed for c in result.checks if c.severity == "CRITICAL")

    def test_wrong_codec(self, tmp_path: Path):
        """不正なコーデック検出。"""
        mp4_file = tmp_path / "bad_codec.mp4"
        mp4_file.write_bytes(b"x" * 2_000_000)

        probe_data = {
            "streams": [
                {"codec_type": "video", "codec_name": "vp9", "width": 1920, "height": 1080, "r_frame_rate": "30/1"},
                {"codec_type": "audio", "codec_name": "opus", "sample_rate": "48000"},
            ],
            "format": {"duration": "60"},
        }

        with patch("core.utils.mp4_checker._run_ffprobe", return_value=probe_data):
            result = check_mp4(mp4_file)

        assert not result.passed
        assert any(c.name == "video_codec" and not c.passed for c in result.checks)
        assert any(c.name == "audio_codec" and not c.passed for c in result.checks)

    def test_no_video_stream(self, tmp_path: Path):
        """映像ストリームがない場合。"""
        mp4_file = tmp_path / "audio_only.mp4"
        mp4_file.write_bytes(b"x" * 2_000_000)

        probe_data = {
            "streams": [
                {"codec_type": "audio", "codec_name": "aac", "sample_rate": "48000"},
            ],
            "format": {"duration": "60"},
        }

        with patch("core.utils.mp4_checker._run_ffprobe", return_value=probe_data):
            result = check_mp4(mp4_file)

        assert not result.passed
        assert any(c.name == "video_stream" and not c.passed for c in result.checks)

    def test_no_audio_stream(self, tmp_path: Path):
        """音声ストリームがない場合。"""
        mp4_file = tmp_path / "video_only.mp4"
        mp4_file.write_bytes(b"x" * 2_000_000)

        probe_data = {
            "streams": [
                {"codec_type": "video", "codec_name": "h264", "width": 1920, "height": 1080, "r_frame_rate": "30/1"},
            ],
            "format": {"duration": "60"},
        }

        with patch("core.utils.mp4_checker._run_ffprobe", return_value=probe_data):
            result = check_mp4(mp4_file)

        assert not result.passed
        assert any(c.name == "audio_stream_count" and not c.passed for c in result.checks)

    def test_duration_mismatch(self, tmp_path: Path):
        """再生時間が期待値と大きく異なる場合。"""
        mp4_file = tmp_path / "wrong_dur.mp4"
        mp4_file.write_bytes(b"x" * 2_000_000)

        probe_data = {
            "streams": [
                {"codec_type": "video", "codec_name": "h264", "width": 1920, "height": 1080, "r_frame_rate": "60/1"},
                {"codec_type": "audio", "codec_name": "aac", "sample_rate": "44100"},
            ],
            "format": {"duration": "120"},
        }

        with patch("core.utils.mp4_checker._run_ffprobe", return_value=probe_data):
            result = check_mp4(mp4_file, expected_duration=300)

        # duration は HIGH severity (not CRITICAL) なので passed=True になるが警告
        assert any(c.name == "duration" and not c.passed for c in result.checks)

    def test_wrong_resolution(self, tmp_path: Path):
        """解像度が期待値と異なる場合。"""
        mp4_file = tmp_path / "low_res.mp4"
        mp4_file.write_bytes(b"x" * 2_000_000)

        probe_data = {
            "streams": [
                {"codec_type": "video", "codec_name": "h264", "width": 1280, "height": 720, "r_frame_rate": "30/1"},
                {"codec_type": "audio", "codec_name": "aac", "sample_rate": "48000"},
            ],
            "format": {"duration": "60"},
        }

        with patch("core.utils.mp4_checker._run_ffprobe", return_value=probe_data):
            result = check_mp4(mp4_file)

        assert not result.passed
        assert any(c.name == "resolution" and not c.passed for c in result.checks)

    def test_ffprobe_failure(self, tmp_path: Path):
        """FFprobeが失敗する場合。"""
        mp4_file = tmp_path / "corrupt.mp4"
        mp4_file.write_bytes(b"x" * 2_000_000)

        with patch("core.utils.mp4_checker._run_ffprobe", side_effect=FileNotFoundError("no ffprobe")):
            result = check_mp4(mp4_file)

        assert not result.passed
        assert "ffprobe" in result.error.lower()

    def test_hevc_codec_accepted(self, tmp_path: Path):
        """H.265 (HEVC) も受け入れる。"""
        mp4_file = tmp_path / "hevc.mp4"
        mp4_file.write_bytes(b"x" * 2_000_000)

        probe_data = {
            "streams": [
                {"codec_type": "video", "codec_name": "hevc", "width": 1920, "height": 1080, "r_frame_rate": "30/1"},
                {"codec_type": "audio", "codec_name": "aac", "sample_rate": "48000"},
            ],
            "format": {"duration": "60"},
        }

        with patch("core.utils.mp4_checker._run_ffprobe", return_value=probe_data):
            result = check_mp4(mp4_file)

        assert result.passed
        assert any(c.name == "video_codec" and c.passed for c in result.checks)

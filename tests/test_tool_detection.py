"""ツール検出テスト"""
import os
from pathlib import Path
from unittest.mock import patch

from core.utils.tool_detection import (
    _get_program_files_dirs,
    _program_files_candidates,
    find_executable,
    find_autohotkey_exe,
    find_ffmpeg_exe,
    find_ymm4_exe,
)


class TestGetProgramFilesDirs:
    def test_returns_list(self):
        result = _get_program_files_dirs()
        assert isinstance(result, list)

    def test_deduplicates(self):
        with patch.dict(os.environ, {
            "ProgramW6432": "C:\\Program Files",
            "ProgramFiles": "C:\\Program Files",
            "ProgramFiles(x86)": "C:\\Program Files (x86)",
        }):
            result = _get_program_files_dirs()
            # No duplicates
            assert len(result) == len(set(result))


class TestProgramFilesCandidates:
    def test_generates_candidates(self):
        with patch("core.utils.tool_detection._get_program_files_dirs", return_value=[Path("C:/PF")]):
            result = _program_files_candidates(["app/app.exe", "app2/app2.exe"])
            assert Path("C:/PF/app/app.exe") in result
            assert Path("C:/PF/app2/app2.exe") in result
            assert len(result) == 2

    def test_empty_dirs(self):
        with patch("core.utils.tool_detection._get_program_files_dirs", return_value=[]):
            result = _program_files_candidates(["app/app.exe"])
            assert result == []


class TestFindExecutable:
    def test_env_var_takes_priority(self, tmp_path):
        exe = tmp_path / "test.exe"
        exe.write_text("fake")
        with patch.dict(os.environ, {"TEST_EXE": str(exe)}):
            result = find_executable([], "TEST_EXE", [])
            assert result == exe

    def test_env_var_missing_file_ignored(self):
        with patch.dict(os.environ, {"TEST_EXE": "/nonexistent/path.exe"}):
            result = find_executable([], "TEST_EXE", [])
            assert result is None

    def test_which_fallback(self, tmp_path):
        exe = tmp_path / "found.exe"
        exe.write_text("fake")
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("TEST_EXE", None)
            with patch("shutil.which", return_value=str(exe)):
                result = find_executable([], "TEST_EXE", ["found.exe"])
                assert result == exe

    def test_candidates_fallback(self, tmp_path):
        exe = tmp_path / "candidate.exe"
        exe.write_text("fake")
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("TEST_EXE", None)
            with patch("shutil.which", return_value=None):
                result = find_executable([exe], "TEST_EXE", [])
                assert result == exe

    def test_nothing_found(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("TEST_EXE", None)
            with patch("shutil.which", return_value=None):
                result = find_executable(
                    [Path("/nonexistent/a.exe")], "TEST_EXE", ["nonexistent"]
                )
                assert result is None


class TestFindSpecificTools:
    def test_find_autohotkey_returns_optional(self):
        result = find_autohotkey_exe()
        assert result is None or isinstance(result, Path)

    def test_find_ymm4_returns_optional(self):
        result = find_ymm4_exe()
        assert result is None or isinstance(result, Path)

    def test_find_ffmpeg_returns_optional(self):
        result = find_ffmpeg_exe()
        assert result is None or isinstance(result, Path)

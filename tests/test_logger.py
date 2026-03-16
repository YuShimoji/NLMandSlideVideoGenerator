"""SimpleLogger テスト"""
import io
import sys

from core.utils.logger import SimpleLogger, _safe_print, logger


class TestSafePrint:
    def test_normal_ascii(self, capsys):
        _safe_print("hello world")
        captured = capsys.readouterr()
        assert "hello world" in captured.out

    def test_unicode_text(self, capsys):
        _safe_print("日本語テスト")
        captured = capsys.readouterr()
        assert "日本語テスト" in captured.out

    def test_mixed_text(self, capsys):
        _safe_print("[INFO] テスト: abc 123")
        captured = capsys.readouterr()
        assert "[INFO]" in captured.out

    def test_empty_string(self, capsys):
        _safe_print("")
        captured = capsys.readouterr()
        assert captured.out.strip() == ""


class TestSimpleLogger:
    def test_info(self, capsys):
        log = SimpleLogger()
        log.info("test message")
        captured = capsys.readouterr()
        assert "[INFO] test message" in captured.out

    def test_success(self, capsys):
        log = SimpleLogger()
        log.success("done")
        captured = capsys.readouterr()
        assert "[SUCCESS] done" in captured.out

    def test_warning(self, capsys):
        log = SimpleLogger()
        log.warning("careful")
        captured = capsys.readouterr()
        assert "[WARNING] careful" in captured.out

    def test_error(self, capsys):
        log = SimpleLogger()
        log.error("fail")
        captured = capsys.readouterr()
        assert "[ERROR] fail" in captured.out

    def test_debug(self, capsys):
        log = SimpleLogger()
        log.debug("detail")
        captured = capsys.readouterr()
        assert "[DEBUG] detail" in captured.out

    def test_module_level_logger_instance(self):
        assert isinstance(logger, SimpleLogger)

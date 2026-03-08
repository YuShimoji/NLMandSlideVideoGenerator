"""
シンプルロガー
"""
import sys


def _safe_print(msg: str) -> None:
    """Encoding-safe print (handles Windows cp1252 etc.)."""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(
            sys.stdout.encoding or "utf-8", errors="replace"
        ))


class SimpleLogger:
    def info(self, msg): _safe_print(f"[INFO] {msg}")
    def success(self, msg): _safe_print(f"[SUCCESS] {msg}")
    def warning(self, msg): _safe_print(f"[WARNING] {msg}")
    def error(self, msg): _safe_print(f"[ERROR] {msg}")
    def debug(self, msg): _safe_print(f"[DEBUG] {msg}")


logger = SimpleLogger()

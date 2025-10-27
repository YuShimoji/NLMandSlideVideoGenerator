import sys
from pathlib import Path

# Add project root to path (same as web_app.py)
PROJECT_ROOT = Path(__file__).parent
SRC_PATH = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_PATH))
sys.path.insert(0, str(PROJECT_ROOT))

print(f"PROJECT_ROOT: {PROJECT_ROOT}")
print(f"SRC_PATH: {SRC_PATH}")
print(f"sys.path[:3]: {sys.path[:3]}")

try:
    from config.settings import settings
    print("Settings import: OK")
except Exception as e:
    print(f"Settings import error: {e}")

try:
    from notebook_lm.source_collector import SourceCollector
    print("Notebook_lm direct import: OK")
except Exception as e:
    print(f"Notebook_lm direct import error: {e}")

try:
    from src.core import interfaces
    print("Interfaces import: OK")
except Exception as e:
    print(f"Interfaces import error: {e}")

try:
    from src.core.pipeline import build_default_pipeline
    print("Pipeline import: OK")
except Exception as e:
    import traceback
    print(f"Pipeline import error: {e}")
    print("Traceback:")
    traceback.print_exc()

try:
    import streamlit as st
    print("Streamlit import: OK")
except Exception as e:
    print(f"Streamlit import error: {e}")

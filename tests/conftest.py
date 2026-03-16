"""Shared pytest fixtures and configuration."""

import sys
import types
from unittest.mock import MagicMock


def _ensure_google_genai_mockable() -> None:
    """Ensure google.genai module path is resolvable for unittest.mock.patch.

    When google-genai SDK is not installed, patch("google.genai.Client")
    fails with ModuleNotFoundError because mock tries to import the target.
    This injects minimal stub modules into sys.modules so that patch()
    can resolve the path without the real SDK.
    """
    if "google" not in sys.modules:
        google_pkg = types.ModuleType("google")
        google_pkg.__path__ = []  # make it a package
        sys.modules["google"] = google_pkg

    if "google.genai" not in sys.modules:
        genai_mod = types.ModuleType("google.genai")
        genai_mod.Client = MagicMock  # default, overridden by individual patches
        sys.modules["google.genai"] = genai_mod
        sys.modules["google"].genai = genai_mod  # type: ignore[attr-defined]


# Run once at import time (before any test collection)
_ensure_google_genai_mockable()

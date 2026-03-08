"""
Web UI Pages Module

This module re-exports all page functions to maintain backward compatibility.
Previously, all pages were in a single pages.py file (1,465 lines).
Now split into separate modules for better maintainability:

- home.py: Landing page and environment check
- pipeline.py: Full pipeline execution
- asset_management.py: Asset viewing and management
- settings.py: Settings display and configuration
- research.py: Research package alignment
- documentation.py: Documentation viewer
- tests.py: API tests runner
- _utils.py: Shared utility functions
"""

from .home import show_home_page
from .pipeline import show_pipeline_page
from .asset_management import show_assets_page
from .settings import show_settings_page
from .research import show_research_page
from .documentation import show_documentation_page
from .tests import show_tests_page

# Re-export utility functions for backward compatibility
from ._utils import load_markdown_file, update_progress, _run_environment_check

__all__ = [
    # Main page functions
    "show_home_page",
    "show_pipeline_page",
    "show_assets_page",
    "show_settings_page",
    "show_research_page",
    "show_documentation_page",
    "show_tests_page",
    # Utility functions
    "load_markdown_file",
    "update_progress",
    "_run_environment_check",
]

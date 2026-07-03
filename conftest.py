"""
Root conftest.py — ensures the project root and src/ are on sys.path so tests can
import from the src/ package using either the full dotted path or the short form:

    from src.ph_test.mcp_mock import MCPMock   # full path (repo root on sys.path)
    from ph_test.mcp_mock import MCPMock        # short form (src/ on sys.path)

This is needed for src-layout projects without an editable install.
Must run before pytest-cov begins instrumentation so coverage can track modules correctly.
"""

import sys
from pathlib import Path

_root = str(Path(__file__).parent)
_src = str(Path(__file__).parent / "src")

if _root not in sys.path:
    sys.path.insert(0, _root)
if _src not in sys.path:
    sys.path.insert(0, _src)

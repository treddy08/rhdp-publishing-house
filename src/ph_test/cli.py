"""
ph-test CLI entrypoint — delegates to scripts/ph-test.py logic.
Installed as `ph-test` command via pyproject.toml.
"""
import sys
import os
from pathlib import Path

# Set REPO_ROOT so ph-test finds fixtures, skills, and template relative to
# the installed package location regardless of working directory.
_PACKAGE_DIR = Path(__file__).parent          # src/ph_test/
_REPO_ROOT = _PACKAGE_DIR.parent.parent       # repo root

os.environ.setdefault("PH_TEST_REPO_ROOT", str(_REPO_ROOT))

# Delegate to the main CLI
sys.path.insert(0, str(_REPO_ROOT))

from scripts.ph_test import main  # noqa: E402 (needed after path setup)


if __name__ == "__main__":
    main()

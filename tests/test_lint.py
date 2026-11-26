import importlib.util
import os
import subprocess
import sys

import pytest

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.mark.skipif(
    importlib.util.find_spec("ruff") is None,
    reason="Ruff isn't installed (pip install -r requirements.txt)",
)
def test_ruff_finds_no_mistakes():
    # The same check as "ruff check ." (its rules are in pyproject.toml). "ruff check --fix ." fixes most of them, like unused imports.
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--output-format", "concise", "."],
        cwd=REPO_DIR,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0, result.stdout[-4000:]


@pytest.mark.skipif(
    importlib.util.find_spec("ruff") is None,
    reason="Ruff isn't installed (pip install -r requirements.txt)",
)
def test_the_code_is_formatted():
    # "ruff format ." formats it (the same as Black, which VS Code uses when saving a file).
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "format", "--check", "."],
        cwd=REPO_DIR,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0, result.stdout[-4000:]

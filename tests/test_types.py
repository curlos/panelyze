import os
import shutil
import subprocess
import sys

import pytest

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.mark.skipif(
    not shutil.which("npx"),
    reason="Pyright runs with Node's npx, which isn't installed",
)
def test_pyright_finds_no_type_errors():
    # The same check as "npx --yes pyright@1.1.414" in DEVELOPING.md (its settings are in pyproject.toml). About 12 seconds.
    result = subprocess.run(
        ["npx", "--yes", "pyright@1.1.414", "--pythonpath", sys.executable],
        cwd=REPO_DIR,
        capture_output=True,
        text=True,
        timeout=600,
    )

    # The last lines list the errors and end with "N errors, ...".
    assert result.returncode == 0, "\n".join(result.stdout.splitlines()[-40:])

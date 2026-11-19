import os
import sys

# Make the repo's root-level modules (utils.py, magi.py, etc.) importable from the tests.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tests.fake_gui import make_gui  # noqa: E402,F401 (makes the "make_gui" fixture available to every test)

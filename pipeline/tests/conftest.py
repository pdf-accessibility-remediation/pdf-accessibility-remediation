"""conftest.py: puts pipeline/ on sys.path, so the tests import the shared modules as the scripts do (from lib import X).

    cd pipeline && python -m pytest tests -q
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

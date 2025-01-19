import sys
import os
import pathlib

sys.path.insert(0, str(pathlib.Path(os.path.dirname(__file__))))


print(__name__)


def run_addon():
    if "pytest" in sys.modules:
        return

    import src


run_addon()

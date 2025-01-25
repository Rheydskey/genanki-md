import sys
import os

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), 'libs'))


def run_addon():
    if "pytest" in sys.modules:
        return

    import src  # pragma: no cover


run_addon()

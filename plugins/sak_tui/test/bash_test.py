import sys
import unittest
from pathlib import Path

TEST_PATH = Path(__file__).resolve().parent
SRC_PATH = TEST_PATH.parent

sys.path.append(str(SRC_PATH))


class BashTests(unittest.TestCase):
    def test_dummy(self) -> None:

        pass

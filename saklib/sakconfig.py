# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__version__ = "0.0.0"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

from pathlib import Path
from typing import List, Any, Optional


def find_in_parent(dirname: Path, name: Path) -> Optional[Path]:
    if (dirname / name).exists():
        return dirname / name
    if dirname.parent != Path('/'):
        return find_in_parent(dirname.parent, name)
    return None

SCRIPT_DIR = Path(__file__).parent.resolve()
CURRENT_DIR = Path('.').resolve()

SAK_GLOBAL = find_in_parent(SCRIPT_DIR, Path('.sak'))
SAK_LOCAL = find_in_parent(CURRENT_DIR, Path('.sak'))

class SakConfig(object):
    def __init__(self, path: Path) -> None:
        super(SakConfig, self).__init__()
        self.path: List[Any] = []

    def get(self, key: str) -> str:
        pass

    def set(self, key: str, value: str) -> str:
        pass

# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__version__ = "0.0.0"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

import Path
from typing import List, Any

class SakConfig(object):
    def __init__(self, path: Path) -> None:
        super(SakConfig, self).__init__()
        self.path: List[Any] = []

    def get(self, key: str) -> str:
        pass

    def set(self, key: str, value: str) -> str:
        pass

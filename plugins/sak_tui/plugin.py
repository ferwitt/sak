#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__version__ = "0.0.0"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

from sakcmd import SakCmd, SakArg
from sakplugin import SakPlugin, SakPluginManager

from typing import List, Any, Dict, Optional

import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parent
sys.path.append(str(PLUGIN_DIR))

class SakTui(SakPlugin):
    '''Text User Interface for SAK.'''

    def __init__(self, name, **kwargs) -> None:
        super(SakTui, self).__init__(name, **kwargs)
        self.lazy_import_done = False

    def lazy_import(self):
        if not self.lazy_import_done:
            from tui import SakTuiImpl
            self.saktui = SakTuiImpl(self)
            self.lazy_import_done = True

    @SakCmd(helpmsg='Start the TUI application.')
    def start(self):
        self.lazy_import()
        return self.saktui.start()


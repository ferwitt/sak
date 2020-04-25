#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__version__ = "0.0.0"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

from sakcmd import SakCmd, SakArg, SakCmdCtx, SakCmdRet
import sakplugin
from sakplugin import SakPlugin, SakPluginManager, owl

import os
import json
import io
import base64

from pathlib import Path
from typing import List, Dict, Any, Optional

import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parent
sys.path.append(str(PLUGIN_DIR))


class SakWebapp(SakPlugin):
    def __init__(self, name, **kwargs) -> None:
        super(SakWebapp, self).__init__(name, **kwargs)

    def lazy_import(self):
        if not self.lazy_import_done:
            from webapp import SakWebappImpl
            self.sakwebapp = SakWebappImpl(self)
            self.lazy_import_done = True

    def start(self, ctx: SakCmdCtx) -> SakCmdRet:
        self.lazy_import()
        return self.sakwebapp.start(ctx)

    def exportCmds(self, base: SakCmd) -> None:
        webapp = SakCmd('webapp', helpmsg='Web application for SAK.')

        start = SakCmd('start', self.start, helpmsg='Start webapp')
        start.addArg(SakArg('port', short_name='p', type=int, default=2020, helpmsg='Server port (default: 2020)'))
        webapp.addSubCmd(start)
        
        base.addSubCmd(webapp)

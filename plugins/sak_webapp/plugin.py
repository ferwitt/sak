#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

from sakcmd import SakCmd, SakArg
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
    '''Web application for SAK.'''

    def __init__(self, name, **kwargs) -> None:
        super(SakWebapp, self).__init__(name, **kwargs)
        self.lazy_import_done = False

    def lazy_import(self):
        if not self.lazy_import_done:
            from webapp import SakWebappImpl
            self.sakwebapp = SakWebappImpl(self)
            self.lazy_import_done = True

    @SakCmd('start', helpmsg='Start webapp')
    @SakArg('port', short_name='p', type=int, default=2020, helpmsg='Server port (default: 2020)')
    def start(self, **vargs):
        self.lazy_import()
        return self.sakwebapp.start(**vargs)


    @SakCmd()
    @SakArg('message', default='No message', type=str, helpmsg='Some message')
    def say_hello(self, message, **vargs):
        return 'Test say: ' +message

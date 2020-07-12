#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

from sakcmd import SakCmd, SakArg
from sakplugin import SakPlugin

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
    @SakArg('bokeh_port', short_name='b', type=int, default=5006, helpmsg='The Bokeh server port (default: 5006)')
    def start(self, **vargs):
        self.lazy_import()
        return self.sakwebapp.start(**vargs)


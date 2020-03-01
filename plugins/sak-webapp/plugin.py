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

import os

from flask import Flask, redirect


class SakWerbapp(SakPlugin):
    def __init__(self):
        super(SakWerbapp, self).__init__('webapp')

        self.app = None

    def _getApp(self):
        thisDir = os.path.dirname(os.path.abspath(__file__))
        staticDir = os.path.join(thisDir, 'web', 'static')

        if not self.app:
            self.app = Flask('sak',
                    static_url_path='',
                    static_folder=staticDir
                    )
        return self.app


    def buildFlask(self):
        app = self._getApp()

        @app.route("/")
        def index():
            return redirect("index.html")

        @app.route('/')
        def root():
            return app.send_static_file('resources/index.html')

        return app

    def appStart(self):
        pluginDirs = [p.path for p in self.context.pluginManager.getPluginList()]

        # Add all the plugin files to the watch list to restart server
        extra_files=[]
        for pDir in pluginDirs:
            if not pDir:
                continue
            extra_files.append(os.path.join(pDir, 'plugin.py'))

        return self.buildFlask().run(debug=True, extra_files=extra_files)


    def start(self, **vargs):
        self.appStart()

    def exportCmds(self, base):
        webapp = SakCmd('webapp')

        start = SakCmd('start', self.start)
        webapp.addSubCmd(start)
        
        base.addSubCmd(webapp)

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

from flask import Flask, redirect, jsonify, request

class SakWebCmdArg():
    def __init__(self, arg):
        self.arg = arg

    def getRequestArg(self, request):
        name = self.arg.name
        required = self.arg.vargs.get('required', False)
        action = self.arg.vargs.get('action', '')
        nargs = self.arg.vargs.get('nargs', '')
        default = self.arg.vargs.get('default', None)
        arg_type = self.arg.vargs.get('type', None)

        def castIt(val):
            if arg_type==None:
                return val
            return arg_type(val)

        req_arg = request.args.get(name, None)

        # TODO: Handle nargs and action append
        if 'store_true' in action:
            req_arg = req_arg != None
            return {name: req_arg}

        if action in ['append'] or nargs in ['*']:
            if req_arg == None:
                req_arg = []
            else:
                req_arg = [castIt(req_arg)]
            return {name: req_arg}

        if not req_arg:
            if required or nargs in ['+']:
                raise('Parameter %s is required' % name)
            else:
                req_arg = default
        req_arg = castIt(req_arg)
        if nargs in ['+']:
            req_arg = [req_arg]

        return {name: req_arg}

class SakWebCmd():
    def __init__(self, cmd, root):
        self.cmd = cmd
        self.root = root

        self.route = os.path.join(self.root, self.cmd.name)

        self.args = []
        for arg in cmd.args:
            self.args.append(SakWebCmdArg(arg))

        self.subcmds = []
        for subcmd in cmd.subcmds:
            self.subcmds.append(SakWebCmd(subcmd, self.route))

    def __call__(self):
        ret = {}

        if self.cmd.callback:
            vargs = {}
            for arg in self.args:
                vargs.update(arg.getRequestArg(request))

            print(vargs)

            ret['result'] = self.cmd.callback(**vargs)


        return jsonify(ret)

    def buildFlaskRoutes(self, app):
        print('register', self.route)
        app.add_url_rule(
                self.route,
                self.route.replace('/', '_'),
                self
                )

        for subcmd in self.subcmds:
            subcmd.buildFlaskRoutes(app)


class SakWebapp(SakPlugin):
    def __init__(self):
        super(SakWebapp, self).__init__('webapp')

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

        @app.route("/api/show/plugins")
        def show_plugins():
            return jsonify([x.name for x in self.context.pluginManager.getPluginList()])


        @app.route("/api/show/commands")
        def show_commands():
            return jsonify(self.context.pluginManager.generateCommandsTree().getAsDict())


        commands_root = '/api/commands'
        @app.route(commands_root)
        def commands():
            return show_commands()

        cmdTree = SakWebCmd(self.context.pluginManager.generateCommandsTree(), commands_root)
        cmdTree.buildFlaskRoutes(app)


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

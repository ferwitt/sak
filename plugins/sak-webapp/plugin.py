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

    def getAsDict(self):
        ret = {
                'name': self.arg.name.replace('-', '_'),
                'help': self.arg.helpmsg,
                }
        #ret.update(self.vargs)
        return ret

    def getRequestArg(self, request):
        name = self.arg.name.replace('-', '_')
        required = self.arg.vargs.get('required', False)
        action = self.arg.vargs.get('action', '')
        nargs = self.arg.vargs.get('nargs', '')
        default = self.arg.vargs.get('default', None)
        arg_type = self.arg.vargs.get('type', None)

        def castIt(val):
            if val == None:
                return val
            if arg_type == None:
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

        if req_arg == None:
            if default == None:
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
        if self.cmd.callback:
            ret = {}
            vargs = {}
            for arg in self.args:
                vargs.update(arg.getRequestArg(request))

            print(vargs)

            ret['result'] = self.cmd.callback(**vargs)
            return jsonify(ret)
        else:
            return self.getAsDict()

    def buildFlaskRoutes(self, app):
        if SakCmd.EXP_WEB not in self.cmd.expose:
            return

        app.add_url_rule(
                self.route,
                self.route.replace('/', '_'),
                self
                )

        for subcmd in self.subcmds:
            subcmd.buildFlaskRoutes(app)

    def getAsDict(self):
        ret = { 'name': self.cmd.name, 'helpmsg': self.cmd.helpmsg}
        ret['subcmds'] = [x.getAsDict() for x in self.subcmds if SakCmd.EXP_WEB in x.cmd.expose]
        ret['args'] = [x.getAsDict() for x in self.args]
        ret['isCallable'] = self.cmd.callback != None
        ret['path'] = self.route
        ret['parent_path'] = self.root
        return ret



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
        commands_root = '/api/cmd'

        @app.route("/")
        def index():
            return redirect("index.html")

        privatePlugins = ['sak', 'plugins']
        plugins = [x for x in self.context.pluginManager.getPluginList() if x.name not in privatePlugins]

        @app.route("/api/show/plugins")
        def show_plugins():
            return jsonify([x.name for x in plugins])

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

        # https://www.quora.com/How-is-it-possible-to-make-Flask-web-framework-non-blocking
        return self.buildFlask().run(debug=True, extra_files=extra_files, threaded=True)


    def start(self, **vargs):
        self.appStart()

    def exportCmds(self, base):
        webapp = SakCmd('webapp')

        start = SakCmd('start', self.start)
        webapp.addSubCmd(start)
        
        base.addSubCmd(webapp)

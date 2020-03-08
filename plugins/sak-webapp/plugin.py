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
        action = self.arg.vargs.get('action', '')
        default = self.arg.vargs.get('default', None)
        choices = self.arg.vargs.get('choices', None)
        arg_type = self.arg.vargs.get('type', None)
        nargs = self.arg.vargs.get('nargs', None)

        if not choices and self.arg.completercb:
            choices = self.arg.completercb()

        if arg_type is None:
            if action in ['store_true', 'store_false']:
                arg_type = bool
            if action in ['append'] or nargs in ['*', '+']:
                arg_type = list

        if default is None:
            if action == 'store_true':
                default = False
            elif action == 'store_false':
                default = True

        type_lut = {
                bool: 'bool',
                str: 'string',
                list: 'list',
                int: 'int',
                float: 'float'
                }

        ret = {
                'name': self.arg.name,
                'help': self.arg.helpmsg,
                'type': type_lut.get(arg_type, 'string'),
                'default': default,
                'choices': choices,
                'nargs': nargs,
                'action': action,
                }
        #ret.update(self.vargs)
        return ret

    def getRequestArgList(self, request):

        type_lut = {
                'bool': bool,
                'string': str,
                'list': list,
                'int': int,
                'float': float
                }
        cfg = self.getAsDict()

        name = cfg['name']
        arg_type = type_lut.get(cfg['type'], 'string')
        arg_action = cfg['action']

        req_arg = request.args.get(name, None)

        ret = []

        if req_arg is not None:

            if arg_type is bool:
                if 'store_true' == arg_action:
                    if req_arg not in ['yes', 'true', '1']:
                        return []
                if 'store_false' == arg_action:
                    if req_arg not in ['false', 'no', '0']:
                        return []

            ret.append('--%s' % name)

            if arg_type is not bool:
                if isinstance(req_arg, list):
                    ret += req_arg
                else:
                    ret.append(req_arg)

        return ret

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

            arg_list = []
            for arg in self.args:
                arg_list += arg.getRequestArgList(request)

            print(arg_list)

            p = self.cmd.generateArgParse()

            error_status = {}
            def exit(p, status=0, message=None):
                error_status['status'] = status
                error_status['message'] = message
            p.exit = exit

            try:
                args = p.parse_args(arg_list)
            except:
                pass

            ret = {'error': False}

            if error_status:
                ret['error'] = True
                ret.update(error_status)
            else:
                args = vars(args)
                print(args)

                callback = args.pop('sak_callback')

                ret['params'] = args

                if callback:
                    ret['result'] = str(callback(**args))

            print(ret)

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

    def appStart(self, port=5000):
        pluginDirs = [p.path for p in self.context.pluginManager.getPluginList()]

        # Add all the plugin files to the watch list to restart server
        extra_files = []
        for pDir in pluginDirs:
            if not pDir:
                continue
            extra_files.append(os.path.join(pDir, 'plugin.py'))

        # https://www.quora.com/How-is-it-possible-to-make-Flask-web-framework-non-blocking
        return self.buildFlask().run(debug=True, extra_files=extra_files, threaded=True, port=port)


    def start(self, **vargs):
        self.appStart(**vargs)

    def exportCmds(self, base):
        webapp = SakCmd('webapp')

        start = SakCmd('start', self.start)
        start.addArg(SakArg('port', short_name='p', type=int, default='2020'))
        webapp.addSubCmd(start)
        
        base.addSubCmd(webapp)

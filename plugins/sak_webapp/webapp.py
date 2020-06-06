#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__version__ = "0.0.0"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

from sakcmd import SakCmd, SakArg, sak_arg_parser, SakCmdWrapper
from sakplugin import SakPlugin, SakPluginManager, onto

import os
import json
import io
import base64
import inspect

from pathlib import Path

from typing import List, Dict, Any, Optional

from argparse import ArgumentParser

from flask import Flask, redirect, jsonify, request
from flask.wrappers import Request, ResponseBase

has_pandas = False
try:
    import pandas as pd
    has_pandas = True
except:
    pass

has_matplotlib = False
try:
    import matplotlib
    import matplotlib.pyplot as plt
    has_matplotlib = True
except:
    pass


class SakWebCmdArg():
    def __init__(self, arg: SakArg):
        self.arg = arg

    def getAsDict(self, request: Optional[Request] = None) -> Dict[str, Any]:
        action = self.arg.vargs.get('action', '')
        default = self.arg.vargs.get('default', None)
        choices = list(self.arg.vargs.get('choices', []))
        arg_type = self.arg.vargs.get('type', None)
        nargs = self.arg.vargs.get('nargs', None)

        # Work around for list
        if nargs is not None:
            if nargs in ['*', '+']:
                arg_type = list

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

        #TODO(witt): Should I override the default or give another value?
        request_default = None
        if request is not None:
            request_default = request.json.get(self.arg.name, None)

        ret: Dict[str, Any] = {
            'name': self.arg.name,
            'help': self.arg.helpmsg,
            'type': type_lut.get(arg_type, 'string'),
            'default': request_default or default,
            'choices': choices,
            'nargs': nargs,
            'action': action,
        }
        #ret.update(self.vargs)
        return ret

    def getRequestArgList(self, request: Request) -> List[str]:
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

        req_arg = request.json.get(name, None)

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
                    if arg_type is list:
                        ret += req_arg.split(',')
                    else:
                        ret.append(req_arg)

        return ret


class SakWebappImpl(object):
    def __init__(self, plugin) -> None:
        super(SakWebappImpl, self).__init__()
        self.plugin = plugin
        self.app: Optional[Flask] = None

    def _getApp(self) -> Flask:
        thisDir = Path(__file__).resolve().parent
        staticDir = thisDir / 'web' / 'static'

        if self.app is None:
            self.app = Flask('sak',
                             static_url_path='',
                             static_folder=str(staticDir))
        return self.app

    def buildFlask(self) -> Flask:
        app = self._getApp()

        @app.route("/")
        def index() -> ResponseBase:
            return redirect("index.html")

        root_cmd = self.plugin.context.plugin_manager.root_cmd()

        api_root = '/api/sak'

        @app.route(api_root)
        @app.route(api_root + '/')
        @app.route(api_root + '/<path:path>', methods=['GET', 'POST'])
        def cmd_api(path=''):
            web_ret = {}

            args = path.split('/')

            # Filter empty fields
            args = [x for x in args if x]

            # Get only the metadata.
            ret = sak_arg_parser(root_cmd, args + ['-h'])

            if args:
                if args[-1] != ret['cmd'].name:
                    web_ret['error'] = True
                    web_ret[
                        'error_message'] = 'Could not find the path for %s' % (
                            api_root + '/' + path)
                    return jsonify(web_ret), 500

            cmd = ret['cmd']
            webArgs = []
            for arg in cmd.args:
                webArgs.append(SakWebCmdArg(arg))

            web_ret['name'] = cmd.name
            web_ret['helpmsg'] = cmd.helpmsg

            web_ret['error'] = False
            if 'error' in ret['argparse']:
                web_ret['error'] = True
                web_ret['error_message'] = ret['error']
                return jsonify(web_ret), 500

            web_ret['subcmds'] = []
            for subcmd in cmd.subcmds:
                subcmd = SakCmdWrapper(subcmd)

                if not subcmd.name:
                    continue
                web_ret['subcmds'].append({
                    'name':
                    subcmd.name,
                    'helpmsg':
                    subcmd.helpmsg,
                    'path':
                    os.path.join(api_root, path, subcmd.name),
                    'parent_path':
                    os.path.join(api_root, path),
                    'subcmds': [],
                })

            web_ret['isCallable'] = cmd.callback is not None

            web_ret['path'] = os.path.join(api_root, path)
            web_ret['parent_path'] = os.path.dirname(web_ret['path'])
            web_ret['args'] = []
            for arg in webArgs:
                web_ret['args'].append(arg.getAsDict())

            if request.method == 'GET':
                return jsonify(web_ret)

            if request.method == 'POST':
                web_ret['args'] = []
                for arg in webArgs:
                    web_ret['args'].append(arg.getAsDict(request))

                param_args = []
                for arg in webArgs:
                    param_args += arg.getRequestArgList(request)

                post_ret = sak_arg_parser(root_cmd, args + param_args)

                web_ret['error'] = False
                if 'error' in post_ret['argparse']:
                    web_ret['error'] = True
                    web_ret['error_message'] = post_ret['error']
                    return jsonify(web_ret), 500

                web_ret['result'] = post_ret['value']

                if not web_ret['error']:
                    if has_pandas and isinstance(web_ret['result'],
                                                 pd.DataFrame):
                        if 1:
                            web_ret['type'] = 'pd.DataFrame'
                            web_ret['result'] = json.loads(
                                web_ret['result'].reset_index().to_json(
                                    orient='records', date_format='iso'))
                        else:
                            web_ret['type'] = 'html'
                            web_ret['result'] = web_ret['result'].reset_index(
                            ).to_html()
                    elif has_matplotlib and isinstance(
                            web_ret['result'], matplotlib.figure.Figure):
                        web_ret['type'] = 'png'
                        buf = io.BytesIO()
                        web_ret['result'].savefig(buf, format='png')
                        web_ret['result'] = base64.b64encode(
                            buf.getvalue()).decode()
                    else:
                        web_ret['type'] = 'string'
                        web_ret['result'] = str(web_ret['result'])

                return jsonify(web_ret)

            return jsonify(isError=True,
                           message="Method not allowed",
                           statusCode=405), 405

        return app

    def appStart(self, port: int) -> None:
        pluginDirs = [
            p.getPath()
            for p in self.plugin.context.pluginManager.getPluginList()
        ]

        ## Add all the plugin files to the watch list to restart server
        extra_files = []
        for pDir in pluginDirs:
            if not pDir:
                continue
            extra_files.append(os.path.join(pDir))
        extra_files = list(set(extra_files))

        # https://www.quora.com/How-is-it-possible-to-make-Flask-web-framework-non-blocking
        self.buildFlask().run(debug=True,
                              extra_files=extra_files,
                              threaded=True,
                              port=port)

    def start(self, port: int) -> None:
        self.appStart(port)

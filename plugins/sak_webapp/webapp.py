#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

from sak import root_cmd
from sakcmd import SakCmd, SakArg, sak_arg_parser, SakCmdWrapper, SakCompleterArg

import os
import json
import io
import base64
import inspect
import uuid

from threading import Thread

from pathlib import Path

from typing import List, Dict, Any, Optional

from argparse import ArgumentParser

from flask import Flask, redirect, jsonify, request
from flask.wrappers import Request, ResponseBase
from flask import render_template

from bokeh.server.server import Server
from tornado.ioloop import IOLoop
from bokeh.embed import server_document
import panel as pn

pn.extension()

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

# Dictionary used to send documents from Flask to the Bokeh server.
DOCS = {}

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

    def getRequestArgList(self, request: Dict) -> List[str]:
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

        req_arg = request.get(name, None)

        ret = []

        if req_arg is not None:

            if arg_type is bool:
                if 'store_true' == arg_action:
                    if req_arg not in ['yes', 'true', '1', True]:
                        return []
                if 'store_false' == arg_action:
                    if req_arg not in ['false', 'no', '0', False]:
                        return []
            else:
                if req_arg == '':
                    return []

            ret.append('--%s' % name)

            if arg_type is not bool:
                if isinstance(req_arg, list):
                    ret += req_arg
                else:
                    if arg_type is list:
                        if '\n' in req_arg:
                            ret += req_arg.split('\n')
                        else:
                            ret += req_arg.split(',')
                    else:
                        ret.append(req_arg)

        return ret


def modify_doc(doc):
    args = doc.session_context.request.arguments
    doc_id = args['doc_id'][0].decode("utf-8")
    newdoc = DOCS.pop(doc_id)
    doc.add_root(newdoc.get_root(doc))


def bk_worker(bokeh_port, flask_port):
    server = Server({'/': modify_doc}, io_loop=IOLoop(), allow_websocket_origin=[f"127.0.0.1:{flask_port}"], port=bokeh_port)
    server.start()
    server.io_loop.start()


class SakWebappImpl(object):
    def __init__(self, plugin) -> None:
        super(SakWebappImpl, self).__init__()
        self.plugin = plugin
        self.app: Optional[Flask] = None
        self.bokeh_port: int

    def _getApp(self) -> Flask:
        thisDir = Path(__file__).resolve().parent
        staticDir = thisDir / 'web' / 'static'
        templateDir = thisDir / 'web' / 'template'

        if self.app is None:
            self.app = Flask('sak',
                             static_url_path='',
                             static_folder=str(staticDir),
                             template_folder=str(templateDir)
                             )
        return self.app

    def buildFlask(self, bokeh_port) -> Flask:
        app = self._getApp()

        @app.route("/")
        def index() -> ResponseBase:
            return redirect("index.html")

        _root_cmd = root_cmd()

        @app.route('/new/')
        @app.route('/new/<path:path>')
        def pages(path=''):
            web_ret = {}

            args = path.split('/')

            # Filter empty fields
            args = [x for x in args if x]

            # Get only the metadata.
            ret = sak_arg_parser(_root_cmd, args + ['-h'])

            if args:
                if args[-1] != ret['cmd'].name:
                    web_ret['error'] = True
                    web_ret[
                        'error_message'] = 'Could not find the path for %s' % (
                            api_root + '/' + path)
                    return jsonify(web_ret), 500

            cmd = ret['cmd']
            params = {}

            for arg in cmd.args:
                webarg = SakWebCmdArg(arg).getAsDict()

                name = webarg['name']
                default = webarg['default']
                choices = webarg['choices']

                if webarg['type'] in ['int', 'float', 'string']:
                    _params = {}
                    if choices:
                        if default is not None:
                            _params['value'] = str(default)
                        params[name] = pn.widgets.Select(name=name, options=choices, **_params)
                    else:
                        if default is not None:
                            _params['value'] = str(default)
                        params[name] = pn.widgets.TextInput(name=name, **_params)
                elif webarg['type'] in ['bool']:
                    params[name] = pn.widgets.Checkbox(name=name, value=default)
                elif webarg['type'] in ['list']:
                    _params = {}

                    if choices:
                        if default:
                            _params['value'] = default

                        _params['options'] = choices
                        if arg.completercb:
                            completer_args = SakCompleterArg(None, None, None, None)
                            _params['options'] = arg.completercb(completer_args)

                        params[name] = pn.widgets.CrossSelector(name=name, **_params)
                    elif default:
                        _params['value'] = default

                        if choices:
                            _params['options'] = choices
                        if arg.completercb is not None:
                            completer_args = SakCompleterArg(None, None, None, None)
                            _params['options'] = arg.completercb(completer_args)

                        params[name] = pn.widgets.MultiChoice(name=name, **_params)
                    else:
                        if default is not None:
                            _params['placeholder'] = str(default)
                        params[name] = pn.widgets.TextAreaInput(name=name, **_params)

            command = pn.Row(path, path)

            if cmd.callback is not None and callable(cmd.callback):
                class _callback:
                    def __init__(self, params, root_cmd, args, cmd):
                        self.first_call = True
                        self.params = params
                        self.root_cmd = root_cmd
                        self.args = args
                        self.cmd = cmd

                        self.output = pn.Column('Output here')
                        self.button = pn.widgets.Button(name='Run', button_type='primary')

                        self.layout = pn.Row(
                                pn.Column(f'## {self.cmd.name}', *self.params.values(), self.button),
                                self.output,
                                sizing_mode="stretch_both"
                                    )

                        self.button.on_click(self.update)

                    def update(self, event):
                        vargs = {param_name: param.value for param_name, param in self.params.items()}
                        new_output = self.callback(**vargs)
                        print('update', new_output)
                        self.output.clear()
                        self.output.append(new_output)
                        print('done')

                    def callback(self, **vargs):
                        param_args = []
                        for arg in cmd.args:
                            param_args += SakWebCmdArg(arg).getRequestArgList(vargs)

                        post_ret = sak_arg_parser(self.root_cmd, self.args + param_args)

                        web_ret = {}
                        web_ret['error'] = False
                        if 'error' in post_ret['argparse']:
                            web_ret['error'] = True
                            web_ret['error_message'] = post_ret['argparse']['error']
                            return web_ret

                        if 'value' in post_ret:
                            web_ret['result'] = post_ret['value']
                            if not web_ret['error']:
                                if has_pandas and isinstance(web_ret['result'], pd.DataFrame):
                                    return pn.pane.DataFrame(web_ret['result'])
                                return web_ret['result']

                        return None

                _foo = _callback(params, _root_cmd, args, cmd)
                command = _foo.layout

            doc_id = str(uuid.uuid1())
            DOCS[doc_id] = command
            args = {'doc_id': doc_id}

            script = server_document('http://localhost:%d/' % bokeh_port,  arguments=args)

            return render_template("index.html", script=script, template="Flask")


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
            ret = sak_arg_parser(_root_cmd, args + ['-h'])

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
                    param_args += arg.getRequestArgList(request.json)

                post_ret = sak_arg_parser(_root_cmd, args + param_args)

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

    def appStart(self, port: int, bokeh_port: int) -> None:
        pluginDirs = [
            p.has_plugin_path
            for p in self.plugin.has_context.has_plugin_manager.has_plugins
        ]

        ## Add all the plugin files to the watch list to restart server
        extra_files = []
        for pDir in pluginDirs:
            if not pDir:
                continue
            extra_files.append(os.path.join(pDir))
        extra_files = list(set(extra_files))

        # https://www.quora.com/How-is-it-possible-to-make-Flask-web-framework-non-blocking
        self.buildFlask(bokeh_port).run(extra_files=extra_files, port=port)

    def start(self, port: int, bokeh_port: int) -> None:
        # Start the bokeh in a separate thread.
        Thread(target=bk_worker, args=(bokeh_port, port,)).start()

        # Start the flask in the main thread.
        self.appStart(port, bokeh_port)

#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__version__ = "0.0.0"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

from sakcmd import SakCmd, SakArg, sak_arg_parser
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

#class SakWebCmd():
#    def __init__(self, cmd: SakCmd, root: str) -> None:
#        self.cmd = cmd
#        self.root = root
#        self.route = os.path.join(self.root, self.cmd.name)
#        self.args: List[SakWebCmdArg] = []
#        for arg in cmd.args:
#            self.args.append(SakWebCmdArg(arg))
#
#        self.subcmds: List[SakWebCmd] = []
#        for subcmd in cmd.subcmds:
#            self.subcmds.append(SakWebCmd(subcmd, self.route))
#
#    def __call__(self) -> ResponseBase:
#        if self.cmd.callback:
#            ret: Dict[str, Any] = {}
#
#            arg_list = []
#            for arg in self.args:
#                arg_list += arg.getRequestArgList(request)
#
#            sak_arg_parser(self.cmd, arg_list)
#            return jsonify({'TODO': 'TODO'})
#            #p = self.cmd.generateArgParse()
#
#            error_status = {}
#            def exit(p: ArgumentParser, status: Optional[str] = None, message: Optional[str] = None) -> None:
#                error_status['status'] = status
#                error_status['message'] = message
#
#            # TODO: How to legally override the exit method?
#            #p.exit = exit # type: ignore
#
#
#            try:
#                args = p.parse_args(arg_list)
#            except:
#                pass
#
#            ret.update({'error': False})
#
#            if error_status:
#                ret['error'] = True
#                ret.update(error_status)
#            else:
#                dargs: Dict[str, Any] = vars(args)
#
#                callback = dargs.pop('sak_callback')
#
#                ret['params'] = dargs
#
#                if callback:
#                    cret: SakCmdRet = callback(**dargs)
#                    ret['result'] = cret.retValue
#
#            if not ret['error']:
#                if has_pandas and isinstance(ret['result'], pd.DataFrame):
#                    if 1:
#                        ret['type'] = 'pd.DataFrame'
#                        ret['result'] = json.loads(ret['result'].reset_index().to_json(orient='records', date_format='iso'))
#                    else:
#                        ret['type'] = 'html'
#                        ret['result'] = ret['result'].reset_index().to_html()
#                elif has_matplotlib and isinstance(ret['result'], matplotlib.figure.Figure):
#                    ret['type'] = 'png'
#                    buf = io.BytesIO()
#                    ret['result'].savefig(buf, format='png')
#                    ret['result'] = base64.b64encode(buf.getvalue()).decode()
#                else:
#                    ret['type'] = 'string'
#                    ret['result'] = str(ret['result'])
#
#            tmpret = jsonify(ret)
#            return tmpret
#        else:
#            tmpret = jsonify(self.getAsDict())
#            return tmpret
#
#    def buildFlaskRoutes(self, app: Flask) -> None:
#        if SakCmd.EXP_WEB not in self.cmd.expose:
#            return
#
#        app.add_url_rule(
#                self.route,
#                self.route.replace('/', '_'),
#                self
#                )
#
#        for subcmd in self.subcmds:
#            subcmd.buildFlaskRoutes(app)
#
#    def getAsDict(self) -> Dict[str, Any]:
#        ret: Dict[str, Any] = { 'name': self.cmd.name, 'helpmsg': self.cmd.helpmsg}
#        ret['subcmds'] = [x.getAsDict() for x in self.subcmds if SakCmd.EXP_WEB in x.cmd.expose]
#        ret['args'] = [x.getAsDict() for x in self.args]
#        ret['isCallable'] = self.cmd.callback != None
#        ret['path'] = self.route
#        ret['parent_path'] = self.root
#        return ret


class SakWebappImpl(object):
    def __init__(self, plugin) -> None:
        super(SakWebappImpl, self).__init__()
        self.plugin = plugin
        self.app: Optional[Flask] = None

    def _getApp(self) -> Flask:
        thisDir = Path(__file__).resolve().parent
        staticDir = thisDir / 'web' / 'static'

        if self.app is None:
            self.app = Flask('sak', static_url_path='', static_folder=str(staticDir))
        return self.app


    def buildFlask(self) -> Flask:
        app = self._getApp()
        commands_root = '/api/cmd'

        @app.route("/")
        def index() -> ResponseBase:
            return redirect("index.html")

        # privatePlugins = ['sak', 'plugins']
        # plugins = [x for x in self.plugin.context.pluginManager.getPluginList() if x.name not in privatePlugins]

        # @app.route("/api/show/plugins")
        # def show_plugins() -> ResponseBase:
        #     return jsonify([x.name for x in plugins])

        #cmdTree = SakWebCmd(self.plugin.context.pluginManager.generateCommandsTree(), commands_root)
        #cmdTree.buildFlaskRoutes(app)

        root_cmd = self.plugin.context.plugin_manager.generateCommandsTree()

        api_root = '/api/sak'
        @app.route(api_root)
        @app.route(api_root + '/')
        @app.route(api_root + '/<path:path>', methods=['GET', 'POST'
            #,'DELETE', 'PATCH'
            ])
        def foobar(path=''):
            web_ret = {}

            args = path.split('/')

            # Get only the metadata.
            ret = sak_arg_parser(root_cmd, args + ['-h'])

            cmd = ret['cmd']
            webArgs = []
            if '_sak_cmd_args' in cmd:
                for arg in cmd['_sak_cmd_args']:
                    webArgs.append(SakWebCmdArg(arg))


            if '_sak_cmd' in cmd:
                web_ret['name'] = cmd['_sak_cmd'].name
                web_ret['helpmsg'] = cmd['_sak_cmd'].helpmsg

            if 'error' in ret['argparse']:
                web_ret['error'] = ret['error']
                return jsonify(web_ret), 500

            web_ret['subcmds'] = []
            for subcmd in ret.get('subcmds', []):
                if not subcmd.name:
                    continue
                web_ret['subcmds'].append({
                    'name': subcmd.name,
                    'helpmsg': subcmd.helpmsg,
                    })

            web_ret['isCallable'] = cmd.get('_sak_cmd_callback', None) is not None

            web_ret['path'] = api_root + '/' + path
            web_ret['parent_path'] = os.path.dirname(web_ret['path'])
            web_ret['args'] = []
            for arg in webArgs:
                web_ret['args'].append(arg.getAsDict())

            print(request.method)

            if request.method == 'GET':
                return jsonify(web_ret)

            if request.method == 'POST':
                #TODO(witt): Get the json info

                print(request.json)

                web_ret['args'] = []
                for arg in webArgs:
                    web_ret['args'].append(arg.getAsDict(request))

                param_args = []
                for arg in webArgs:
                    param_args += arg.getRequestArgList(request)

                post_ret = sak_arg_parser(root_cmd, args + param_args)


                if 'error' in post_ret['argparse']:
                    web_ret['error'] = post_ret['argparse']['error']
                    return jsonify(web_ret), 500


                web_ret['value'] = post_ret['value']

                return jsonify(web_ret)

            #if request.method == 'DELETE':
            #    #TODO(witt): Get the json info
            #    return jsonify(web_ret)

            return jsonify(isError= True, message= "Method not allowed", statusCode= 405), 405


        #api_root = '/api'

        ## class SakWebOnto(Resource):
        ##     def get(self, **kwargs):
        ##         return jsonify(kwargs)
        ## api = Api(app)
        #@app.route(api_root + '/onto')
        #@app.route(api_root + '/onto/<path:path>')
        #def onto(path=''):

        #    def process(state, path_list, env):
        #        env_type = type(env)
        #        # TODO: Sanityze the penv
        #        def sanitize(d):
        #            if not isinstance(d, dict):
        #                #if isinstance(d, list) or inspect.isgenerator(d):
        #                if isinstance(d, tuple):
        #                    nenv = {}
        #                    for idx, v in enumerate(d):
        #                        k = str(idx)
        #                        nenv[k] = v
        #                    d = nenv
        #                elif isinstance(d, Iterable):
        #                    nenv = {}
        #                    for idx, v in enumerate(d):
        #                        #TODO: If it is a thing, I can put the name in the index
        #                        k = str(idx)
        #                        try:
        #                            k = v.name
        #                        except:
        #                            pass
        #                        k  = k.replace('/', '__')
        #                        nenv[k] = v
        #                    d = nenv
        #                elif isinstance(d, str):
        #                    d = d
        #                elif inspect.ismethod(d):
        #                    d = sanitize(d())
        #                else:

        #                    export_lut = {
        #                            owl.Ontology: ['name', 'individuals', 'classes'],
        #                            owl.ThingClass: ['name', 'get_properties', 'get_inverse_properties']
        #                            }

        #                    obj = d

        #                    d = {}
        #                    for classType, exporlist in export_lut.items():
        #                        if isinstance(obj, classType):
        #                            for k in dir(obj):
        #                                if k not in exporlist:
        #                                    continue
        #                                if k.startswith('_'):
        #                                    continue
        #                                dd = getattr(obj, k)
        #                                k = k.replace('/', '__')
        #                                d[k] = dd
        #                            break
        #            return d

        #        env = sanitize(env)

        #        if not path_list or not path_list[0]:
        #            def norm_dict(d, depth=-1):
        #                nd = {}
        #                if depth==0:
        #                    return str(d)
        #                if isinstance(d, dict):
        #                    for k, v in d.items():
        #                        k = k.replace('/', '__')
        #                        nd[k] = norm_dict(v, depth-1)
        #                #elif isinstance(d, list) or inspect.isgenerator(d):
        #                elif isinstance(d, tuple):
        #                    for idx, v in enumerate(d):
        #                        k = str(idx)
        #                        nd[k] = norm_dict(v, depth-1)
        #                elif isinstance(d, Iterable):
        #                    for idx, v in enumerate(d):
        #                        k = str(idx)
        #                        k = k.replace('/', '__')
        #                        nd[k] = norm_dict(v, depth-1)
        #                elif isinstance(d, str):
        #                    return d
        #                elif inspect.ismethod(d):
        #                    # TODO: I can put the documentation here maybe
        #                    nd = repr(d)
        #                    #try:
        #                    #    nd = norm_dict( d(), depth - 1)
        #                    #except:
        #                    #    nd = repr(d)
        #                else:
        #                    try:
        #                        jsonify(d)
        #                        nd = d
        #                    except:
        #                        nd = repr(d)
        #                return nd

        #            nenv = norm_dict(env, 1)

        #            ret = {
        #                    'type': str(env_type),
        #                    'value': nenv
        #                    }
        #            return jsonify(ret)

        #        if not path_list[0] in env:
        #            return jsonify('[ERROR] no %s in env' % path_list[0])
        #        else:
        #            el = env[path_list[0]]
        #            return process(state, path_list[1:], el)

        #    ontologies = {'sak': onto}
        #    for p in plugins:
        #        ontologies[p.ontology.name] = p.ontology
        #    return process('foo', path.split('/'), ontologies)
        #    #return process('foo', path.split('/'), self)

        return app

    def appStart(self, port:int) -> None:
        pluginDirs = [p.getPath() for p in self.plugin.context.pluginManager.getPluginList()]

        ## Add all the plugin files to the watch list to restart server
        extra_files = []
        for pDir in pluginDirs:
            if not pDir:
                continue
            extra_files.append(os.path.join(pDir))
        extra_files = list(set(extra_files))
        print(extra_files)

        # https://www.quora.com/How-is-it-possible-to-make-Flask-web-framework-non-blocking
        self.buildFlask().run(
                debug=True,
                extra_files=extra_files,
                #threaded=True,
                port=port
                )


    def start(self, port:int) -> None:
        self.appStart(port)


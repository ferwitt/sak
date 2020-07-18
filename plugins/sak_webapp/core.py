#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

import base64
import io
import json
import os
from pathlib import Path
from threading import Thread
from typing import Any, Dict, Optional

import bokeh
import bokeh.document
import bokeh.embed
import bokeh.server.server
import flask
import panel as pn
import tornado
import tornado.gen
from flask.wrappers import ResponseBase  # type: ignore

from saklib.sak import plm, root_cmd
from saklib.sakcmd import SakArg, SakCmdWrapper, sak_arg_parser
from saklib.sakio import register_threaded_stderr_tee, register_threaded_stdout_tee
from saklib.sakplugin import load_file

has_pandas = False
try:
    import pandas as pd

    has_pandas = True
except Exception:
    pass

has_matplotlib = False
try:
    import matplotlib

    has_matplotlib = True
except Exception:
    pass


def set_extensions() -> None:
    pn.extension()


def get_impl() -> Dict[str, Any]:
    webapp_file = Path(__file__).resolve().parent / "webapp.py"
    webapp = load_file(webapp_file)
    return webapp  # type: ignore


def modify_doc(doc: bokeh.document.document.Document) -> None:
    # Get the doc object
    newdoc = get_impl()["SakDoc"](doc)
    doc.add_root(newdoc.view().get_root(doc))


def bk_worker(bokeh_port: int, flask_port: int) -> None:
    server = bokeh.server.server.Server(
        {"/": modify_doc},
        io_loop=tornado.ioloop.IOLoop(),
        allow_websocket_origin=[f"127.0.0.1:{flask_port}"],
        port=bokeh_port,
    )
    server.start()
    server.io_loop.start()


class SakWebappImpl(object):
    def __init__(self) -> None:
        super(SakWebappImpl, self).__init__()
        self.app: Optional[flask.Flask] = None
        self.bokeh_port: int

    def _getApp(self) -> "flask.Flask":
        thisDir = Path(__file__).resolve().parent
        staticDir = thisDir / "web" / "static"
        templateDir = thisDir / "web" / "template"

        if self.app is None:
            self.app = flask.Flask(
                "sak",
                static_url_path="",
                static_folder=str(staticDir),
                template_folder=str(templateDir),
            )
        return self.app

    def buildFlask(self, bokeh_port: int) -> "flask.Flask":
        app = self._getApp()

        @app.route("/")
        def index() -> ResponseBase:
            return flask.redirect("/new")

        _root_cmd = root_cmd()

        @app.route("/new")
        @app.route("/new/")
        @app.route("/new/<path:path>")
        def pages(path: str = "") -> ResponseBase:
            args = {"path": path}

            script = bokeh.embed.server_document(
                "http://127.0.0.1:%d/" % bokeh_port, arguments=args
            )

            return flask.render_template("index.html", script=script, template="Flask")

        api_root = "/api/sak"

        @app.route(api_root)
        @app.route(api_root + "/")
        @app.route(api_root + "/<path:path>", methods=["GET", "POST"])
        def cmd_api(path: str = "") -> ResponseBase:
            web_ret: Dict[str, Any] = {}

            args = path.split("/")

            # Filter empty fields
            args = [x for x in args if x]

            # Get only the metadata.
            ret = sak_arg_parser(_root_cmd, args + ["-h"])

            if args:
                if args[-1] != ret["cmd"].name:
                    web_ret["error"] = True
                    web_ret["error_message"] = "Could not find the path for %s" % (
                        api_root + "/" + path
                    )
                    return flask.jsonify(web_ret), 500

            cmd = ret["cmd"]
            webArgs = []
            for arg in cmd.args:
                webArgs.append(get_impl()["SakWebCmdArg"](arg))

            web_ret["name"] = cmd.name
            web_ret["helpmsg"] = cmd.helpmsg

            web_ret["error"] = False
            if "error" in ret["argparse"]:
                web_ret["error"] = True
                web_ret["error_message"] = ret["error"]
                return flask.jsonify(web_ret), 500

            web_ret["subcmds"] = []
            for subcmd in cmd.subcmds:
                subcmd = SakCmdWrapper(subcmd)

                if not subcmd.name:
                    continue
                web_ret["subcmds"].append(
                    {
                        "name": subcmd.name,
                        "helpmsg": subcmd.helpmsg,
                        "path": os.path.join(api_root, path, subcmd.name),
                        "parent_path": os.path.join(api_root, path),
                        "subcmds": [],
                    }
                )

            web_ret["isCallable"] = cmd.callback is not None

            web_ret["path"] = os.path.join(api_root, path)
            web_ret["parent_path"] = os.path.dirname(web_ret["path"])
            web_ret["args"] = []
            for arg in webArgs:
                web_ret["args"].append(arg.getAsDict())

            if flask.request.method == "GET":
                return flask.jsonify(web_ret)

            if flask.request.method == "POST":
                web_ret["args"] = []
                for arg in webArgs:
                    web_ret["args"].append(arg.getAsDict(flask.request))

                param_args = []
                for arg in webArgs:
                    param_args += arg.getRequestArgList(flask.request.json)

                post_ret = sak_arg_parser(_root_cmd, args + param_args)

                print(post_ret)

                web_ret["error"] = False
                if "error" in post_ret["argparse"]:
                    web_ret["error"] = True
                    web_ret["error_message"] = post_ret["argparse"]["error"]
                    return flask.jsonify(web_ret), 500

                web_ret["result"] = post_ret["value"]

                if not web_ret["error"]:
                    if has_pandas and isinstance(web_ret["result"], pd.DataFrame):
                        if 1:
                            web_ret["type"] = "pd.DataFrame"
                            web_ret["result"] = json.loads(
                                web_ret["result"]
                                .reset_index()
                                .to_json(orient="records", date_format="iso")
                            )
                        else:
                            web_ret["type"] = "html"
                            web_ret["result"] = (
                                web_ret["result"].reset_index().to_html()
                            )
                    elif has_matplotlib and isinstance(
                        web_ret["result"], matplotlib.figure.Figure
                    ):
                        web_ret["type"] = "png"
                        buf = io.BytesIO()
                        web_ret["result"].savefig(buf, format="png")
                        web_ret["result"] = base64.b64encode(buf.getvalue()).decode()
                    else:
                        web_ret["type"] = "string"
                        web_ret["result"] = str(web_ret["result"])

                return flask.jsonify(web_ret)

            return (
                flask.jsonify(
                    isError=True, message="Method not allowed", statusCode=405
                ),
                405,
            )

        return app

    def appStart(self, port: int, bokeh_port: int) -> None:
        pluginDirs = [p._has_plugin_path for p in plm.has_plugins]

        # Add all the plugin files to the watch list to restart server
        extra_files = []
        for pDir in pluginDirs:
            if not pDir:
                continue
            extra_files.append(os.path.join(pDir))
        extra_files = list(set(extra_files))

        # https://www.quora.com/How-is-it-possible-to-make-Flask-web-framework-non-blocking
        app = self.buildFlask(bokeh_port)

        app.run(extra_files=extra_files, port=port)

    def start(self, port: int, bokeh_port: int) -> None:

        set_extensions()

        # Start the bokeh in a separate thread.
        Thread(
            target=bk_worker,
            args=(
                bokeh_port,
                port,
            ),
        ).start()

        # Start the flask in the main thread.
        self.appStart(port, bokeh_port)


sakwebapp = SakWebappImpl()


@SakArg("port", short_name="p")
@SakArg("bokeh_port", short_name="b")
def start(port: int = 2020, bokeh_port: int = 5006) -> None:
    """
    Start webapp.

    :param port: Server port (default: 2020).
    :param bokeh_port: The Bokeh server port (default: 5006).
    """
    register_threaded_stdout_tee()
    register_threaded_stderr_tee()
    sakwebapp.start(port, bokeh_port)


EXPOSE = {"start": start}

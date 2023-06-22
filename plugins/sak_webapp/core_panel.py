#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

from pathlib import Path

import bokeh
import bokeh.document
import bokeh.server.server
import panel as pn
import tornado
import tornado.gen
from webapp_cmd import register_commands

from saklib.sak import plm
from saklib.sakio import register_threaded_stderr_tee, register_threaded_stdout_tee
from saklib.sakplugin import load_file


def modify_doc(doc: "bokeh.document.document.Document") -> None:
    webapp_file = Path(__file__).resolve().parent / "webapp.py"
    webapp = load_file(webapp_file)

    # Get the doc object
    newdoc = webapp["SakDoc"](doc)

    newdoc.server_doc()


def bk_worker(bokeh_port: int) -> None:

    pn.extension()

    server = bokeh.server.server.Server(
        {"/": modify_doc},
        io_loop=tornado.ioloop.IOLoop(),
        allow_websocket_origin=[f"127.0.0.1:{bokeh_port}"],
        port=bokeh_port,
    )
    server.start()
    server.io_loop.start()


def start(port: int = 2020) -> None:
    # Prepare stdout and sterr capture.
    register_threaded_stdout_tee()
    register_threaded_stderr_tee()

    # Force loading plugins.
    register_commands()
    for plugin in plm.getPluginList():
        dir(plugin)

    # Start server.
    print(f"Running on http://127.0.0.1:{port}/")
    bk_worker(port)

#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

import os
import sys
from pathlib import Path

import bokeh
import bokeh.document
import bokeh.embed
import bokeh.server.server
import panel as pn
import tornado
import tornado.gen

from saklib.sak import ctx
from saklib.sakcmd import SakArg, SakCmd
from saklib.sakio import register_threaded_stderr_tee, register_threaded_stdout_tee
from saklib.sakplugin import load_file


def set_extensions() -> None:
    pass


def modify_doc(doc: bokeh.document.document.Document) -> None:
    webapp_file = Path(__file__).resolve().parent / "webapp.py"
    webapp = load_file(webapp_file)

    # Get the doc object
    newdoc = webapp["SakDoc"](doc)

    newdoc.server_doc()

    return
    newdoc_layout = newdoc.view()

    doc.add_root(newdoc_layout.get_root(doc))

    return

    args = doc.session_context.request.arguments

    path = ""
    try:
        path = args["path"][0].decode("utf-8")
    except Exception as e:
        print("ERROR! Failed to get the path from the args", str(e))

    # TODO(witt): Make some way to cache this and not reload the module all the time!
    try:
        webapp_file = Path(__file__).resolve().parent / "webapp.py"
        webapp = load_file(webapp_file)

        # Get the doc object
        newdoc = webapp["get_callback_object"](doc, path)
        newdoc_layout = newdoc.layout

        doc.add_root(newdoc_layout.get_root(doc))
    except Exception as e:
        # TODO(witt): I could update the doc with some nice error message :)
        print("ERROR! Failed to load the webapp or to execute the command.", str(e))


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


@SakCmd("start", helpmsg="Start webapp")
@SakArg("port", short_name="p", helpmsg="The Bokeh server port (default: 5006)")
def start(port: int = 2020) -> None:
    set_extensions()

    register_threaded_stdout_tee()
    register_threaded_stderr_tee()

    print(f"Running on http://127.0.0.1:{port}/")
    bk_worker(port)


def jupyter() -> None:
    if ctx.sak_global is None:
        raise Exception("No context available")

    sys.path.append(str(ctx.sak_global / "saklib"))

    os.environ["PATH"] = str(ctx.sak_global / "saklib") + ":" + os.environ["PATH"]
    os.system("jupyter lab")


EXPOSE = {"start": start, "jupyter": jupyter}

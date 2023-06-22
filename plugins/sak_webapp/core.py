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
from typing import Any, Callable, List, Tuple

import bokeh
import bokeh.document
import bokeh.embed
import bokeh.server.server
import panel as pn
import tornado
import tornado.gen
from webapp_cmd import register_commands

from saklib.sak import ctx, plm
from saklib.sakcmd import SakArg, SakCmd
from saklib.sakio import register_threaded_stderr_tee, register_threaded_stdout_tee
from saklib.sakplugin import load_file

SCRIPT_PATH = Path(__file__).resolve()
SRC_PATH = SCRIPT_PATH.parent
sys.path.append(str(SRC_PATH))


class WebAppCtx:
    def __init__(self) -> None:
        self.panel_register_cbs: List[Tuple[str, str, Path, Callable[[Any], None]]] = []

    def panel_register(
        self,
        name: str,
        path: str,
        file_path: Path,
        callback: Callable[[Any], None],
    ) -> None:
        for iname, ipath, _, icallback in self.panel_register_cbs:
            icb_name = icallback if isinstance(icallback, str) else icallback.__name__
            cb_name = callback if isinstance(callback, str) else callback.__name__
            if iname == name and ipath == path and icb_name == cb_name:
                return
        self.panel_register_cbs.append((name, path, file_path, callback))


def panel_register(
    name: str,
    path: str,
    file_path: Path,
    callback: Callable[[Any], None],
) -> None:
    if "webapp" not in ctx.plugin_data:
        ctx.plugin_data["webapp"] = WebAppCtx()
    wac = ctx.plugin_data["webapp"]
    wac.panel_register(name, path, file_path, callback)


def set_extensions() -> None:
    pass


def modify_doc(doc: bokeh.document.document.Document) -> None:
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


@SakCmd("start", helpmsg="Start webapp")
@SakArg("port", short_name="p", helpmsg="The Bokeh server port (default: 5006)")
def start(port: int = 2020) -> None:
    # Prepare stdout and sterr capture.
    register_threaded_stdout_tee()
    register_threaded_stderr_tee()

    # Force loading plugins.
    register_commands()
    for plugin in plm.getPluginList():
        dir(plugin)

    # Set extensions.
    set_extensions()

    # Start server.
    print(f"Running on http://127.0.0.1:{port}/")
    bk_worker(port)


def jupyter() -> None:
    if ctx.sak_global is None:
        raise Exception("No context available")

    sys.path.append(str(ctx.sak_global / "saklib"))

    os.environ["PATH"] = str(ctx.sak_global / "saklib") + ":" + os.environ["PATH"]
    os.system("jupyter lab")


EXPOSE = {
    "start": start,
    "jupyter": jupyter,
    "panel_register": panel_register,
}

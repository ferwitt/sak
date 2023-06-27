#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

import sys
from pathlib import Path
from typing import List, Optional, Tuple

from saklib.sak import ctx
from saklib.sakcmd import SakArg, SakCmd

SCRIPT_PATH = Path(__file__).resolve()
SRC_PATH = SCRIPT_PATH.parent
sys.path.append(str(SRC_PATH))


class WebAppCtx:
    def __init__(self) -> None:
        self.panel_register_cbs: List[Tuple[str, str, Path, str, Optional[str]]] = []

    def panel_register(
        self,
        name: str,
        path: str,
        file_path: Path,
        callback: str,
        tmplmod: Optional[str],
    ) -> None:
        for iname, ipath, _, icallback, _ in self.panel_register_cbs:
            icb_name = icallback
            cb_name = callback
            if iname == name and ipath == path and icb_name == cb_name:
                return
        self.panel_register_cbs.append((name, path, file_path, callback, tmplmod))


def panel_register(
    name: str,
    path: str,
    file_path: Path,
    callback: str,
    tmplmod: Optional[str],
) -> None:
    if "webapp" not in ctx.plugin_data:
        ctx.plugin_data["webapp"] = WebAppCtx()
    wac = ctx.plugin_data["webapp"]
    wac.panel_register(name, path, file_path, callback, tmplmod)


@SakCmd("start", helpmsg="Start webapp")
@SakArg("port", short_name="p", helpmsg="The Bokeh server port (default: 5006)")
def start(port: int = 2020) -> None:
    from core_panel import start

    start(port=port)


EXPOSE = {
    "start": start,
    "panel_register": panel_register,
}

if __name__ == "__main__":
    pass

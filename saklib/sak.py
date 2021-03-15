#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__version__ = "0.1.0"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

import os
import subprocess
import sys

sys.path.append(os.environ["SAK_GLOBAL"])


try:
    import lazy_import

    lazy_import.lazy_module("param")
    lazy_import.lazy_module("panel")
    lazy_import.lazy_module("flask")
    lazy_import.lazy_module("wrappers")
    lazy_import.lazy_module("bokeh")
    lazy_import.lazy_module("bokeh.server.server")
    lazy_import.lazy_module("bokeh.embed")
    # lazy_import.lazy_module('bokeh.models')
    lazy_import.lazy_module("panel")
    lazy_import.lazy_module("pandas")
    # lazy_import.lazy_module('pandas_bokeh')
    lazy_import.lazy_module("matplotlib")
    lazy_import.lazy_module("matplotlib.pyplot")
    lazy_import.lazy_module("matplotlib.animation")
    lazy_import.lazy_module("matplotlib.widgets")
    lazy_import.lazy_module("pylab")
    lazy_import.lazy_module("tornado")
    # lazy_import.lazy_module('pymovies')
    lazy_import.lazy_module("numpy")
    lazy_import.lazy_module("scipy.optimize")
    lazy_import.lazy_module("scipy.spatial.transform")
    lazy_import.lazy_module("git")
except ImportError:
    import sys
    import traceback

    print("Exception in user code:")
    print("-" * 60)
    traceback.print_exc(file=sys.stdout)
    print("-" * 60)

    # If import fails, then ask if the user wants to try to update the requirements
    from saklib.sakconfig import install_core_requirements  # noqa: E402

    install_core_requirements()

from saklib.sakcmd import SakCmd, sak_arg_parser  # noqa: E402
from saklib.sakplugin import SakContext, SakPlugin, SakPluginManager  # noqa: E402

ctx = SakContext()
plm = SakPluginManager()

ctx.has_plugin_manager = plm
plm.has_context = ctx


class SakShow(SakPlugin):
    """General information about SAK."""

    @SakCmd(
        "version", expose=[SakCmd.EXP_CLI, SakCmd.EXP_WEB], helpmsg="Show SAK version."
    )
    def show_version(self) -> str:
        return "Version: %s" % (__version__)

    @SakCmd("argcomp", helpmsg="Show the autocomplete string")
    def show_argcomp(self) -> None:
        subprocess.call(["register-python-argcomplete", "sak", "-s", "bash"])
        return None


plm.addPlugin(SakShow(ctx, "show"))
# plm.addPlugin(SakPlugins(ctx, 'plugins'))

if ctx.sak_global:
    sys.path.append(str(ctx.sak_global / "plugins"))
    plm.loadPlugins(ctx.sak_global / "plugins")
if ctx.sak_local and ctx.sak_local != ctx.sak_global:
    sys.path.append(str(ctx.sak_local / "plugins"))
    plm.loadPlugins(ctx.sak_local / "plugins")


def root_cmd() -> SakCmd:
    root = SakCmd(
        "sak", helpmsg="Group everyday developer's tools in a swiss-army-knife command."
    )
    for plugin in plm.has_plugins:
        root.subcmds.append(plugin)
    return root


def main() -> None:
    root = root_cmd()

    args = sys.argv[1:]
    ret = sak_arg_parser(root, args)

    if "error" in ret["argparse"]:
        sys.stderr.write(ret["argparse"]["error"])
        sys.exit(-1)

    if "help" in ret["argparse"]:
        sys.stdout.write(ret["argparse"]["help"])
        sys.exit(0)

    if ret["value"] is not None:
        print(type(ret["value"]))

        if hasattr(ret["value"], "show"):
            ret["value"].show()
        elif "bokeh" in str(type(ret["value"])):
            from bokeh.plotting import show

            show(ret["value"])
        else:
            print(ret["value"])


if __name__ == "__main__":
    if True:
        main()
    else:
        import cProfile

        cProfile.run("main()", "/tmp/sak.profile")

#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__version__ = "0.5.0"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

import os
import subprocess
import sys

sys.path.append(os.environ["SAK_GLOBAL"])
os.environ["NUMEXPR_MAX_THREADS"] = "8"


from saklib.sakcmd import SakCmd, sak_arg_parser  # noqa: E402
from saklib.sakplugin import SakContext, SakPlugin, SakPluginManager  # noqa: E402

ctx = SakContext()
plm = SakPluginManager()

ctx.has_plugin_manager = plm
plm.has_context = ctx

IS_ARGCOMP_COMMAND = " ".join(sys.argv[1:]) == "show argcomp"


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
        sys.stderr.write(f'ERROR: {ret["argparse"]["error"]}\n')
        sys.exit(-1)

    if "help" in ret["argparse"]:
        sys.stdout.write(ret["argparse"]["help"])
        sys.exit(0)

    if ret["value"] is not None:

        if hasattr(ret["value"], "show"):
            ret["value"].show()
        elif "bokeh" in str(type(ret["value"])):
            from bokeh.plotting import show

            show(ret["value"])
        else:
            print(ret["value"])


def run_pdb() -> None:
    if os.environ.get("SAK_PDB", False):
        import pdb

        pdb.run("main()")
    else:
        main()


if __name__ == "__main__":
    profile = os.environ.get("SAK_PROFILE", False) is not False
    if not profile:
        run_pdb()
    else:
        import cProfile

        cProfile.run("run_pdb()", "/tmp/sak.profile")

        if not IS_ARGCOMP_COMMAND:
            print(80 * "-")
            print(
                "To visualize the profiling result, please execute:\n\t$ pyprof2calltree -i /tmp/sak.profile -k"
            )

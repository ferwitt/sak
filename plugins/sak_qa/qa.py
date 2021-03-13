#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

from saklib.sak import root_cmd, plm, ctx
from saklib.sakcmd import SakCmd, SakArg, sak_arg_parser, SakCmdWrapper
from saklib.sakplugin import load_file
from saklib.sakio import register_threaded_stdout_tee, register_threaded_stderr_tee

from saklib.sakconfig import SAK_GLOBAL, SAK_LOCAL, CURRENT_DIR

import subprocess


@SakCmd("mypy", helpmsg="Execute mypy for Sak and Plugins")
def mypy() -> None:

    cmd = ["mypy", ".", "--strict", "--exclude", "python", "--ignore-missing-imports"]

    cwd = SAK_GLOBAL
    subprocess.run(cmd, check=True, cwd=cwd)


@SakCmd("flake8", helpmsg="Execute flake8 for Sak and Plugins")
def flake8() -> None:
    cmd = ["flake8", str(SAK_GLOBAL / "saklib"), str(SAK_GLOBAL / "plugins")]

    cwd = SAK_GLOBAL
    subprocess.run(cmd, check=True, cwd=cwd)


@SakCmd("black", helpmsg="Execute black format for Sak and Plugins")
def black() -> None:
    cmd = ["black", str(SAK_GLOBAL / "saklib"), str(SAK_GLOBAL / "plugins")]

    cwd = SAK_GLOBAL
    subprocess.run(cmd, check=True, cwd=cwd)


EXPOSE = {"mypy": mypy, "flake8": flake8, "black": black}

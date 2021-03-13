#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

from saklib.sakcmd import SakCmd
from saklib.sakconfig import SAK_GLOBAL

import subprocess


@SakCmd("mypy", helpmsg="Execute mypy for Sak and Plugins")
def mypy() -> None:
    if SAK_GLOBAL is None:
        raise Exception("No SAK_GLOBAL defined")

    cmd = [
        "mypy",
        str(SAK_GLOBAL / "saklib"),
        str(SAK_GLOBAL / "plugins"),
        "--strict",
        "--exclude",
        "python",
        "--ignore-missing-imports",
        "--show-absolute-path",
    ]

    cwd = SAK_GLOBAL
    subprocess.run(cmd, check=True, cwd=cwd)


@SakCmd("flake8", helpmsg="Execute flake8 for Sak and Plugins")
def flake8() -> None:
    if SAK_GLOBAL is None:
        raise Exception("No SAK_GLOBAL defined")
    cmd = ["flake8", str(SAK_GLOBAL / "saklib"), str(SAK_GLOBAL / "plugins")]

    cwd = SAK_GLOBAL
    subprocess.run(cmd, check=True, cwd=cwd)


@SakCmd("black", helpmsg="Execute black format for Sak and Plugins")
def black() -> None:
    if SAK_GLOBAL is None:
        raise Exception("No SAK_GLOBAL defined")
    cmd = ["black", str(SAK_GLOBAL / "saklib"), str(SAK_GLOBAL / "plugins")]

    cwd = SAK_GLOBAL
    subprocess.run(cmd, check=True, cwd=cwd)


EXPOSE = {"mypy": mypy, "flake8": flake8, "black": black}

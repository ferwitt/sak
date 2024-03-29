# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

import os
import subprocess
import sys
from pathlib import Path
from typing import Any, List, Optional


def find_in_parent(dirname: Path, name: Path) -> Optional[Path]:
    if (dirname / name).exists():
        return dirname / name
    if dirname.parent != Path("/"):
        return find_in_parent(dirname.parent, name)
    return None


SCRIPT_DIR = Path(__file__).parent.resolve()
CURRENT_DIR = Path(".").resolve()

if "SAK_GLOBAL" not in os.environ:
    SAK_GLOBAL = find_in_parent(SCRIPT_DIR, Path(".sak"))
    if SAK_GLOBAL is not None:
        os.environ["SAK_GLOBAL"] = str(SAK_GLOBAL)
else:
    SAK_GLOBAL = Path(os.environ["SAK_GLOBAL"])

SAK_LOCAL = find_in_parent(CURRENT_DIR, Path(".sak"))


def install_core_requirements(ask_confirm: bool = True) -> None:
    if SAK_GLOBAL is None:
        print("Something wrong happened, there is not global SAK installed")
        return

    # TODO: Extract this to a common file
    if " ".join(sys.argv[1:]) == "show argcomp":
        return

    if ask_confirm:
        if not input(
            "There are dependencies missing for SAK core, would like to install? [y/N]"
        ) in ["Y", "y", "yes"]:
            sys.exit(-1)

    subprocess.check_call(
        ["/usr/bin/env", "pip", "install", "-r", str(SAK_GLOBAL / "requirements.txt")],
        stdout=sys.stdout,
        stderr=sys.stderr,
    )


class SakConfig(object):
    def __init__(self, path: Path) -> None:
        super(SakConfig, self).__init__()
        self.path: List[Any] = []

    def get(self, key: str) -> str:
        return "NOT IMPLEMENTED"

    def set(self, key: str, value: str) -> str:
        return "NOT IMPLEMENTED"

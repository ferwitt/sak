# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

import os
import platform
import subprocess
import sys

CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))

if "SAK_GLOBAL" not in os.environ:
    SAK_GLOBAL = os.path.abspath(os.path.join(os.environ["HOME"], ".sak"))
    os.environ["SAK_GLOBAL"] = SAK_GLOBAL
else:
    SAK_GLOBAL = os.environ["SAK_GLOBAL"]


# SAK will not use the system python, but will download miniconda
SAK_PYTHON = os.path.join(SAK_GLOBAL, "python")
SAK_PYTHON_BIN = os.path.join(SAK_PYTHON, "miniconda3", "bin", "python3")


def check_python() -> bool:
    return os.path.exists(SAK_PYTHON_BIN)


def pip_install() -> None:
    pass


MINICONDA_LINKS = {
    "x86": "https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86.sh",
    "x86_64": "https://repo.anaconda.com/miniconda/Miniconda3-py38_4.12.0-Linux-x86_64.sh",
    "i686": "https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86.sh",
}


def install_python(ask_confirm: bool = True) -> None:
    if " ".join(sys.argv[1:]) == "show argcomp":
        return

    if check_python():
        return

    if ask_confirm:
        if not input(
            "No local python found in SAK directory, would like to install? [y/N]"
        ) in ["Y", "y", "yes"]:
            sys.exit(-1)

    if not os.path.exists(SAK_PYTHON):
        os.makedirs(SAK_PYTHON)

    miniconda_installer = os.path.join(SAK_PYTHON, "miniconda.sh")
    if not os.path.exists(miniconda_installer):
        current_platform = platform.machine()
        link = MINICONDA_LINKS[current_platform]
        subprocess.check_call(
            [
                "wget",
                link,
                "-O",
                miniconda_installer,
            ]
        )

    instalation_prefix = os.path.join(SAK_PYTHON, "miniconda3")
    subprocess.check_call(
        ["/usr/bin/env", "bash", miniconda_installer, "-b", "-p", instalation_prefix]
    )

    os.environ["PATH"] = os.path.dirname(SAK_PYTHON_BIN) + ":" + os.environ["PATH"]
    subprocess.check_call(
        [
            "/usr/bin/env",
            "pip",
            "install",
            "-r",
            os.path.join(SAK_GLOBAL, "requirements.txt"),
        ]
    )


def install() -> None:
    if platform.machine() in MINICONDA_LINKS:
        # Only try to run inside miniconda if in the suppoted platforms.
        ask_confirm = os.environ.get("SAK_ASK_CONFIRM", "YES") == "YES"
        install_python(ask_confirm=ask_confirm)


def run() -> None:
    use_miniconda_flag = os.environ.get("SAK_USE_MINICONDA", "YES") == "YES"

    current_platform = platform.machine()
    is_supported_env = current_platform in MINICONDA_LINKS

    if use_miniconda_flag and is_supported_env:
        install()

        os.environ["PATH"] = os.path.dirname(SAK_PYTHON_BIN) + ":" + os.environ["PATH"]

        cmd = [SAK_PYTHON_BIN, os.path.join(SAK_GLOBAL, "saklib", "sak.py")] + sys.argv[
            1:
        ]
        ret = os.system(" ".join(['"%s"' % x for x in cmd]))
        if ret:
            sys.exit(-1)
    else:
        sys.path.append(os.path.join(SAK_GLOBAL, "saklib"))
        from saklib import sak

        sak.main()

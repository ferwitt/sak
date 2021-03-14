#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

from saklib.sakcmd import SakCmd
from saklib.sakconfig import SAK_GLOBAL

import re
import sys
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
        "--pretty",
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


@SakCmd("test", helpmsg="Execute tests for Sak and Plugins")
def test(coverage: bool = False) -> None:
    if SAK_GLOBAL is None:
        raise Exception("No SAK_GLOBAL defined")

    cmd = []

    if coverage:
        cmd += ["coverage", "run", "--source=saklib,plugins"]
    else:
        cmd += ["python"]

    cmd += [
        "-m",
        "unittest",
        "discover",
        "-s",
        str(SAK_GLOBAL / "saklib"),
        "-s",
        str(SAK_GLOBAL / "plugins"),
        "-p",
        "*_test.py",
    ]

    cwd = SAK_GLOBAL

    normalize_file_path = True
    if normalize_file_path:
        p = subprocess.Popen(
            cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        if (p.stdout is None) or (p.stderr is None):
            raise Exception('Failed to execute "%s" ' % (" ".join(cmd)))

        def convertPythonTracebackFileToNormalizeFile(line: str) -> str:
            return re.sub(r'^ *File "(.*?)", line (\d+),', r"\1:\2:", line, re.M)

        for l in p.stdout:
            sys.stdout.write(
                convertPythonTracebackFileToNormalizeFile(l.decode("utf-8"))
            )
            sys.stdout.flush()
        for l in p.stderr:
            sys.stderr.write(
                convertPythonTracebackFileToNormalizeFile(l.decode("utf-8"))
            )
            sys.stderr.flush()
        p.communicate()
        if p.returncode != 0:
            raise Exception(
                'Failed to execute "%s" ret core: %d' % (" ".join(cmd), p.returncode)
            )
    else:
        subprocess.run(cmd, check=True, cwd=cwd)


@SakCmd("report", helpmsg="Show the coverage report")
def coverage_report(html: bool = False) -> None:
    if SAK_GLOBAL is None:
        raise Exception("No SAK_GLOBAL defined")

    test(coverage=True)

    # For more information check: https://coverage.readthedocs.io/en/coverage-5.5/
    cmd = []
    if html:
        cmd += ["coverage", "html"]
    else:
        cmd += ["coverage", "report"]

    cwd = SAK_GLOBAL
    subprocess.run(cmd, check=True, cwd=cwd)

    if html:
        subprocess.run(["xdg-open", "htmlcov/index.html"], check=True, cwd=cwd)


EXPOSE = {
    "mypy": mypy,
    "flake8": flake8,
    "black": black,
    "test": test,
    "coverage": {"report": coverage_report},
}

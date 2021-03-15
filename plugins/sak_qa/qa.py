#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

from saklib.sak import plm
from saklib.sakcmd import SakCmd
from saklib.sakconfig import SAK_GLOBAL

import re
import sys
import subprocess

from pathlib import Path

from typing import Optional


@SakCmd("mypy", helpmsg="Execute mypy for Sak and Plugins")
def mypy() -> None:
    if SAK_GLOBAL is None:
        raise Exception("No SAK_GLOBAL defined")

    paths = []
    paths += [str(SAK_GLOBAL / "saklib")]
    for plugin in plm.getPluginList():
        if plugin.plugin_path is None:
            continue
        paths += [str(plugin.plugin_path)]

    cmd = [
        "mypy",
        "--strict",
        "--exclude",
        "python",
        "--ignore-missing-imports",
        "--show-absolute-path",
        "--pretty",
    ]

    cmd += paths

    cwd = SAK_GLOBAL
    subprocess.run(cmd, check=True, cwd=cwd)


@SakCmd("flake8", helpmsg="Execute flake8 for Sak and Plugins")
def flake8() -> None:
    if SAK_GLOBAL is None:
        raise Exception("No SAK_GLOBAL defined")

    paths = []
    paths += [str(SAK_GLOBAL / "saklib")]
    for plugin in plm.getPluginList():
        if plugin.plugin_path is None:
            continue
        paths += [str(plugin.plugin_path)]

    cmd = ["flake8"]
    cmd += paths

    cwd = SAK_GLOBAL
    subprocess.run(cmd, check=True, cwd=cwd)


@SakCmd("black", helpmsg="Execute black format for Sak and Plugins")
def black() -> None:
    if SAK_GLOBAL is None:
        raise Exception("No SAK_GLOBAL defined")

    paths = []
    paths += [str(SAK_GLOBAL / "saklib")]
    for plugin in plm.getPluginList():
        if plugin.plugin_path is None:
            continue
        paths += [str(plugin.plugin_path)]

    for path in paths:
        cmd = ["black", path]

        cwd = path
        subprocess.run(cmd, check=True, cwd=cwd)


@SakCmd("test", helpmsg="Execute tests for Sak and Plugins")
def test(coverage: bool = False, filefilter: Optional[str] = None) -> None:
    if SAK_GLOBAL is None:
        raise Exception("No SAK_GLOBAL defined")

    cmd = ["pytest"]

    if coverage:
        cmd += ["--cov-report=html", "--cov=saklib", "--cov=plugins"]

    test_files = []

    test_files += [str(x) for x in (SAK_GLOBAL / "saklib").rglob("*_test.py")]
    for plugin in plm.getPluginList():
        if plugin.plugin_path is None:
            continue
        test_files += [str(x) for x in Path(plugin.plugin_path).rglob("*_test.py")]

    filtered_files = []
    if filefilter is not None:
        for test_file in test_files:
            if filefilter in test_file:
                filtered_files.append(test_file)
    else:
        filtered_files = test_files

    cmd += filtered_files

    cwd = SAK_GLOBAL

    normalize_file_path = False
    if normalize_file_path:
        p = subprocess.Popen(
            cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        if (p.stdout is None) or (p.stderr is None):
            raise Exception('Failed to execute "%s" ' % (" ".join(cmd)))

        def convertPythonTracebackFileToNormalizeFile(line: str) -> str:
            return re.sub(r'^ *File "(.*?)", line (\d+),', r"\1:\2:", line, re.M)

        for data in p.stdout:
            sys.stdout.write(
                convertPythonTracebackFileToNormalizeFile(data.decode("utf-8"))
            )
            sys.stdout.flush()
        for data in p.stderr:
            sys.stderr.write(
                convertPythonTracebackFileToNormalizeFile(data.decode("utf-8"))
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


@SakCmd("all", helpmsg="Execute all the QA commands.")
def execute_all() -> None:
    print(80 * "=")
    print("Black")
    print(80 * "=")
    black()

    print(80 * "=")
    print("Flake8")
    print(80 * "=")
    flake8()

    print(80 * "=")
    print("Mypy")
    print(80 * "=")
    mypy()

    print(80 * "=")
    print("Unit test")
    print(80 * "=")
    test(coverage=True)

    # TODO(witt): Evaluate coverage requirements.


EXPOSE = {
    "all": execute_all,
    "mypy": mypy,
    "flake8": flake8,
    "black": black,
    "test": test,
    "coverage": {"report": coverage_report},
}

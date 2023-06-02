# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

import subprocess
import sys
from typing import Any, Callable, List, Optional, Union


def run_cmd(
    cmd: Union[List[str], str],
    check: bool = False,
    stdout: Optional[Any] = None,
    stderr: Optional[Any] = None,
    block: bool = True,
    **kwargs: Any,
) -> Union[int, Callable[[], int]]:
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
    if stdout is None:
        stdout = sys.stdout
    if stderr is None:
        stderr = sys.stderr

    if p.stdout is None:
        raise Exception('Failed to build "%s" ' % (" ".join(cmd)))
    if p.stderr is None:
        raise Exception('Failed to build "%s" ' % (" ".join(cmd)))

    def process_result() -> int:
        if p.stdout is not None and stdout is not None:
            for text in p.stdout:
                stdout.write(text.decode("utf-8"))
                stdout.flush()

        if p.stderr is not None and stderr is not None:
            for text in p.stderr:
                stderr.write(text.decode("utf-8"))
                stderr.flush()

        p.communicate()
        if check:
            if p.returncode != 0:
                cmd_str = ""
                if isinstance(cmd, str):
                    cmd_str = cmd
                if isinstance(cmd, list):
                    cmd_str = " ".join(cmd)

                raise Exception('"%s" ret core: %d' % (cmd_str, p.returncode))
        return p.returncode

    if block:
        return process_result()
    return process_result

# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

import os
import sys

from saklib.sakio import register_threaded_stdout_and_stderr_tee

STDOUT = sys.stdout
STDERR = sys.stderr

# Redirect stdout and sterr for the threads.
VERBOSE = os.environ.get("SAK_VERBOSE", False)
register_threaded_stdout_and_stderr_tee(redirect_only=(not VERBOSE))

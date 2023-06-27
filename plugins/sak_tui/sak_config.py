# -*- coding: UTF-8 -*-
"""
Simple Text user interface for SAK.
"""

from typing import List

PLUGIN_NAME = "tui"
PLUGIN_VERSION = "0.5.0"

# Specify a list of plugins that we depend and the version
DEPENDS: List[str] = []

# TODO(witt): That to put in this file?

EXPOSE_FILES = {"bash": "bash.py"}

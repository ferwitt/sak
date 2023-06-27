# -*- coding: UTF-8 -*-
"""
Plugin to interact with Sak Task abstraction.
"""

from typing import List

PLUGIN_NAME = "task"
PLUGIN_VERSION = "0.5.0"

# Specify a list of plugins that we depend and the version
DEPENDS: List[str] = []

# TODO(witt): That to put in this file?

EXPOSE_FILES = "task.py"

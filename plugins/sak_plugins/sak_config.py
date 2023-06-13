# -*- coding: UTF-8 -*-

"""
Plugin manager commands.
"""

from typing import List

PLUGIN_NAME = "plugins"
PLUGIN_VERSION = "0.3.0"

# Specify a list of plugins that we depend and the version
DEPENDS: List[str] = []

# TODO(witt): That to put in this file?

EXPOSE_FILES = "plugins.py"

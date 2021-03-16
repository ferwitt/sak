# -*- coding: UTF-8 -*-

"""
Simple webapp for SAK.
"""
from typing import List

PLUGIN_NAME = "webapp"
PLUGIN_VERSION = "0.2.2"

# Specify a list of plugins that we depend and the version
DEPENDS: List[str] = []

# TODO(witt): That to put in this file?

EXPOSE_FILES = "core.py"

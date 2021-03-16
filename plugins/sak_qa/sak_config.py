# -*- coding: UTF-8 -*-

"""
Centralized support for Quality Assurance.
"""
from typing import List

PLUGIN_NAME = "qa"
PLUGIN_VERSION = "0.2.0"

# Specify a list of plugins that we depend and the version
DEPENDS: List[str] = []

# TODO(witt): That to put in this file?

EXPOSE_FILES = "qa.py"

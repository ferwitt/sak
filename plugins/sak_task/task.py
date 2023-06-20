#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"


from saklib.sak import plm
from saklib.saktask import STORAGE


def _force_loading_plugin() -> None:
    # Force loading plugins.
    for plugin in plm.getPluginList():
        dir(plugin)


def sync() -> None:
    """Synchronize the Sak Task DB."""

    _force_loading_plugin()

    for storage_name, storage in STORAGE.items():
        storage.sync_ga()
        storage.sync_db()


EXPOSE = {
    "sync": sync,
}

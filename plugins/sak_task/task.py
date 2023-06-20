#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"


from saklib.saktask import get_storage


def sync() -> None:
    """Synchronize the Sak Task DB."""
    storage = get_storage()
    storage.sync_db()


EXPOSE = {
    "sync": sync,
}

# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

import hashlib
from typing import Any


def make_hashable(o: Any) -> Any:

    if isinstance(o, (tuple, list)):
        return tuple((make_hashable(e) for e in o))
    elif isinstance(o, dict):
        return tuple(sorted((k, make_hashable(v)) for k, v in o.items()))
    elif isinstance(o, (set, frozenset)):
        return tuple(sorted(make_hashable(e) for e in o))
    elif hasattr(o, "get_hash"):
        return tuple(o.get_hash())

    return o


def make_hash_sha256(o: Any) -> str:
    hasher = hashlib.sha256()
    hasher.update(repr(make_hashable(o)).encode())
    return hasher.hexdigest()


def make_hash_sha1(o: Any) -> str:
    hasher = hashlib.sha1()
    hasher.update(repr(make_hashable(o)).encode())
    return hasher.hexdigest()

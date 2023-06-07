"""
Sak SE commands storage abstraction.
"""
import hashlib
import io
import json
import os
import sys
import threading
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

import lazy_import  # type: ignore
from filelock import FileLock
from tqdm import tqdm  # type: ignore

from saklib.sakio import (
    get_stdout_buffer_for_thread,
    register_threaded_stdout_and_stderr_tee,
    unregister_stdout_thread_id,
)

lazy_import.lazy_module("pandas")

import pandas as pd  # type: ignore

# Store global state.
STORAGE: Dict[str, "SakStasksSotorage"] = {}
NAMESPACE: Dict[str, "SakTasksNamespace"] = {}
STDOUT = sys.stdout
STDERR = sys.stderr

# Redirect stdout and sterr for the threads.
VERBOSE = os.environ.get("SAK_VERBOSE", False)
register_threaded_stdout_and_stderr_tee(redirect_only=(not VERBOSE))


def make_hashable(o: Any) -> Any:
    if hasattr(o, "get_hash"):
        return tuple(o.get_hash())

    if isinstance(o, (tuple, list)):
        return tuple((make_hashable(e) for e in o))

    if isinstance(o, dict):
        return tuple(sorted((k, make_hashable(v)) for k, v in o.items()))

    if isinstance(o, (set, frozenset)):
        return tuple(sorted(make_hashable(e) for e in o))

    return o


def make_hash_sha1(o: Any) -> str:
    hasher = hashlib.sha1()
    hasher.update(repr(make_hashable(o)).encode())
    return hasher.hexdigest()


class SakTaskKey:
    def __init__(self, **data: Any) -> None:
        self.data = data
        self._hash_str: Optional[str] = None

    def get_hash(self) -> str:
        if self._hash_str is not None:
            return self._hash_str
        return make_hash_sha1(self.data)

    def set_hash(self, hash_str: str) -> None:
        self._hash_str = hash_str


class SakTask:
    def __init__(self, key: SakTaskKey, namespace: "SakTasksNamespace") -> None:
        self.key = key
        self.namespace = namespace

        self.lock = FileLock(str(self._get_lock_path()))

        self.key_path = self.get_key_path()
        if not self.key_path.exists():
            with open(self.key_path, "w") as f:
                json.dump(self.key.data, f, indent=2)

    def __repr__(self) -> str:
        return f"<{type(self).__name__} key={self.key.get_hash()}>"

    def __call__(self, parameter: Dict[str, Any]) -> None:
        raise Exception("You should implement this method in the specialize class")

    def get_key_path(self) -> Path:
        ret = self._get_path() / "key.json"
        return ret

    def _get_path(self) -> Path:
        key_hash = self.key.get_hash()
        ret = self.namespace.get_namespace_path() / "obj" / key_hash[:3] / key_hash
        ret.mkdir(parents=True, exist_ok=True)
        return ret

    def get_work_path(self) -> Path:
        ret = self._get_path() / "data"
        ret.mkdir(parents=True, exist_ok=True)
        return ret

    def _get_lock_path(self) -> Path:
        ret = self._get_path() / "obj.lock"
        return ret

    def get_status(self) -> str:
        with self.lock:
            status_path = self._get_path() / "status.txt"
            if status_path.exists():
                with open(status_path, "r") as f:
                    status = f.read()
                    return "success" if status == "success" else "failure"
        return "pending"

    def get_additional_data(self) -> Dict[str, Any]:
        return {}

    def has_to_rerun(self) -> bool:
        return False

    def run(self, **kwargs: Any) -> None:

        if (self.get_status() == "success") and (not self.has_to_rerun()):
            return

        with self.lock:
            with open(self._get_path() / "start_time.txt", "w") as f:
                f.write(datetime.now().isoformat())

            if VERBOSE:
                tqdm.write(
                    f"Running {type(self).__name__} {self.key.get_hash()}", file=STDOUT
                )

            # TODO(witt): This is a work around. Try to remove.
            # Make sure will start from a clean buffer.
            unregister_stdout_thread_id()

            has_error = False
            exception = None
            error_message = io.StringIO("")

            try:
                self(kwargs)
            except Exception as e:
                has_error = True
                exception = e
                traceback.print_exc(file=error_message)

                print(80 * "=")
                print(e)
                print(80 * "=")
                print(error_message.getvalue())
            finally:
                with open(self._get_path() / "log.txt", "a") as f:
                    stdout_strio = get_stdout_buffer_for_thread(threading.get_ident())
                    if stdout_strio is not None:
                        f.write(stdout_strio.getvalue())

                with open(self._get_path() / "end_time.txt", "w") as f:
                    f.write(datetime.now().isoformat())

                unregister_stdout_thread_id()

            with open(self._get_path() / "status.txt", "w") as f:
                f.write("success" if not has_error else "failure")

            if has_error:
                print(80 * "-")
                print("Found something wrong")
                print(80 * "-")
                STDERR.write(error_message.getvalue() + "\n")
                if exception is not None:
                    raise exception


class SakTasksNamespace:
    def __init__(
        self, name: str, storage: "SakStasksSotorage", param_class: Any, obj_class: Any
    ) -> None:
        self.name = name
        self.storage = storage

        self.param_class = param_class
        self.obj_class = obj_class

    def set_volatile(self) -> None:
        with open(self.get_namespace_path() / ".gitignore", "w") as f:
            f.write("*\n")

    def get_namespace_path(self) -> Path:
        ret = self.storage.get_path() / "nm" / self.name
        ret.mkdir(parents=True, exist_ok=True)
        return ret

    def get_keys(self) -> List[str]:
        return [
            x.parent.name
            for x in self.get_namespace_path().glob("obj/*/*/key.json")
            if x.exists()
        ]

    def get_task(self, hash_str: str) -> Optional[SakTask]:
        obj_path = self.get_namespace_path() / "obj" / hash_str[:3] / hash_str
        obj_key = obj_path / "key.json"

        if obj_key.exists():
            with open(obj_key, "rb") as f:
                param_obj = self.param_class(**json.load(f))
                return self.obj_class(param_obj, hash_str=hash_str)  # type: ignore

        return None

    def get_tasks(self) -> Generator[Any, None, None]:
        for key in self.get_keys():
            yield self.get_task(key)

    def get_tasks_df(self) -> pd.DataFrame:
        ret = []
        for obj in self.get_tasks():
            row = {}
            row["_key"] = obj.key.get_hash()
            row["_nm"] = self.name
            row["_obj"] = obj
            row.update(obj.key.data)
            row.update(obj.get_additional_data())
            ret.append(row)
        return pd.DataFrame(ret)


class SakStasksSotorage:
    def __init__(self, path: Path):
        self.path = Path(path)

    def get_path(self) -> Path:
        ret = self.path
        ret.mkdir(parents=True, exist_ok=True)
        return ret


def get_storage(name: str = "global") -> SakStasksSotorage:
    return STORAGE[name]


def set_storage(
    path: Path,
    name: str = "global",
) -> None:
    STORAGE[name] = SakStasksSotorage(path)
    path.mkdir(parents=True, exist_ok=True)


def register_namespace(nm_obj: "SakTasksNamespace") -> None:
    NAMESPACE[nm_obj.name] = nm_obj


def get_namespace(name: str) -> "SakTasksNamespace":
    return NAMESPACE[name]


DEFAULT_STORAGE = Path(os.environ["HOME"]) / "sak"
set_storage(name="global", path=DEFAULT_STORAGE)

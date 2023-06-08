"""
Sak SE commands storage abstraction.
"""
import enum
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
import sqlalchemy as db
from filelock import FileLock
from sqlalchemy import DateTime, Enum, String, Text
from sqlalchemy.orm import declarative_base, mapped_column, scoped_session, sessionmaker
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


Base = declarative_base()


class TaskStatus(enum.Enum):
    PENDING = 1
    ABORTED = 2
    FAIL = 3
    SUCCESS = 4


class TaskObject(Base):  # type: ignore
    __tablename__ = "tasks"

    key_hash = mapped_column(String(30), primary_key=True)

    namespace = mapped_column(String(64))

    key_data = mapped_column(Text)
    user_data = mapped_column(Text)
    log = mapped_column(Text)

    status = mapped_column(Enum(TaskStatus))
    start_time = mapped_column(DateTime)
    end_time = mapped_column(DateTime)


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

        db_obj = self.namespace.get_task_db_obj(self.key.get_hash())

        if db_obj is None:
            db_obj = TaskObject(
                key_hash=self.key.get_hash(),
                namespace=self.namespace.name,
                key_data=json.dumps(self.key.data),
                user_data="{}",
                log="",
                status=TaskStatus.PENDING,
            )
            session = self.namespace.storage.scoped_session_obj()
            session.add(db_obj)
            session.commit()
            session.flush()
            # self.namespace.storage.scoped_session_obj.remove()

        self._lock: Optional[FileLock] = None

    @property
    def lock(self) -> FileLock:
        if self._lock is None:
            self._lock = FileLock(str(self._get_lock_path()))
        return self._lock

    def __repr__(self) -> str:
        return f"<{type(self).__name__} key={self.key.get_hash()}>"

    def __call__(self, parameter: Dict[str, Any]) -> None:
        raise Exception("You should implement this method in the specialize class")

    def _get_path(self) -> Path:
        key_hash = self.key.get_hash()
        ret = self.namespace.get_namespace_path() / "obj" / key_hash[:3] / key_hash
        ret.mkdir(parents=True, exist_ok=True)
        return ret

    def get_work_path(self) -> Path:
        ret = self._get_path() / "data"
        ret.mkdir(parents=True, exist_ok=True)
        return ret

    def update_user_data(self, new_user_data: Dict[str, Any]) -> None:

        session = self.namespace.storage.scoped_session_obj()

        db_obj = self.namespace.get_task_db_obj(self.key.get_hash())
        assert db_obj is not None, f"Failed to get db_obj for {self.key.get_hash()}"

        user_data_str = db_obj.user_data
        user_data = json.loads(user_data_str)
        user_data.update(new_user_data)
        db_obj.user_data = json.dumps(user_data)

        session.commit()
        session.flush()

        # self.namespace.storage.scoped_session_obj.remove()

    def get_user_data(self) -> Dict[str, Any]:
        db_obj = self.namespace.get_task_db_obj(self.key.get_hash())
        assert db_obj is not None, f"Failed to get db_obj for {self.key.get_hash()}"

        return json.loads(db_obj.user_data)  # type: ignore

    def _get_lock_path(self) -> Path:
        ret = self._get_path() / "obj.lock"
        return ret

    def get_status(self) -> TaskStatus:
        db_obj = self.namespace.get_task_db_obj(self.key.get_hash())
        assert db_obj is not None, f"Failed to get db_obj for {self.key.get_hash()}"

        return db_obj.status  # type: ignore

    def get_additional_data(self) -> Dict[str, Any]:
        return {}

    def has_to_rerun(self) -> bool:
        return False

    def run(self, **kwargs: Any) -> None:

        if (self.get_status() == TaskStatus.SUCCESS) and (not self.has_to_rerun()):
            return

        db_obj = self.namespace.get_task_db_obj(self.key.get_hash())
        assert db_obj is not None, f"Failed to get db_obj for {self.key.get_hash()}"

        session = self.namespace.storage.scoped_session_obj()

        db_obj.start_time = datetime.now()
        session.commit()
        session.flush()

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
            stdout_strio = get_stdout_buffer_for_thread(threading.get_ident())
            if stdout_strio is not None:
                db_obj.log = stdout_strio.getvalue()
                session.commit()
                session.flush()

            db_obj.end_time = datetime.now()
            session.commit()
            session.flush()

            unregister_stdout_thread_id()

        db_obj.status = TaskStatus.SUCCESS if not has_error else TaskStatus.FAIL
        session.commit()
        session.flush()

        self.namespace.storage.scoped_session_obj.remove()

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
        pass

    def get_namespace_path(self) -> Path:
        ret = self.storage.get_path() / "nm" / self.name
        ret.mkdir(parents=True, exist_ok=True)
        return ret

    def get_keys(self) -> List[str]:
        session = self.storage.scoped_session_obj()

        with session.no_autoflush:
            query = session.query(TaskObject).filter_by(namespace=self.name)

        # self.storage.scoped_session_obj.remove()

        return [x.key_hash for x in query.all()]

    def get_task_db_obj(self, hash_str: str) -> Optional[TaskObject]:
        session = self.storage.scoped_session_obj()

        with session.no_autoflush:
            query = session.query(TaskObject).filter_by(
                namespace=self.name, key_hash=hash_str
            )

        # self.storage.scoped_session_obj.remove()

        return query.first()

    def get_task(self, hash_str: str) -> Optional[SakTask]:
        db_obj = self.get_task_db_obj(hash_str=hash_str)

        if db_obj is None:
            return None

        key_data: str = db_obj.key_data
        param_obj = self.param_class(**json.loads(key_data))
        return self.obj_class(param_obj, hash_str=hash_str)  # type: ignore

    def get_task_db_objs(self) -> List[TaskObject]:
        session = self.storage.scoped_session_obj()

        with session.no_autoflush:
            query = session.query(TaskObject).filter_by(namespace=self.name)

        # self.storage.scoped_session_obj.remove()

        return query.all()

    def get_tasks(self) -> Generator[Any, None, None]:
        for db_obj in self.get_task_db_objs():
            key_data: str = db_obj.key_data
            param_obj = self.param_class(**json.loads(key_data))
            yield self.obj_class(param_obj, hash_str=db_obj.key_hash)

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

        self.get_path()

        db_url = f"sqlite:///{self.path.resolve()}/db.sqlite"

        self.engine = db.create_engine(db_url)
        self.session_factory = sessionmaker(bind=self.engine)
        self.scoped_session_obj = scoped_session(self.session_factory)

        Base.metadata.create_all(self.engine)

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

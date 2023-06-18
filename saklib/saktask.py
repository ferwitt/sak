"""
Sak SE commands storage abstraction.
"""
import enum
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import threading
import traceback
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Generator, Iterable, List, Optional

import lazy_import  # type: ignore
import sqlalchemy as db
from filelock import FileLock
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
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
STORAGE: Dict[str, "SakTaskStorage"] = {}
NAMESPACE: Dict[str, "SakTasksNamespace"] = {}
STDOUT = sys.stdout
STDERR = sys.stderr

# Redirect stdout and sterr for the threads.
VERBOSE = os.environ.get("SAK_VERBOSE", False)
register_threaded_stdout_and_stderr_tee(redirect_only=(not VERBOSE))


Base = declarative_base()
TABLES: Dict[str, Any] = {}


class SakTaskStatus(enum.Enum):
    PENDING = 1
    ABORTED = 2
    FAIL = 3
    SUCCESS = 4


SAK_TASK_DB = "sak_tasks"


class SakTaskDb(Base):  # type: ignore
    __tablename__ = SAK_TASK_DB

    last_changed = mapped_column(String, index=True)

    key_hash = mapped_column(String(256), primary_key=True)
    namespace = mapped_column(String(64), index=True)

    status = mapped_column(Enum(SakTaskStatus), index=True)
    start_time = mapped_column(DateTime, index=True)
    end_time = mapped_column(DateTime, index=True)

    key_data = mapped_column(Text)
    user_data = mapped_column(Text)
    log = mapped_column(Text)


TABLES[SAK_TASK_DB] = SakTaskDb


def camel_to_enum(text: str) -> str:
    """Convert camel case to ENUM case.

    :param text: CamelCase text to be converted.
    :returns: The DEFINE_CASE text.
    """
    text = text[0].upper() + text[1:]
    return "_".join(re.findall("[A-Z][a-z0-9_]*", text)).upper()


def camel_to_snake(text: str) -> str:
    return camel_to_enum(text).lower()


@dataclass
class SakTaskGitAnnexData:
    key_hash: Optional[str] = None
    _key_hash: Optional[str] = None

    namespace: Optional[str] = None
    _namespace: Optional[str] = None

    status: Optional[SakTaskStatus] = None
    _status: Optional[str] = None

    start_time: Optional[datetime] = None
    _start_time: Optional[str] = None

    end_time: Optional[datetime] = None
    _end_time: Optional[str] = None

    key_data: Optional[Dict[str, Any]] = None
    _key_data: Optional[str] = None

    user_data: Optional[Dict[str, Any]] = None
    _user_data: Optional[str] = None

    log: Optional[str] = None
    _log: Optional[str] = None

    _last_changed: Optional[str] = None


def _git_annex_metadata_update_hashes(out: SakTaskGitAnnexData) -> SakTaskGitAnnexData:
    out2 = SakTaskGitAnnexData(**asdict(out))

    out2._key_hash = make_hash_sha1(out.key_hash)
    out2._namespace = make_hash_sha1(out.namespace)
    out2._status = make_hash_sha1(out.status)
    out2._start_time = make_hash_sha1(out.start_time)
    out2._end_time = make_hash_sha1(out.end_time)
    out2._key_data = make_hash_sha1(out.key_data)
    out2._user_data = make_hash_sha1(out.user_data)
    out2._log = make_hash_sha1(out.log)

    return out2


def _git_annex_parse_metadata(ga_metadata: Dict[str, Any]) -> SakTaskGitAnnexData:
    out = SakTaskGitAnnexData()

    fields = ga_metadata.get("fields")
    if fields is not None:
        out.key_hash = json.loads(fields.get("key_hash", ["null"])[0])
        out.namespace = json.loads(fields.get("namespace", ["null"])[0])
        out.key_data = json.loads(fields.get("key_data", ["null"])[0])
        out.user_data = json.loads(fields.get("user_data", ["null"])[0])

        status = json.loads(fields.get("status", ["null"])[0])
        out.status = None
        if status is not None:
            out.status = SakTaskStatus[status]

        out.log = json.loads(fields.get("log", ["null"])[0])

        start_time = fields.get("start_time", [None])[0]
        end_time = fields.get("end_time", [None])[0]

        if start_time is not None:
            out.start_time = datetime.fromisoformat(start_time)
        if end_time is not None:
            out.end_time = datetime.fromisoformat(end_time)

        out._last_changed = fields.get("lastchanged", [None])[0]
    out = _git_annex_metadata_update_hashes(out)

    return out


class SakTaskGitAnnex:
    def __init__(
        self,
        nm_obj: "SakTasksNamespace",
        data: SakTaskGitAnnexData,
        change_callback: Optional[Callable[[SakTaskGitAnnexData], None]] = None,
    ) -> None:
        self.nm_obj = nm_obj

        key_hash = data.key_hash
        assert key_hash is not None, "Cannot start with no object key"

        self.git_annex_key = key_hash

        self.set_data(data, change_callback)

    def set_data(
        self,
        data: SakTaskGitAnnexData,
        change_callback: Optional[Callable[[SakTaskGitAnnexData], None]] = None,
    ) -> SakTaskGitAnnexData:
        # TODO(witt): Maybe I should lock this thing.
        self.data = self.nm_obj.storage.ga_drv.git_annex_set_metadata(
            key=self.git_annex_key,
            data=data,
            change_callback=change_callback,
        )
        return self.data


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


def make_hash_sha256(o: Any) -> str:
    hasher = hashlib.sha256()
    hasher.update(repr(make_hashable(o)).encode())
    return hasher.hexdigest()


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

        self._hash_str = make_hash_sha256(self.data)
        return self._hash_str

    def set_hash(self, hash_str: str) -> None:
        self._hash_str = hash_str


class SakTask:
    def __init__(self, key: SakTaskKey, namespace: "SakTasksNamespace") -> None:
        self.key = key
        self.namespace = namespace

        key_hash = self.key.get_hash()

        self.ga_obj = SakTaskGitAnnex(
            nm_obj=self.namespace,
            data=SakTaskGitAnnexData(
                key_hash=key_hash,
                namespace=self.namespace.name,
                key_data=self.key.data,
            ),
        )

        session = self.namespace.storage.scoped_session_obj()

        db_obj = self.namespace.get_task_db_obj(key_hash)
        if db_obj is None:
            db_obj = SakTaskDb(
                key_hash=key_hash,
                namespace=self.namespace.name,
                status=SakTaskStatus.PENDING,
            )
            session.add(db_obj)
            session.commit()

        param_obj = self.namespace.get_task_db_param(key_hash)
        if param_obj is None:
            # TODO(witt): Extract to common function.
            supported_params: Dict[str, Any] = {}
            for k, v in key.data.items():
                if isinstance(v, int):
                    supported_params[k] = v
                elif isinstance(v, str):
                    supported_params[k] = v
                else:
                    supported_params[k] = json.dumps(v)

            param_obj = self.namespace.param_table_class(
                key_hash=key_hash,
                **supported_params,
            )
            session.add(param_obj)
            session.commit()

        self.sync_db(self.ga_obj.data)

        self._lock: Optional[FileLock] = None

    def sync_db(self, ga_data: SakTaskGitAnnexData) -> None:
        session = self.namespace.storage.scoped_session_obj()

        db_obj = self.namespace.get_task_db_obj(self.key.get_hash())

        assert (
            db_obj is not None
        ), f"Failed to get DB object for key {self.key.get_hash()}. Should it be created now?"

        # TODO(witt): What if I call the sync but there is not object yet?

        if (
            (db_obj.last_changed is None)
            or (ga_data._last_changed is None)
            or (db_obj.last_changed < ga_data._last_changed)
        ):
            db_obj.namespace = ga_data.namespace
            db_obj.status = ga_data.status
            db_obj.start_time = ga_data.start_time
            db_obj.end_time = ga_data.end_time

            # Dump addition info into cache.
            db_obj.key_data = json.dumps(ga_data.key_data)
            db_obj.user_data = json.dumps(ga_data.user_data)
            db_obj.log = json.dumps(ga_data.log)

            db_obj.last_changed = ga_data._last_changed

            session.commit()

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
        user_data = self.get_user_data()
        user_data.update(new_user_data)
        self.ga_obj.set_data(
            SakTaskGitAnnexData(user_data=user_data), change_callback=self.sync_db
        )

    def is_pending(self) -> bool:
        return self.get_status() == SakTaskStatus.PENDING

    def get_user_data(self) -> Dict[str, Any]:
        return self.ga_obj.data.user_data or {}

    def _get_lock_path(self) -> Path:
        ret = self._get_path() / "obj.lock"
        return ret

    def get_status(self) -> SakTaskStatus:
        if self.ga_obj.data.status is None:
            return SakTaskStatus.PENDING
        return self.ga_obj.data.status

    def get_additional_data(self) -> Dict[str, Any]:
        return {}

    def has_to_rerun(self) -> bool:
        return False

    def run(self, **kwargs: Any) -> None:
        # TODO(witt): Verify wrong pending status.
        if (self.get_status() != SakTaskStatus.PENDING) and (not self.has_to_rerun()):
            return

        self.ga_obj.set_data(
            SakTaskGitAnnexData(start_time=datetime.now()),
        )

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
                self.ga_obj.set_data(
                    SakTaskGitAnnexData(log=stdout_strio.getvalue()),
                )

            self.ga_obj.set_data(
                SakTaskGitAnnexData(end_time=datetime.now()),
            )

            unregister_stdout_thread_id()

        status = SakTaskStatus.SUCCESS if not has_error else SakTaskStatus.FAIL
        self.ga_obj.set_data(
            SakTaskGitAnnexData(status=status), change_callback=self.sync_db
        )

        if has_error:
            print(80 * "-")
            print("Found something wrong")
            print(80 * "-")
            STDERR.write(error_message.getvalue() + "\n")
            if exception is not None:
                raise exception


def tasks_to_df(
    objs: Iterable[SakTask], namespace: Optional[str] = None
) -> pd.DataFrame:
    ret = []
    for obj in objs:
        row: Dict[str, Any] = {}

        row["_key"] = obj.key.get_hash()

        if namespace is not None:
            row["_nm"] = namespace

        row["_obj"] = obj
        row.update(obj.key.data)
        row.update(obj.get_additional_data())
        ret.append(row)
    return pd.DataFrame(ret)


class SakTasksNamespace:
    def __init__(
        self, name: str, storage: "SakTaskStorage", param_class: Any, obj_class: Any
    ) -> None:
        self.name = name
        self.storage = storage

        self.param_class = param_class
        self.obj_class = obj_class

        self.param_name = self.obj_class.__name__
        self.param_table = camel_to_snake(self.param_name)

        if self.param_table not in TABLES:
            fields = []
            for field_name, field in self.param_class.__dataclass_fields__.items():
                field_type: Any = String
                if field.type == int:
                    field_type = Integer

                fields.append((field_name, mapped_column(field_type, index=True)))

            _parameters = {
                "__tablename__": self.param_table,
                "__table_args__": {"extend_existing": True},
                "key_hash": mapped_column(
                    ForeignKey(SAK_TASK_DB + ".key_hash"), primary_key=True
                ),
            }
            _parameters.update(dict(fields))

            self.param_table_class = type(self.param_name, (Base,), _parameters)

            TABLES[self.param_table] = self.param_table_class
        else:
            self.param_table_class = TABLES[self.param_table]

    def set_volatile(self) -> None:
        pass

    def get_namespace_path(self) -> Path:
        ret = self.storage.get_path() / "nm" / self.name
        ret.mkdir(parents=True, exist_ok=True)
        return ret

    def count_tasks(self) -> int:
        session = self.storage.scoped_session_obj()

        query = session.query(SakTaskDb.key_hash).filter_by(namespace=self.name)

        # self.storage.scoped_session_obj.remove()

        return query.count()  # type: ignore

    def get_keys(self) -> List[str]:
        session = self.storage.scoped_session_obj()

        query = session.query(SakTaskDb.key_hash).filter_by(namespace=self.name)

        # self.storage.scoped_session_obj.remove()

        return [x for x in query.all()]

    def get_task_db_param(self, hash_str: str) -> Optional[Base]:  # type: ignore
        session = self.storage.scoped_session_obj()
        ret = session.get(self.param_table_class, hash_str)
        return ret  # type: ignore

    def get_task_db_obj(self, hash_str: str) -> Optional[SakTaskDb]:
        session = self.storage.scoped_session_obj()

        ret = session.get(SakTaskDb, hash_str)
        if ret is not None:
            if ret.namespace == self.name:
                return ret  # type: ignore
        return None

    def load_from_git_annex(
        self, hash_str: str, key_data: Dict[str, Any]
    ) -> Optional[SakTask]:
        param_obj = self.param_class(**key_data)
        return self.obj_class(param_obj, hash_str=hash_str)  # type: ignore

    def get_task(self, hash_str: str) -> Optional[SakTask]:
        db_obj = self.get_task_db_obj(hash_str=hash_str)

        if db_obj is None:
            return None

        metadata = self.storage.ga_drv.git_annex_get_metada(key=db_obj.key_hash)
        param_obj = self.param_class(**metadata.key_data)
        return self.obj_class(param_obj, hash_str=hash_str)  # type: ignore

    def get_task_df(self, hash_str: str) -> pd.DataFrame:
        obj = self.get_task(hash_str=hash_str)
        if obj is None:
            return pd.DataFrame()

        return tasks_to_df([obj], namespace=self.name)

    def get_task_db_objs(
        self,
        limit: Optional[int] = None,
        query: Optional[db.sql.elements.BooleanClauseList] = None,
    ) -> List[SakTaskDb]:
        session = self.storage.scoped_session_obj()

        namespace_objs = session.query(SakTaskDb.key_hash).filter(
            SakTaskDb.namespace == self.name
        )
        _query = SakTaskDb.key_hash.in_(namespace_objs)
        if query is not None:
            _query = query  # type: ignore
        else:
            _query = session.query(SakTaskDb.key_hash).filter(
                SakTaskDb.namespace == self.name
            )

        do_query = session.query(SakTaskDb).filter(_query)

        # self.storage.scoped_session_obj.remove()
        if limit is not None:
            return do_query.limit(limit).all()  # type: ignore
        else:
            return do_query.all()  # type: ignore

    def get_tasks(
        self,
        limit: Optional[int] = None,
        query: Optional[db.sql.elements.BooleanClauseList] = None,
    ) -> Generator[Any, None, None]:
        for db_obj in self.get_task_db_objs(limit=limit, query=query):
            metadata = self.storage.ga_drv.git_annex_get_metada(key=db_obj.key_hash)
            param_obj = self.param_class(**metadata.key_data)
            yield self.obj_class(param_obj, hash_str=db_obj.key_hash)

    def get_tasks_df(
        self,
        query: Optional[db.sql.elements.BooleanClauseList] = None,
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        return tasks_to_df(
            self.get_tasks(query=query, limit=limit), namespace=self.name
        )


class SakGitAnnexDriver:
    def __init__(self, storage: "SakTaskStorage") -> None:
        self.storage = storage
        self.metada_p: Optional[subprocess.Popen[bytes]] = None

    def git_annex_get_metada(self, key: str) -> SakTaskGitAnnexData:
        return self.git_annex_set_metadata(key=key)

    def git_annex_set_metadata(
        self,
        key: str,
        data: Optional[SakTaskGitAnnexData] = None,
        change_callback: Optional[Callable[[SakTaskGitAnnexData], None]] = None,
    ) -> SakTaskGitAnnexData:
        git_annex_repo = self.storage.path

        # TODO(witt): Maybe this should be locked!!!!

        if self.metada_p is None:
            cmd = ["git", "annex", "metadata", "--json", "--batch", "--fast"]
            self.metada_p = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                cwd=git_annex_repo,
            )

        p = self.metada_p

        assert (
            (p is not None) and (p.stdin is not None) and (p.stdout is not None)
        ), f"Failed to write metadata for {key} in {str(git_annex_repo)}"

        in_data: Dict[str, Any] = {
            "key": "SHA256E-s0--" + key,
            "fields": {},
        }

        if data is not None:
            orig_data = self.git_annex_get_metada(key)

            if data.key_hash is not None:
                in_data["fields"]["key_hash"] = [json.dumps(data.key_hash)]
            if data.namespace is not None:
                in_data["fields"]["namespace"] = [json.dumps(data.namespace)]

            if data.key_data is not None:
                in_data["fields"]["key_data"] = [json.dumps(data.key_data)]
            if data.user_data is not None:
                in_data["fields"]["user_data"] = [json.dumps(data.user_data)]
            if data.start_time is not None:
                in_data["fields"]["start_time"] = [data.start_time.isoformat()]
            if data.end_time is not None:
                in_data["fields"]["end_time"] = [data.end_time.isoformat()]
            if data.status is not None:
                in_data["fields"]["status"] = [json.dumps(data.status.name)]
            if data.log is not None:
                in_data["fields"]["log"] = [json.dumps(data.log)]

            data = _git_annex_parse_metadata(in_data)

            if data.key_hash is not None:
                if orig_data._key_hash == data._key_hash:
                    in_data["fields"].pop("key_hash")

            if data.namespace is not None:
                if orig_data._namespace == data._namespace:
                    in_data["fields"].pop("namespace")
            if data.key_data is not None:
                if orig_data._key_data == data._key_data:
                    in_data["fields"].pop("key_data")
            if data.user_data is not None:
                if orig_data._user_data == data._user_data:
                    in_data["fields"].pop("user_data")
            if data.start_time is not None:
                if orig_data._start_time == data._start_time:
                    in_data["fields"].pop("start_time")
            if data.end_time is not None:
                if orig_data._end_time == data._end_time:
                    in_data["fields"].pop("end_time")
            if data.status is not None:
                if orig_data._status == data._status:
                    in_data["fields"].pop("status")
            if data.log is not None:
                if orig_data._log == data._log:
                    in_data["fields"].pop("log")

        in_data_str = json.dumps(in_data) + "\n"

        p.stdin.write(bytes(in_data_str, "utf-8"))
        p.stdin.flush()

        out_data_bytes = p.stdout.readline()
        out_data = json.loads(out_data_bytes.decode("utf-8"))

        out = _git_annex_parse_metadata(out_data)

        if in_data["fields"]:
            if change_callback is not None:
                change_callback(out)

        return out

    def close(self) -> None:
        p = self.metada_p

        if p is not None:
            assert (
                p.stdin is not None
            ), "Something went wrong, the stdin should not be None"
            p.stdin.close()
            p.wait()

        self.metada_p = None


class SakTaskStorage:
    def __init__(self, path: Path):
        self.path = Path(path)

        self.get_path()

        self.ga_drv = SakGitAnnexDriver(self)

        self._engine: Optional[db.engine.base.Engine] = None
        self._session_factory: Optional[db.orm.session.sessionmaker] = None  # type: ignore
        self._scoped_session_obj: Optional[db.orm.scoping.scoped_session] = None  # type: ignore

    def _get_current_git_hash(self) -> Optional[str]:
        bname = "git-annex"
        try:
            cmd = ["git", "log", "-1", bname]
            p = subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                cwd=self.path,
            )
            text = p.stdout.strip().decode("utf-8")
            r: List[str] = re.findall("commit ([a-f0-9]+)", text)
            if r:
                return r[0]
            else:
                return None
        except Exception as e:
            print(
                "ERROR! Failed to get the current commit. Are you in a git repository?",
                str(e),
            )
            return None

    def _get_all_keys(
        self, current_commit: str, last_commit: Optional[str] = None
    ) -> Optional[List[str]]:
        try:
            diff_hashes = ""
            if last_commit is not None:
                diff_hashes = last_commit + ".."
            diff_hashes += current_commit

            cmd = ["git", "diff", "--name-only", diff_hashes]

            p = subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                cwd=self.path,
            )
            text = p.stdout.strip().decode("utf-8")
            return [
                Path(x).name.replace("SHA256E-s0--", "").replace(".log.met", "")
                for x in text.splitlines()
                if x.endswith(".log.met")
            ]
        except Exception as e:
            print(
                "ERROR! Failed to get the current commit. Are you in a git repository?",
                str(e),
            )
            return None

    def sync_db(self) -> None:
        git_dir = self.path / ".git"
        assert (
            git_dir.exists()
        ), f"The repository ({str(git_dir)}) was not initialized yet."

        last_sync_commit_dir = git_dir / "sak"
        last_sync_commit_dir.mkdir(parents=True, exist_ok=True)

        last_sync_commit_file = last_sync_commit_dir / "LAST_SYNC_COMMIT"
        last_sync_commit_file_lock = last_sync_commit_dir / "LAST_SYNC_COMMIT.lock"

        with FileLock(str(last_sync_commit_file_lock), timeout=1):
            pass

        with FileLock(str(last_sync_commit_file_lock)):

            current_commit = self._get_current_git_hash()
            assert (
                current_commit is not None
            ), f"Failed to get current commit for git-annex branch in {str(git_dir)}."

            last_commit = None

            if last_sync_commit_file.exists():
                with open(last_sync_commit_file) as f:
                    last_commit = f.read()

            db_file = self.path.resolve() / "db.sqlite"
            if not db_file.exists():
                last_sync_commit_file.unlink()
                last_commit = None

            if last_commit != current_commit:
                pass

            all_keys = self._get_all_keys(
                current_commit=current_commit, last_commit=last_commit
            )
            if all_keys is None:
                return

            for key in tqdm(all_keys):
                metadata = self.ga_drv.git_annex_get_metada(key=key)
                if metadata.namespace is None:
                    continue

                nm_obj = NAMESPACE.get(metadata.namespace)
                if nm_obj is not None:

                    assert (
                        metadata.key_hash is not None
                    ), f"Object in namespace {metadata.namespace} has no valid key."

                    assert (
                        metadata.key_data is not None
                    ), f"Object {metadata.key_hash} in namespace {metadata.namespace} has no valid data."

                    obj = nm_obj.load_from_git_annex(
                        metadata.key_hash, metadata.key_data
                    )


            with open(last_sync_commit_file, "w") as f:
                f.write(current_commit)

    @property
    def engine(self) -> db.engine.base.Engine:
        if self._engine is None:
            self.db_connect()
        assert self._engine is not None, "Failed to create DB engine"
        return self._engine

    @property
    def session_factory(self) -> db.orm.session.sessionmaker:  # type: ignore
        if self._session_factory is None:
            self.db_connect()
        assert self._session_factory is not None, "Failed to create DB session factory"
        return self._session_factory

    @property
    def scoped_session_obj(self) -> db.orm.scoping.scoped_session:  # type: ignore
        if self._scoped_session_obj is None:
            self.db_connect()
        assert (
            self._scoped_session_obj is not None
        ), "Failed to create DB scoped session factory"
        return self._scoped_session_obj

    def db_connect(self) -> None:
        db_url = f"sqlite:///{self.path.resolve()}/db.sqlite"

        self._engine = db.create_engine(db_url, echo=False)
        self._session_factory = sessionmaker(bind=self._engine)
        self._scoped_session_obj = scoped_session(self._session_factory)

        Base.metadata.create_all(self._engine)

    def get_path(self) -> Path:
        ret = self.path
        ret.mkdir(parents=True, exist_ok=True)
        return ret


def get_storage(name: str = "global") -> SakTaskStorage:
    return STORAGE[name]


def set_storage(
    path: Path,
    name: str = "global",
) -> None:
    STORAGE[name] = SakTaskStorage(path)
    path.mkdir(parents=True, exist_ok=True)


def register_namespace(nm_obj: "SakTasksNamespace") -> None:
    NAMESPACE[nm_obj.name] = nm_obj


def get_namespace(name: str) -> "SakTasksNamespace":
    return NAMESPACE[name]


DEFAULT_STORAGE = Path(os.environ["HOME"]) / "sak"
set_storage(name="global", path=DEFAULT_STORAGE)

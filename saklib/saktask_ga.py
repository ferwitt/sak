# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

import hashlib
import json
import re
import subprocess
import sys
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import pygit2  # type: ignore

from saklib.sakhash import make_hash_sha1
from saklib.saktask_model import SakTaskStatus


def get_ga_key(key: str) -> str:
    return "SHA256E-s0--" + key


def ga_key_to_key_file(key: str) -> str:
    x = get_ga_key(key)
    hasher = hashlib.md5()
    hasher.update(x.encode("utf-8"))
    y = hasher.hexdigest()

    ret = y[0:3] + "/" + y[3:6] + "/" + x + ".log.met"
    return ret


def ga_key_file_to_key(key_file: str) -> str:
    return Path(key_file).name.replace("SHA256E-s0--", "").replace(".log.met", "")


@dataclass
class SakTaskGitAnnexDataHashes:
    _key_hash: Optional[str] = None
    _namespace: Optional[str] = None
    _status: Optional[str] = None
    _start_time: Optional[str] = None
    _end_time: Optional[str] = None
    _key_data: Optional[str] = None
    _user_data: Optional[str] = None
    _log: Optional[str] = None


@dataclass
class SakTaskGitAnnexData:
    key_hash: Optional[str] = None
    namespace: Optional[str] = None
    status: Optional[SakTaskStatus] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    key_data: Optional[Dict[str, Any]] = None
    user_data: Optional[Dict[str, Any]] = None
    log: Optional[str] = None

    _last_changed: Optional[str] = None
    _hashes: Optional[SakTaskGitAnnexDataHashes] = None

    def get_annex_hash(self) -> str:
        assert self.key_hash is not None, f"The key hash is not set for {str(self)}"
        return get_ga_key(self.key_hash)

    def get_hash(self, ga_drv: "SakGitAnnexDriver") -> Optional[str]:
        assert (
            self.key_hash is not None
        ), f"It is not possible to calculate the metadata hash for {self}. Make sure the key_hash value is set."
        return ga_drv.ga_key_metadata_hash(key=self.key_hash)

    def get_metadata_hashes(self) -> SakTaskGitAnnexDataHashes:
        ret = SakTaskGitAnnexDataHashes()

        ret._key_hash = make_hash_sha1(self.key_hash)
        ret._namespace = make_hash_sha1(self.namespace)
        ret._status = make_hash_sha1(self.status)
        ret._start_time = make_hash_sha1(self.start_time)
        ret._end_time = make_hash_sha1(self.end_time)
        ret._key_data = make_hash_sha1(self.key_data)
        ret._user_data = make_hash_sha1(self.user_data)
        ret._log = make_hash_sha1(self.log)

        return ret


def git_annex_parse_metadata(ga_metadata: Dict[str, Any]) -> SakTaskGitAnnexData:
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

    out._hashes = out.get_metadata_hashes()

    return out


class SakGitAnnexDriver:
    def __init__(self, repo_path: Path) -> None:
        self.repo_path = repo_path
        self.repo = pygit2.Repository(self.repo_path)
        self.metada_p: Optional[subprocess.Popen[bytes]] = None

    def ga_key_metadata_hash(self, key: str) -> Optional[str]:
        fname = ga_key_to_key_file(key)

        content: Optional[bytes] = None

        journal = (
            self.repo_path / ".git" / "annex" / "journal" / fname.replace("/", "_")
        )
        if journal.exists():
            with open(journal, "rb") as f:
                content = f.read()

            hasher = hashlib.sha1()
            hasher.update(b"Blob " + f"{len(content)}".encode() + b"\0" + content)
            return hasher.hexdigest()
        else:
            return self.git_annex_get_path_blob(fname)

        raise Exception(f"Failed to get content for metadata {key}")

    def git_annex_get_metada(self, key: str) -> SakTaskGitAnnexData:
        return self.git_annex_set_metadata(key=key)

    def git_annex_get_path_blob(self, path: str) -> Optional[str]:
        commit = self.repo.revparse_single("git-annex")
        tree = commit.tree
        blob_id = None

        for part in path.split("/"):
            if not part:
                continue

            if part not in tree:
                return None

            entry = tree[part]
            if entry.filemode == pygit2.GIT_FILEMODE_TREE:
                tree = self.repo[entry.oid]
            elif entry.filemode == pygit2.GIT_FILEMODE_BLOB:
                blob_id = entry.oid
            else:
                raise ValueError(
                    f"Invalid filemode for path part {part}: {entry.filemode}"
                )
        if blob_id is None:
            raise ValueError(f"Blob not found for path: {path}")

        blob = self.repo[blob_id]
        blob_hash = blob.hex
        return blob_hash  # type: ignore

    def git_annex_drop_key(self, key: str) -> None:
        git_annex_repo = self.repo_path
        key_str = get_ga_key(key)

        cmd = ["git", "annex", "metadata", "--json", "--key", key_str, "--remove-all"]

        p = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            cwd=git_annex_repo,
            check=True,
        )

        assert (p is not None) and (
            p.stdout is not None
        ), f"Failed to remove metadata for {key} in {str(git_annex_repo)}"

    def git_annex_set_metadata(
        self,
        key: str,
        data: Optional[SakTaskGitAnnexData] = None,
        change_callback: Optional[Callable[[SakTaskGitAnnexData], None]] = None,
    ) -> SakTaskGitAnnexData:
        git_annex_repo = self.repo_path

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
            "key": get_ga_key(key),
            "fields": {},
        }

        # import pdb; pdb.set_trace()
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

            data = git_annex_parse_metadata(in_data)

            if (orig_data._hashes is not None) and (data._hashes is not None):
                if data.key_hash is not None:
                    if orig_data._hashes._key_hash == data._hashes._key_hash:
                        in_data["fields"].pop("key_hash")

                if data.namespace is not None:
                    if orig_data._hashes._namespace == data._hashes._namespace:
                        in_data["fields"].pop("namespace")
                if data.key_data is not None:
                    if orig_data._hashes._key_data == data._hashes._key_data:
                        in_data["fields"].pop("key_data")
                if data.user_data is not None:
                    if orig_data._hashes._user_data == data._hashes._user_data:
                        in_data["fields"].pop("user_data")
                if data.start_time is not None:
                    if orig_data._hashes._start_time == data._hashes._start_time:
                        in_data["fields"].pop("start_time")
                if data.end_time is not None:
                    if orig_data._hashes._end_time == data._hashes._end_time:
                        in_data["fields"].pop("end_time")
                if data.status is not None:
                    if orig_data._hashes._status == data._hashes._status:
                        in_data["fields"].pop("status")
                if data.log is not None:
                    if orig_data._hashes._log == data._hashes._log:
                        in_data["fields"].pop("log")

        in_data_str = json.dumps(in_data) + "\n"

        p.stdin.write(bytes(in_data_str, "utf-8"))
        p.stdin.flush()

        out_data_bytes = p.stdout.readline()
        out_data = json.loads(out_data_bytes.decode("utf-8"))

        out = git_annex_parse_metadata(out_data)

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

    def get_current_git_hash(self) -> Optional[str]:
        bname = "git-annex"
        try:
            cmd = ["git", "log", "-1", bname]
            p = subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                cwd=self.repo_path,
            )
            text = p.stdout.strip().decode("utf-8")
            r: List[str] = re.findall("commit ([a-f0-9]+)", text)
            if r:
                return r[0]
            else:
                return None
        except Exception as e:
            print(80 * "-")
            traceback.print_exc(file=sys.stdout)
            print(80 * "-")
            print(
                "ERROR! Failed to get the current commit. Are you in a git repository?",
                str(e),
            )
            return None

    def get_all_keys(
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
                cwd=self.repo_path,
            )
            text = p.stdout.strip().decode("utf-8")
            return [
                ga_key_file_to_key(x)
                for x in text.splitlines()
                if x.endswith(".log.met")
            ]
        except Exception as e:
            print(80 * "-")
            traceback.print_exc(file=sys.stdout)
            print(80 * "-")
            print(
                "ERROR! Failed to get the current commit. Are you in a git repository?",
                str(e),
            )
            return None

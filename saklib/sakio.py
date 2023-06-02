# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"


import sys
import threading
from datetime import datetime
from io import StringIO, TextIOWrapper  # for Python 3
from typing import Dict, Optional


class SakThreadedTee(TextIOWrapper):
    def __init__(self, stream: TextIOWrapper, redirect_only: bool = False) -> None:
        self.thread_buffer: Dict[int, StringIO] = {}
        self.stream = stream
        self.redirect_only = redirect_only

        self._threaded_tee_lock = threading.Lock()

    def write(self, message: str) -> int:
        is_main_thread = threading.current_thread() is threading.main_thread()
        timestamp = datetime.now().strftime(
            "[%m/%d/%Y %H:%M:%S] "
        )  # current date and time

        ret = 0

        def _write_new_msg(tm: str) -> int:
            ret = 0
            if not self.redirect_only or is_main_thread:
                ret = self.stream.write(tm)
            else:
                ret = len(tm)

            with self._threaded_tee_lock:
                current_thread = threading.get_ident()
                if current_thread not in self.thread_buffer:
                    self.thread_buffer[current_thread] = StringIO()

                # TODO(witt): Write only the ret bytes to the stringio?
                self.thread_buffer[current_thread].write(tm)
            return ret

        if is_main_thread:
            ret += _write_new_msg(message)
        else:
            for line in message.splitlines():
                tm = timestamp + line + "\n"
                ret += _write_new_msg(tm)

        return ret

    def flush(self) -> None:
        is_main_thread = threading.current_thread() is threading.main_thread()
        if not self.redirect_only or is_main_thread:
            self.stream.flush()

    def get_thread_buffer(self, thread_id: int) -> Optional[StringIO]:
        with self._threaded_tee_lock:
            if thread_id in self.thread_buffer:
                return self.thread_buffer[thread_id]
        return None

    def unregister_thread_id(self, thread_id: int) -> None:
        with self._threaded_tee_lock:
            if thread_id in self.thread_buffer:
                self.thread_buffer.pop(thread_id)


def _get_stream_buffer_for_thread(
    stream: TextIOWrapper, thread_id: Optional[int] = None
) -> Optional[StringIO]:
    if thread_id is None:
        thread_id = threading.get_ident()
    if isinstance(stream, SakThreadedTee):
        return stream.get_thread_buffer(thread_id)
    return None


def _unregister_threaded_tee(
    stream: TextIOWrapper, thread_id: Optional[int] = None
) -> None:
    if thread_id is None:
        thread_id = threading.get_ident()

    if isinstance(stream, SakThreadedTee):
        stream.unregister_thread_id(thread_id)


def register_threaded_stdout_tee() -> None:
def register_threaded_stdout_tee(redirect_only: bool = False) -> None:
    if not isinstance(sys.stdout, SakThreadedTee):
        # TODO(witt): Check if the stdout should inherit TextIOWrapper.
        sys.stdout = SakThreadedTee(sys.stdout, redirect_only=redirect_only)  # type: ignore


def register_threaded_stderr_tee(redirect_only: bool = False) -> None:
    if not isinstance(sys.stderr, SakThreadedTee):
        # TODO(witt): Check if the stdout should inherit TextIOWrapper.
        sys.stderr = SakThreadedTee(sys.stderr, redirect_only=redirect_only)  # type: ignore


def get_stdout_buffer_for_thread(thread_id: Optional[int] = None) -> Optional[StringIO]:
    return _get_stream_buffer_for_thread(sys.stdout, thread_id)  # type: ignore


def get_stderr_buffer_for_thread(thread_id: Optional[int] = None) -> Optional[StringIO]:
    return _get_stream_buffer_for_thread(sys.stderr, thread_id)  # type: ignore


def unregister_stdout_thread_id(thread_id: Optional[int] = None) -> None:
    _unregister_threaded_tee(sys.stdout, thread_id)  # type: ignore


def unregister_stderr_thread_id(thread_id: Optional[int] = None) -> None:
    _unregister_threaded_tee(sys.stderr, thread_id)  # type: ignore

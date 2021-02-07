# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"


import sys
from io import StringIO, TextIOWrapper  ## for Python 3
import threading

from typing import Dict, Optional


class SakThreadedTee(TextIOWrapper):
    def __init__(self, stream: TextIOWrapper) -> None:
        self.thread_buffer: Dict[int, StringIO] = {}
        self.stream = stream

        self._threaded_tee_lock = threading.Lock()

    def write(self, message: str) -> int:
        ret = self.stream.write(message)

        with self._threaded_tee_lock:
            current_thread = threading.get_ident()
            if current_thread not in self.thread_buffer:
                self.thread_buffer[current_thread] = StringIO()

            #TODO(witt): Write only the ret bytes to the stringio?
            self.thread_buffer[current_thread].write(message)
        return ret

    def flush(self) -> None:
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


def _get_stream_buffer_for_thread(stream: TextIOWrapper, thread_id: Optional[int] = None) -> Optional[StringIO]:
    if thread_id is None:
        thread_id = threading.get_ident()
    if isinstance(stream, SakThreadedTee):
        return stream.get_thread_buffer(thread_id)
    return None


def _unregister_threaded_tee(stream: TextIOWrapper, thread_id: Optional[int] = None) -> None:
    if thread_id is None:
        thread_id = threading.get_ident()

    if isinstance(stream, SakThreadedTee):
        stream.unregister_thread_id(thread_id)


def register_threaded_stdout_tee() -> None:
    if not isinstance(sys.stdout, SakThreadedTee):
        #TODO(witt): Check if the stdout should inherit TextIOWrapper.
        sys.stdout = SakThreadedTee(sys.stdout) #type: ignore


def register_threaded_stderr_tee() -> None:
    if not isinstance(sys.stderr, SakThreadedTee):
        #TODO(witt): Check if the stdout should inherit TextIOWrapper.
        sys.stderr = SakThreadedTee(sys.stderr) #type: ignore


def get_stdout_buffer_for_thread(thread_id: Optional[int] = None) -> Optional[StringIO]:
    return _get_stream_buffer_for_thread(sys.stdout, thread_id) #type: ignore


def get_stderr_buffer_for_thread(thread_id: Optional[int] = None) -> Optional[StringIO]:
    return _get_stream_buffer_for_thread(sys.stderr, thread_id) #type: ignore


def unregister_stdout_thread_id(thread_id: Optional[int] = None) -> None:
    _unregister_threaded_tee(sys.stdout, thread_id) #type: ignore


def unregister_stderr_thread_id(thread_id: Optional[int] = None) -> None:
    _unregister_threaded_tee(sys.stderr, thread_id) #type: ignore

# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"


import sys
from io import StringIO  ## for Python 3
import threading


class SakThreadedTee:
    def __init__(self, stream):
        self.thread_buffer = {}
        self.stream = stream

        self._threaded_tee_lock = threading.Lock()

    def write(self, message):
        self.stream.write(message)

        with self._threaded_tee_lock:
            current_thread = threading.get_ident()
            if current_thread not in self.thread_buffer:
                self.thread_buffer[current_thread] = StringIO()
            self.thread_buffer[current_thread].write(message)

    def flush(self):
        self.stream.flush()

    def get_thread_buffer(self, thread_id):
        with self._threaded_tee_lock:
            if thread_id in self.thread_buffer:
                return self.thread_buffer[thread_id]
        return None

    def unregister_thread_id(self, thread_id):
        with self._threaded_tee_lock:
            if thread_id in self.thread_buffer:
                self.thread_buffer.pop(thread_id)


def _get_stream_buffer_for_thread(stream, thread_id=None):
    if thread_id is None:
        thread_id = threading.get_ident()
    if isinstance(stream, SakThreadedTee):
        return stream.get_thread_buffer(thread_id)


def _unregister_threaded_tee(stream, thread_id=None):
    if thread_id is None:
        thread_id = threading.get_ident()

    if isinstance(stream, SakThreadedTee):
        stream.unregister_thread_id(thread_id)


def register_threaded_stdout_tee():
    if not isinstance(sys.stdout, SakThreadedTee):
        sys.stdout = SakThreadedTee(sys.stdout)


def register_threaded_stderr_tee():
    if not isinstance(sys.stderr, SakThreadedTee):
        sys.stderr = SakThreadedTee(sys.stderr)


def get_stdout_buffer_for_thread(thread_id=None):
    return _get_stream_buffer_for_thread(sys.stdout, thread_id)


def get_stderr_buffer_for_thread(thread_id=None):
    return _get_stream_buffer_for_thread(sys.stderr, thread_id)


def unregister_stdout_thread_id(thread_id=None):
    return _unregister_threaded_tee(sys.stdout, thread_id)


def unregister_stderr_thread_id(thread_id=None):
    return _unregister_threaded_tee(sys.stderr, thread_id)

#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

import threading
import time
from functools import partial
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Union

import bokeh
import panel as pn
import param  # type: ignore
import tornado
import tornado.gen

from saklib.sak import ctx
from saklib.sakio import (
    get_stdout_buffer_for_thread,
    unregister_stderr_thread_id,
    unregister_stdout_thread_id,
)
from saklib.sakplugin import load_file

has_pandas = False
try:
    pass

    has_pandas = True
except Exception as e:
    print("WARNING! Failed to import pandas", str(e))


SCRIPT_PATH = Path(__file__).resolve()
RESOURCES_PATH = SCRIPT_PATH.parent / "web"


class WebAppCbObj:
    def __init__(
        self,
        doc: bokeh.document.document.Document,
        cb: Callable[[], Union[pn.pane.PaneBase, Dict[str, pn.pane.PaneBase]]],
    ) -> None:
        self.doc = doc
        self.cb = cb

        self.stdout = pn.pane.Str("", sizing_mode="stretch_both")

        self.thread: Optional[threading.Thread] = None

        self.main_output = pn.Column(sizing_mode="stretch_both")
        self.side_output = pn.Column(sizing_mode="stretch_both")
        self.modal_output = pn.Column(sizing_mode="stretch_both")

    def main_view(self) -> pn.Column:
        return self.main_output

    def side_view(self) -> pn.Column:
        return self.side_output

    def modal_view(self) -> pn.Column:
        return self.modal_output

    @tornado.gen.coroutine
    def update_doc(
        self,
        new_main_output: Optional[pn.pane.PaneBase] = None,
        new_side_output: Optional[pn.pane.PaneBase] = None,
        new_modal_output: Optional[pn.pane.PaneBase] = None,
    ) -> None:
        # TODO(witt): This coroutine is the one that will actually update the content
        if new_main_output is not None:
            self.main_output.clear()
            self.main_output.append(new_main_output)

        if new_side_output is not None:
            self.side_output.clear()
            self.side_output.append(new_side_output)

        if new_modal_output is not None:
            self.modal_output.clear()
            self.modal_output.append(new_modal_output)

    @tornado.gen.coroutine
    def update_stdout(self, stdout_str: str) -> None:
        # TODO(witt): This coroutine is the one that will actually update the content
        # print(stdout_str)
        self.stdout.object = stdout_str

    def start_callback(self) -> None:
        # Start thread in another callback.
        self.thread = threading.Thread(target=self.callback)
        self.thread.start()

    def callback(self, **vargs: Any) -> None:
        # TODO: Get from my resources here
        loading_spinner = pn.indicators.LoadingSpinner(
            value=True, width=100, height=100
        )
        loading = pn.Row(
            loading_spinner,
            pn.Column(pn.pane.Str("stdout:"), self.stdout),
        )

        self.doc.add_next_tick_callback(
            partial(
                self.update_doc,
                new_main_output=loading,
                new_side_output=None,
                new_modal_output=None,
            )  # type: ignore
        )

        # TODO(witt): This is a work around. Try to remove.
        # Make sure will start from a clean buffer.
        unregister_stdout_thread_id()

        new_output: Dict[str, Any] = {}
        error_main: Optional[pn.pane.PaneBase] = None

        try:
            # Start a thread to update the stdout every 1s
            do_update_stdout = True

            def simple_update_stdout() -> None:
                UPDATE_PERIOD = 2
                # MAX_SIZE = -1
                MAX_SIZE = 10 * 1024
                while do_update_stdout:
                    if self.thread is None:
                        raise Exception("Thread was not set")

                    stdout_strio = get_stdout_buffer_for_thread(self.thread.ident)
                    stdout_str = ""

                    if stdout_strio is not None:
                        stdout_str = stdout_strio.getvalue()[-MAX_SIZE:]

                    if self.stdout.object != stdout_str:
                        self.doc.add_next_tick_callback(
                            partial(self.update_stdout, stdout_str=stdout_str)  # type: ignore
                        )
                    if do_update_stdout:
                        time.sleep(UPDATE_PERIOD)

            update_stdout_thread = threading.Thread(target=simple_update_stdout)
            update_stdout_thread.start()

            # This is running in another thread.
            # Run callback code.
            _new_output = self.cb()
            if isinstance(_new_output, dict):
                new_output = _new_output
            else:
                new_output = {"main": _new_output}

            # Stop the update thread
            do_update_stdout = False

            # Will not joing to allow a bigger sleep :)
            # update_stdout_thread.join()
        except Exception as e:
            _error_main = pn.Column()
            _error_message = f"ERROR: {str(e)}"
            _error_main.append(
                pn.pane.Alert(
                    _error_message.format(alert_type="danger"), alert_type="danger"
                )
            )

            import traceback
            from io import StringIO

            trace = StringIO()
            traceback.print_exc(file=trace)
            print(trace.getvalue())
            trace_str = f"```python\n{trace.getvalue()}\n```"
            _error_main.append(pn.pane.Markdown(trace_str, sizing_mode="stretch_width"))

            error_main = pn.Column(
                _error_main,
                pn.Column(pn.pane.Str("stdout:"), self.stdout),
            )

        finally:
            # Schedule document update into tornado
            stdout_strio = get_stdout_buffer_for_thread()
            if stdout_strio is not None:
                stdout_strio.getvalue()

            self.doc.add_next_tick_callback(
                partial(
                    self.update_doc,
                    new_main_output=error_main or new_output.get("main"),
                    new_side_output=new_output.get("side"),
                    new_modal_output=new_output.get("modal"),
                )  # type: ignore
            )

            # Clean the thread buffers.
            unregister_stdout_thread_id()
            unregister_stderr_thread_id()

        # TODO(witt): Should I do some thread cleaning?


class SakDoc(param.Parameterized):  # type: ignore
    def __init__(self, doc: bokeh.document.document.Document) -> None:
        self.doc = doc
        super().__init__()

        args = self.doc.session_context.request.arguments  # type: ignore

        self.args = {}
        for k, v in args.items():
            self.args[k] = v[0].decode("utf-8")

        path = ""
        try:
            path = args["path"][0].decode("utf-8")
        except Exception as e:
            print("ERROR! Failed to get the path from the document.", str(e))
        # Filter empty fields
        self._args = [x for x in path.split("/") if x]

    def server_doc(self) -> bokeh.document.document.Document:
        tmpl = pn.template.MaterialTemplate(
            title="Sak",
            favicon=str(RESOURCES_PATH / "static/sak_white.png"),
            header_background="#000000",
            logo=str(RESOURCES_PATH / "static/sak_white.png"),
            site_name="Sak",
            sidebar_width=200,
        )

        toc_md = ""
        toc_md += "[HOME &#127968;](./)\n\n"

        # Expose links to the web expose plugins.
        plugins_url = ""
        subcmds_md = ""
        if "webapp" in ctx.plugin_data:
            wac = ctx.plugin_data["webapp"]
            urls = {}
            for name, path, _, _, _ in wac.panel_register_cbs:
                if name not in urls:
                    urls[name] = path

            if urls:
                subcmds_md += """
        ---
        ## Plugins

        """
            for name, path in urls.items():
                subcmds_md += f"""
        [{name.upper()}](./?name={name}&path={path})
        """
                plugins_url += f"""
                <a href="./?name={name}&path={path}">{name.upper()}</a>
                """

        # Handle the page as an exposed web.
        if "webapp" in ctx.plugin_data:
            wac = ctx.plugin_data["webapp"]

            for name, path, file_path, callback, tmplmod in wac.panel_register_cbs:
                cb_name = callback if isinstance(callback, str) else callback.__name__
                cb = load_file(file_path)[cb_name]

                if name != self.args.get("name"):
                    continue
                _path = [x for x in path.split("/") if x]
                if "/".join(self._args) != "/".join(_path):
                    continue

                controller = pn.Column(
                    pn.pane.Markdown(toc_md, sizing_mode="stretch_width"),
                    pn.pane.Markdown(subcmds_md, sizing_mode="stretch_width"),
                    sizing_mode="stretch_both",
                )
                tmpl.header.append(pn.pane.HTML(plugins_url))
                tmpl.sidebar.append(controller)

                if tmplmod is not None:
                    tmpl = load_file(file_path)[tmplmod](tmpl)

                def internal_callback() -> Union[
                    Dict[str, pn.pane.PaneBase], pn.pane.PaneBase
                ]:
                    return cb(self.doc, tmpl=tmpl, **self.args)  # type: ignore

                content = WebAppCbObj(self.doc, internal_callback)

                tmpl.main.append(content.main_view())
                tmpl.sidebar.append(content.side_view())
                tmpl.modal.append(content.modal_view())

                ret = tmpl.server_doc(self.doc)

                content.start_callback()

                return ret

        main_msg = """
        # Sak

        Group everyday developer's tools in a swiss-army-knife command

        **Select one of the plugins**
        """

        tmpl.main.append(pn.pane.Markdown(main_msg))

        controller = pn.Column(
            pn.pane.Markdown(toc_md, sizing_mode="stretch_width"),
            pn.pane.Markdown(subcmds_md, sizing_mode="stretch_width"),
            sizing_mode="stretch_both",
        )
        tmpl.sidebar.append(controller)

        # Callback that will be called when the About button is clicked
        about = pn.pane.Markdown(
            """
        # About

        Sak is developed by Fernando Witt.
        """
        )

        tmpl.modal.append(about)

        def about_callback(event: param.parameterized.Event) -> None:
            tmpl.open_modal()

        btn = pn.widgets.Button(name="About", width=150)
        btn.on_click(about_callback)
        tmpl.sidebar.append(btn)

        ret = tmpl.server_doc(self.doc)
        return ret

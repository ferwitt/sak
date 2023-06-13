#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

from pathlib import Path

import bokeh
import panel as pn
import param  # type: ignore

from saklib.sak import ctx
from saklib.sakplugin import load_file

has_pandas = False
try:
    pass

    has_pandas = True
except Exception as e:
    print("WARNING! Failed to import pandas", str(e))


SCRIPT_PATH = Path(__file__).resolve()
RESOURCES_PATH = SCRIPT_PATH.parent / "web"


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
            for name, path, _, _ in wac.panel_register_cbs:
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

            for name, path, file_path, callback in wac.panel_register_cbs:
                cb = load_file(file_path)[callback.__name__]

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

                tmpl = cb(self.doc, tmpl, **self.args)

                ret = tmpl.server_doc(self.doc)

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

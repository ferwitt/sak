#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

import ctypes
import os
import threading
import time
from functools import partial
from pathlib import Path
from typing import Any, Dict, List, Optional

import bokeh
import panel as pn
import param
import tornado
import tornado.gen

from saklib.sak import root_cmd
from saklib.sakcmd import SakArg, SakCmd, SakCompleterArg, sak_arg_parser
from saklib.sakio import (
    get_stdout_buffer_for_thread,
    unregister_stderr_thread_id,
    unregister_stdout_thread_id,
)

has_pandas = False
try:
    import pandas as pd

    has_pandas = True
except Exception as e:
    print("WARNING! Failed to import pandas", str(e))


SCRIPT_PATH = Path(__file__).resolve()
RESOURCES_PATH = SCRIPT_PATH.parent / "web"

template = """
{%% extends base %%}
<!-- goes in body -->
{%% block contents %%}
{%% set context = '%s' %%}
{%% if context == 'notebook' %%}
    {%% set slicer_id = get_id() %%}
    <div id='{{slicer_id}}'></div>
{%% endif %%}

<script>
var config = {
    settings: {
        hasHeaders: false,
        constrainDragToContainer: true,
        reorderEnabled: true,
        selectionEnabled: false,
        popoutWholeStack: false,
        blockedPopoutsThrowError: true,
        closePopoutsOnUnload: true,
        showPopoutIcon: false,
        showMaximiseIcon: false,
        showCloseIcon: false
    },
    content: [{
        type: 'row',
        content:[
            {
                type : 'column',
                content: [
                {
                    type: 'component',
                    componentName: 'view',
                    componentState: { model: '{{ embed(roots.controller) }}',
                                      title: 'Controls',
                                      width: 350,
                                      css_classes:['scrollable']},
                    isClosable: false,
                    width: 20,
                },
                {
                    type: 'component',
                    componentName: 'view',
                    componentState: { model: '{{ embed(roots.parameters) }}',
                                      title: 'Parameters',
                                      width: 350,
                                      css_classes:['scrollable']},
                    isClosable: false,
                    width: 20,
                }],
                width: 20
            },
            {
                type : 'column',
                content: [
                {
                    type: 'component',
                    componentName: 'view',
                    componentState: { model: '{{ embed(roots.content) }}',
                                      title: 'Content',
                                      css_classes:['scrollable']},
                    isClosable: false,
                },
                {
                    type: 'component',
                    componentName: 'view',
                    componentState: { model: '{{ embed(roots.stdout) }}',
                                      title: 'Stdout',
                                      css_classes:['scrollable']},
                    isClosable: false,
                    height: 25,
                }
                ]
            }
        ]
    }]
};

var myLayout;
var savedState = localStorage.getItem( 'savedLayout' );

if( false && savedState !== null ) {
    var savedStateObj = JSON.parse( savedState );
    savedStateObj.content[0].content[0].content[0].componentState.model = '{{ embed(roots.controller) }}';
    savedStateObj.content[0].content[0].content[1].componentState.model = '{{ embed(roots.parameters) }}';
    savedStateObj.content[0].content[1].content[0].componentState.model = '{{ embed(roots.content) }}';
    savedStateObj.content[0].content[1].content[1].componentState.model = '{{ embed(roots.stdout) }}';
    myLayout = new GoldenLayout( savedStateObj );
} else {
{%% if context == 'notebook' %%}
    myLayout = new GoldenLayout( config, '#' + '{{slicer_id}}' );
    $('#' + '{{slicer_id}}').css({width: '100%%', height: '800px', margin: '0px'})
{%% else %%}
    myLayout = new GoldenLayout( config );
{%% endif %%}
}

//myLayout.on( 'stateChanged', function(){
//    console.log("Update state");
//    var state = JSON.stringify( myLayout.config );
//    localStorage.setItem( 'savedLayout', state );
//});

myLayout.registerComponent('view', function( container, componentState ){
    const {width, css_classes} = componentState
    if(width)
      container.on('open', () => container.setSize(width, container.height))
    if (css_classes)
      css_classes.map((item) => container.getElement().addClass(item))
    container.setTitle(componentState.title)
    container.getElement().html(componentState.model);
    container.on('resize', () => window.dispatchEvent(new Event('resize')))
});

myLayout.init();
</script>
{%% endblock %%}
"""


class StopableThread(threading.Thread):
    def get_id(self) -> Optional[int]:
        # returns id of the respective thread
        # if hasattr(self, '_thread_id'):
        #    return self._thread_id
        for thread_id, thread in threading._active.items():  # type: ignore
            if thread is self:
                return thread_id  # type: ignore
        return None

    def raise_exception(self) -> None:
        print("Raise exception")
        thread_id = self.get_id()
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(
            thread_id, ctypes.py_object(SystemExit)
        )
        if res > 1:
            ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, 0)
            print("Exception raise failure")


class SakWebCmdArg:
    def __init__(self, arg: SakArg):
        self.arg = arg

    # TODO(witt): Maybe I can populate the arg defaults with what comes from the get params?
    # TODO(witt): What is the type of request?
    def getAsDict(self, request: Optional[Any] = None) -> Dict[str, Any]:
        action = self.arg.vargs.get("action", "")
        default = self.arg.vargs.get("default", None)
        choices = list(self.arg.vargs.get("choices", []))
        arg_type = self.arg.vargs.get("type", None)
        nargs = self.arg.vargs.get("nargs", None)

        # Work around for list
        if nargs is not None:
            if nargs in ["*", "+"]:
                arg_type = list

        if arg_type is None:
            if action in ["store_true", "store_false"]:
                arg_type = bool
            if action in ["append"] or nargs in ["*", "+"]:
                arg_type = list

        if default is None:
            if action == "store_true":
                default = False
            elif action == "store_false":
                default = True

        type_lut = {
            bool: "bool",
            str: "string",
            list: "list",
            int: "int",
            float: "float",
        }

        # TODO(witt): Should I override the default or give another value?
        request_default = None
        if request is not None:
            request_default = request.json.get(self.arg.name, None)

        ret: Dict[str, Any] = {
            "name": self.arg.name,
            "help": self.arg.helpmsg,
            "type": type_lut.get(arg_type, "string"),
            "default": request_default or default,
            "choices": choices,
            "nargs": nargs,
            "action": action,
        }
        # ret.update(self.vargs)
        return ret

    def getRequestArgList(self, request: Dict[str, Any]) -> List[str]:
        type_lut = {
            "bool": bool,
            "string": str,
            "list": list,
            "int": int,
            "float": float,
        }
        cfg = self.getAsDict()

        name = cfg["name"]
        arg_type = type_lut.get(cfg["type"], "string")
        arg_action = cfg["action"]

        req_arg = request.get(name, None)

        ret = []

        if req_arg is not None:
            if arg_type is list:
                tmp_ret = []
                tmp_ret.append("--%s" % name)

                tmp_ret_value = []

                if isinstance(req_arg, list):
                    tmp_ret_value += req_arg
                elif isinstance(req_arg, str):
                    if req_arg.strip():
                        if "\n" in req_arg:
                            tmp_ret_value += req_arg.split("\n")
                        else:
                            tmp_ret_value += req_arg.split(",")
                else:
                    raise Exception("No known way of handling list parameter")

                if tmp_ret_value:
                    ret += tmp_ret
                    ret += tmp_ret_value

            else:
                if arg_type is bool:
                    if "store_true" == arg_action:
                        if req_arg not in ["yes", "true", "1", True]:
                            return []
                    if "store_false" == arg_action:
                        if req_arg not in ["false", "no", "0", False]:
                            return []
                else:
                    if req_arg == "":
                        return []

                ret.append("--%s" % name)

                if arg_type is not bool:
                    if isinstance(req_arg, list):
                        ret += req_arg
                    else:
                        ret.append(req_arg)

        return ret


class CallbackObject:
    def __init__(
        self, doc: bokeh.document.document.Document, root_cmd: SakCmd, args: List[str]
    ) -> None:

        web_ret: Dict[str, Any] = {}
        self.path = "/".join(args)
        # _root_cmd = root_cmd()

        # Get only the metadata.
        ret = sak_arg_parser(root_cmd, args + ["-h"])

        if args:
            if args[-1] != ret["cmd"].name:
                web_ret["error"] = True
                web_ret["error_message"] = "Could not find the path for %s" % (
                    self.path
                )
                raise Exception(web_ret)
                # return web_ret

        cmd = ret["cmd"]
        params = {}

        for arg in cmd.args:
            webarg = SakWebCmdArg(arg).getAsDict()

            name = webarg["name"]
            default = webarg["default"]
            choices = webarg["choices"]

            if webarg["type"] in ["int", "float", "string"]:
                _params = {}
                if choices:
                    if default is not None:
                        _params["value"] = str(default)
                    params[name] = pn.widgets.Select(
                        name=name, options=choices, **_params
                    )
                else:
                    if default is not None:
                        _params["value"] = str(default)
                    params[name] = pn.widgets.TextInput(name=name, **_params)
            elif webarg["type"] in ["bool"]:
                params[name] = pn.widgets.Checkbox(name=name, value=default)
            elif webarg["type"] in ["list"]:

                if name not in params:
                    _params = {}
                    if default:
                        _params["value"] = default

                    if choices:
                        _params["options"] = choices
                    if arg.completercb is not None:
                        completer_args = SakCompleterArg(None, None, None, None)
                        _params["options"] = arg.completercb(completer_args)

                    if "options" in _params:
                        params[name] = pn.widgets.MultiChoice(name=name, **_params)

                if name not in params:
                    _params = {}
                    if default:
                        _params["value"] = default

                    if choices:
                        _params["options"] = choices
                    if arg.completercb:
                        completer_args = SakCompleterArg(None, None, None, None)
                        _params["options"] = arg.completercb(completer_args)

                    if "options" in _params:
                        params[name] = pn.widgets.CrossSelector(name=name, **_params)

                if name not in params:
                    _params = {}
                    if default is not None:
                        if isinstance(default, list):
                            _params["value"] = "\n".join(default)
                        else:
                            _params["value"] = str(default)
                    params[name] = pn.widgets.TextAreaInput(name=name, **_params)

        self.doc = doc
        self.params = params
        self.root_cmd = root_cmd
        self.args = args
        self.cmd = cmd

        self.output = pn.Column(
            # pn.layout.VSpacer(),
            # pn.pane.GIF('https://upload.wikimedia.org/wikipedia/commons/b/b1/Loading_icon.gif')
            # height=900,
            sizing_mode="stretch_both"
        )

        self.run_button = pn.widgets.Button(
            name="Run", button_type="primary", width=250
        )
        self.abort_button = pn.widgets.Button(name="Abort", button_type="primary")
        self.stdout = pn.pane.Str("", sizing_mode="stretch_both")

        # self.layout = pn.Row( self.output, sizing_mode="stretch_width")

        self.run_button.on_click(self.start_callback)
        self.abort_button.on_click(self.abort_callback)

        self.thread: Optional[StopableThread] = None

    def stdout_view(self) -> pn.pane.Str:
        return self.stdout

    def parameters_view(self) -> pn.Column:

        mk_content = f"""
        # {self.cmd.name.capitalize()}
        """

        if self.cmd.helpmsg:
            mk_content += f"""
        ## Help

        {self.cmd.helpmsg}
        """

        ret = pn.Column(pn.pane.Markdown(mk_content, sizing_mode="stretch_width"))

        for obj in self.params.values():
            ret.append(obj)

        if self.cmd.callback is not None:
            ret.append(self.run_button)

        return ret

    def view(self) -> pn.Column:
        return self.output

    @tornado.gen.coroutine
    def update_doc(self, new_output: pn.pane.PaneBase, stdout_str: pn.pane.Str) -> None:
        # TODO(witt): This coroutine is the one that will actually update the content
        # source.stream(dict(x=[x], y=[y]))
        self.output.clear()
        self.output.append(new_output)
        # print(stdout_str)
        self.stdout.object = stdout_str

    @tornado.gen.coroutine
    def update_stdout(self, stdout_str: str) -> None:
        # TODO(witt): This coroutine is the one that will actually update the content
        # print(stdout_str)
        self.stdout.object = stdout_str

    def abort_callback(self, event: Any) -> None:
        print("Raise exception!!!")
        if self.thread:
            self.thread.raise_exception()
        self.thread = None

    def start_callback(self, event: Any) -> None:
        vargs = {param_name: param.value for param_name, param in self.params.items()}

        # Start thread in another callback.
        self.thread = StopableThread(target=self.callback, kwargs=vargs)
        # self.thread = threading.Thread(target=self.callback, kwargs=vargs)
        self.thread.start()

    def callback(self, **vargs: Any) -> None:
        new_output = None

        # TODO: Get from my resources here
        loading = pn.pane.GIF(
            "https://upload.wikimedia.org/wikipedia/commons/b/b1/Loading_icon.gif",
            sizing_mode="stretch_both",
        )
        # loading = pni.LoadingSpinner()
        self.doc.add_next_tick_callback(
            partial(self.update_doc, new_output=loading, stdout_str=None)
        )

        # TODO(witt): This is a work around. Try to remove.
        # Make sure will start from a clean buffer.
        unregister_stdout_thread_id()
        unregister_stderr_thread_id()

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
                        # loading = pn.pane.GIF('https://upload.wikimedia.org/wikipedia/commons/b/b1/Loading_icon.gif')
                        self.doc.add_next_tick_callback(
                            partial(self.update_stdout, stdout_str=stdout_str)
                        )
                    if do_update_stdout:
                        time.sleep(UPDATE_PERIOD)

            update_thread = threading.Thread(target=simple_update_stdout)
            update_thread.start()

            # This is running in another thread.
            # Run callback code.
            new_output = self._callback(**vargs)

            # Stop the update thread
            do_update_stdout = False
            # Will not joing to allow a biffer sleep :)
            # update_thread.join()
        finally:
            # Schedule document update into tornado
            stdout_strio = get_stdout_buffer_for_thread()
            stdout_str = ""
            if stdout_strio is not None:
                stdout_str = stdout_strio.getvalue()

            if (new_output is not None) and hasattr(new_output, "panel"):
                new_output = new_output.panel()

            self.doc.add_next_tick_callback(
                partial(
                    self.update_doc,
                    new_output=new_output,
                    stdout_str=stdout_str + "\nDONE!",
                )
            )

            # Clean the thread buffers.
            unregister_stdout_thread_id()
            unregister_stderr_thread_id()

        # TODO(witt): Should I do some thread cleaning?

    def _callback(self, **vargs: Any) -> Any:
        ret: Any = None

        param_args = []
        for arg in self.cmd.args:
            param_args += SakWebCmdArg(arg).getRequestArgList(vargs)

        post_ret = sak_arg_parser(self.root_cmd, self.args + param_args)

        web_ret = {}
        web_ret["error"] = False
        if "error" in post_ret["argparse"]:
            web_ret["error"] = True
            web_ret["error_message"] = post_ret["argparse"]["error"]
            ret = web_ret
        elif "value" in post_ret:
            web_ret["result"] = post_ret["value"]
            if not web_ret["error"]:
                if has_pandas and isinstance(web_ret["result"], pd.DataFrame):
                    ret = pn.pane.DataFrame(web_ret["result"])
                else:
                    ret = web_ret["result"]

        return ret


class SakDoc(param.Parameterized):  # type: ignore

    # command = param.ObjectSelector()

    def __init__(self, doc: bokeh.document.document.Document) -> None:
        self.doc = doc
        super().__init__()

        self._curr_cmd = root_cmd()

        # TODO(witt): I dont know if I want to receive the path here.
        args = self.doc.session_context.request.arguments
        path = ""
        try:
            path = args["path"][0].decode("utf-8")
        except Exception as e:
            print("ERROR! Failed to get the path from the document.", str(e))
        # Filter empty fields
        self._args = [x for x in path.split("/") if x]

    # def view(self):
    #    content = CallbackObject(self.doc, self._curr_cmd, self._args)
    #    return pn.Column(
    #            pn.pane.Markdown('''# SAK'''),
    #            #pn.Row(
    #                #self.param,
    #                content.view()
    #                #)
    #
    #
    #            )

    def server_doc(self) -> bokeh.document.document.Document:
        content = CallbackObject(self.doc, self._curr_cmd, self._args)

        # from panel.template import DarkTheme

        # tmpl = pn.Template(template=(template % 'server'), nb_template=(template % 'notebook'))
        # tmpl = pn.template.GoldenTemplate(title='SAK' #, theme=DarkTheme)
        # tmpl = pn.template.VanillaTemplate(title='SAK', header_background="#357ebd") #, theme=DarkTheme)
        tmpl = pn.template.BootstrapTemplate(
            title="SAK", header_background="#357ebd"
        )  # , theme=DarkTheme)
        # tmpl.nb_template.globals['get_id'] = make_globally_unique_id

        toc_md = ""
        # toc_md += f'''[HOME &#127968;](./)'''
        if content.path:
            toc_md += f"""[PARENT  &#8593;](./?path={os.path.dirname(content.path)})"""

        # toc_md += f'''
        # ---
        # '''

        subcmds_md = ""
        if content.cmd.subcmds:
            subcmds_md += """
        ---
        """

        for subcmd in content.cmd.subcmds:
            subcmds_md += f"""
        [{subcmd.name.upper()}](./?path={os.path.join(content.path, subcmd.name)})
        """
        # toc_md += '''
        # ---
        # '''

        controller = pn.Column(
            # pn.Row(
            #    pn.pane.Pane(str( RESOURCES_PATH / 'static/img/sak.png' ), height=40),
            #    pn.pane.Markdown('# SAK')
            # ),
            pn.pane.Markdown(toc_md, sizing_mode="stretch_width"),
            pn.pane.Markdown(
                subcmds_md, sizing_mode="stretch_width"
            ),  # , style={'font-size': '12px'}),
            content.parameters_view(),
            # pn.layout.VSpacer(),
            # css_classes=['panel-widget-box', 'custom-wbox'],
            sizing_mode="stretch_both",
        )

        # parameters = content.parameters_view()

        content_pane = pn.Tabs(
            ("output", content.view()),
            ("stdout", content.stdout_view()),
            # height=900,
            # css_classes=['panel-widget-box', 'custom-wbox'],
            sizing_mode="stretch_both",
        )
        # content_pane = content.view()

        tmpl.sidebar.append(controller)
        tmpl.main.append(content_pane)

        # tmpl.add_panel('controller', controller)
        # tmpl.add_panel('parameters', parameters)
        # tmpl.add_panel('content', content_pane)
        # tmpl.add_panel('stdout', content.stdout_view())

        # tmpl.modal.append(pn.pane.Markdown('This is a modal test'))
        # tmpl.open_modal()

        ret = tmpl.server_doc(self.doc)
        return ret

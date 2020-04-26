#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__version__ = "0.0.0"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

from sakcmd import SakCmd, SakArg, SakCmdCtx, SakCmdRet
from sakplugin import SakPlugin, SakPluginManager

from typing import List, Any, Dict, Optional

from argparse import ArgumentParser

from asyncio import Future, ensure_future

from prompt_toolkit import Application
from prompt_toolkit.application.current import get_app
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.keys import Keys
from prompt_toolkit.key_binding.bindings.focus import focus_next, focus_previous
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    Float,
    HSplit,
    VSplit,
    Window,
    WindowAlign,
)
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.dimension import D
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.filters import Condition
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import (
    Box,
    Button,
    Checkbox,
    Dialog,
    Frame,
    Label,
    MenuContainer,
    MenuItem,
    ProgressBar,
    RadioList,
    TextArea,
)


has_matplotlib = False
try:
    import matplotlib
    import matplotlib.pyplot as plt
    import drawilleplot
    has_matplotlib = True
except:
    pass


class SakTuiCmdArg():
    def __init__(self, arg: SakArg) -> None:
        self.arg = arg

        self.text_field = TextArea(scrollbar=True, width=D(preferred=70))

        self.reset()

    def reset(self) -> None:
        d = self.getAsDict()
        default = d.get('default', None)
        if default is not None:
            if isinstance(default, list):
                self.text_field.text = ', '.join(default)
            else:
                self.text_field.text = str(default)

    def getAsDict(self) -> Dict[str, Any]:
        action = self.arg.vargs.get('action', '')
        default = self.arg.vargs.get('default', None)
        choices = self.arg.vargs.get('choices', [])
        arg_type = self.arg.vargs.get('type', None)
        nargs = self.arg.vargs.get('nargs', None)

        #if arg_type is None:
        if action in ['store_true', 'store_false']:
            arg_type = bool
        if action in ['append'] or nargs in ['*', '+']:
            arg_type = list

        if default is None:
            if action == 'store_true':
                default = False
            elif action == 'store_false':
                default = True

        type_lut = {
            bool: 'bool',
            str: 'string',
            list: 'list',
            int: 'int',
            float: 'float'
        }

        ret: Dict[str, Any] = {
            'name': self.arg.name,
            'help': self.arg.helpmsg,
            'type': type_lut.get(arg_type, 'string'),
            'default': default,
            'choices': choices,
            'nargs': nargs,
            'action': action,
        }
        return ret

    def getLayout(self) -> Any:
        return VSplit([
            Frame(body=Label(text=self.arg.name), width=D(preferred=30)),
            Box(self.text_field),
        ])

    def getRequestArgList(self) -> List[str]:
        type_lut = {
            'bool': bool,
            'string': str,
            'list': list,
            'int': int,
            'float': float
        }
        cfg = self.getAsDict()

        name = cfg['name']
        arg_type = type_lut.get(cfg['type'], str)
        arg_action = cfg['action']

        req_arg = self.text_field.text.strip()

        ret: List[str] = []
        if req_arg == '':
            return ret

        if req_arg is not None:

            if arg_type is bool:
                if 'store_true' == arg_action:
                    if req_arg not in ['yes', 'true', '1']:
                        return []
                if 'store_false' == arg_action:
                    if req_arg not in ['false', 'no', '0']:
                        return []

            ret.append('--%s' % name)

            if arg_type is not bool:
                if arg_type is list:
                    ret += [x.strip() for x in req_arg.split(',')]
                else:
                    ret.append(req_arg)

        return ret


class SakTuiCmd():
    def __init__(self, tui: 'SakTuiImpl', cmd: SakCmd) -> None:
        self.tui = tui

        self.cmd = cmd
        self.args: List[SakTuiCmdArg] = []
        for arg in cmd.args:
            self.args.append(SakTuiCmdArg(arg))

        self.subcmds: List[SakTuiCmd] = []
        for subcmd in cmd.subcmds:
            self.subcmds.append(SakTuiCmd(self.tui, subcmd))

        self._isVisible = False
        self.text_field = TextArea(scrollbar=True)
        self.runButton = Button(text="run", handler=self.execCommand)
        self.closeButton = Button(text="close", handler=self.closeCommand)
        self.restoreButton = Button(text="reset", handler=self.restoreCommand)

        self.reset()

    def reset(self) -> None:
        for arg in self.args:
            arg.reset()
        self.text_field.text = ''

    def getLayout(self) -> Any:
        return ConditionalContainer(
            content=HSplit([
                HSplit([x.getLayout() for x in self.args] + [
                    VSplit(
                        [self.closeButton, self.restoreButton, self.runButton])
                ]),
                Window(height=1, char='.'),
                self.text_field,
                Window(height=1, char='-'),
            ]),
            filter=Condition(lambda: self._isVisible),
        )

    def restoreCommand(self) -> None:
        self.reset()

    def closeCommand(self) -> None:
        self._isVisible = False
        self.reset()

    def execCommand(self) -> None:
        if self.cmd.callback:
            self.tui.log('Executing %s' % self.cmd.name)
            # TODO: Find a way to pass a command Stdout and other parameters
            if has_matplotlib:
                matplotlib.use('module://drawilleplot')

            arg_list = []
            for arg in self.args:
                arg_list += arg.getRequestArgList()


            self.tui.log('Args: %s' % str(arg_list))
            self.cmd.runArgParser(arg_list)
            return 

            p = self.cmd.generateArgParse()

            error_status = {}

            def exit(p: ArgumentParser,
                     status: Optional[str] = None,
                     message: Optional[str] = None) -> None:
                error_status['status'] = status
                error_status['message'] = message

            # TODO: How to legally override the exit method?
            p.exit = exit  # type: ignore

            try:
                self.tui.log('Args: %s' % str(arg_list))

                args = p.parse_args(arg_list)
            except:
                pass
                if error_status:
                    self.tui.log('Err: %s' % str(error_status))
                    # TODO: Sent to the log...
                return

            #TODO: Set better context info
            dargs: Dict[str, Any] = vars(args)

            ctx = SakCmdCtx()
            ctx.kwargs = dargs
            ret = self.cmd.callback(ctx)

            if has_matplotlib and isinstance(ret.retValue,
                                             matplotlib.figure.Figure):
                new_ret = ''
                for manager in drawilleplot.Gcf.get_all_fig_managers():
                    canvas = manager.canvas
                    canvas.draw()
                    new_ret += canvas.to_txt()
                    new_ret += '\n\n'
                plt.close()
                ret.retValue = new_ret

            # TODO: The return value should be wrapped in some SAK return objects (Raw text, image, ...)
            self.text_field.text = str(ret.retValue)

    def __call__(self) -> None:
        self._isVisible = not self._isVisible
        return

    def asMenuItems(self) -> MenuItem:
        return MenuItem(self.cmd.name,
                        children=[
                            c.asMenuItems() for c in self.subcmds
                            if SakCmd.EXP_WEB in c.cmd.expose
                        ],
                        handler=self)


class MessageDialog:
    def __init__(self, title: str, text: str) -> None:
        self.future = Future()

        def set_done() -> None:
            self.future.set_result(None)

        ok_button = Button(text="OK", handler=(lambda: set_done()))

        self.dialog = Dialog(
            title=title,
            body=HSplit([
                Label(text=text),
            ]),
            buttons=[ok_button],
            width=D(preferred=80),
            modal=True,
        )

    def __pt_container__(self) -> Dialog:
        return self.dialog

class SakTuiImpl(object):
    def __init__(self, plugin) -> None:
        super(SakTuiImpl, self).__init__()
        self.plugin = plugin

        self.show_status_bar = True
        self.show_log_pane = True

        self.log_area = TextArea()

    def log(self, msg: str, prefix: str = '>>') -> None:
        self.log_area.text += '%s %s\n' % (prefix, msg)

    def get_statusbar_text(self) -> str:
        return "(left) Press Ctrl-Q to exit. "

    def get_statusbar_right_text(self) -> str:
        return '(right) TODO'

    def start(self, ctx: SakCmdCtx) -> SakCmdRet:
        self.widgetsList: List[Any] = []
        cmdTree = SakTuiCmd(self, self.plugin.context.pluginManager.generateCommandsTree())

        def exportCmdLayout(cmd: SakTuiCmd) -> None:
            if cmd.cmd.callback is not None:
                self.widgetsList.append(cmd.getLayout())
            for subcmd in cmd.subcmds:
                exportCmdLayout(subcmd)

        exportCmdLayout(cmdTree)

        self.statusbar = ConditionalContainer(
            content=VSplit(
                [
                    Window(FormattedTextControl(self.get_statusbar_text),
                           style="class:status"),
                    Window(
                        FormattedTextControl(self.get_statusbar_right_text),
                        style="class:status.right",
                        width=9,
                        align=WindowAlign.RIGHT,
                    ),
                ],
                height=1,
            ),
            filter=Condition(lambda: self.show_status_bar),
        )

        body = HSplit([
            VSplit([
                HSplit(
                    self.widgetsList,
                    width=D(preferred=80),
                    align=WindowAlign.LEFT,
                ),
                Window(width=1, char='|'),
                ConditionalContainer(
                    content=HSplit(
                        [
                            self.log_area,
                        ],
                        width=D(preferred=20),
                        align=WindowAlign.RIGHT,
                    ),
                    filter=Condition(lambda: self.show_log_pane)),
            ]), self.statusbar
        ])

        def show_message(title: str, text: str) -> None:
            async def coroutine() -> None:
                dialog = MessageDialog(title, text)
                await show_dialog_as_float(dialog)
                return None

            ensure_future(coroutine())

        def do_about() -> None:
            show_message(
                "About",
                "SAK Text User Interface plugin.\nCreated by Fernando Witt.")

        root_container = MenuContainer(
            body=body,
            menu_items=[] + cmdTree.asMenuItems().children + [
                MenuItem("Info",
                         children=[
                             MenuItem("About", handler=do_about),
                         ]),
            ],
            floats=[
                Float(
                    xcursor=True,
                    ycursor=True,
                    content=CompletionsMenu(max_height=16, scroll_offset=1),
                ),
            ],
        )

        async def show_dialog_as_float(dialog: MessageDialog) -> Any:
            " Coroutine. "
            float_ = Float(content=dialog)
            root_container.floats.insert(0, float_)

            app = get_app()

            focused_before = app.layout.current_window
            app.layout.focus(dialog)
            result = await dialog.future
            app.layout.focus(focused_before)

            if float_ in root_container.floats:
                root_container.floats.remove(float_)

            return result

        layout = Layout(container=root_container,
                        focused_element=self.log_area)

        kb = KeyBindings()
        kb.add("tab")(focus_next)
        kb.add("s-tab")(focus_previous)

        # TODO: Annotate the event
        @kb.add('c-q')
        def exit_(event) -> None:
            """ Pressing Ctrl-Q to exit.  """
            event.app.exit()

        style = Style.from_dict({
            "status": "reverse",
            "shadow": "bg:#440044",
        })

        app = Application(
            layout=layout,
            key_bindings=kb,
            full_screen=True,
            mouse_support=True,
            style=style,
            enable_page_navigation_bindings=True,
        )
        app.run()

        return ctx.get_ret()


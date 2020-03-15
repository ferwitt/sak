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

from typing import List

from asyncio import Future, ensure_future

from prompt_toolkit import Application
from prompt_toolkit.application.current import get_app
from prompt_toolkit.key_binding import KeyBindings
#from prompt_toolkit.key_binding.manager import KeyBindingManager
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

class SakTuiCmd():
    def __init__(self, tui: 'SakTui', cmd: SakCmd) -> None:
        self.tui = tui

        self.cmd = cmd
        self.args: List[SakTuiCmdArg] = []
        for arg in cmd.args:
            self.args.append(SakTuiCmdArg(arg))

        self.subcmds: List[SakTuiCmd] = []
        for subcmd in cmd.subcmds:
            self.subcmds.append(SakTuiCmd(self.tui, subcmd))

    def __call__(self) -> None:
        if self.cmd.callback:
            # TODO: Find a way to pass a command Stdout and other parameters
            if has_matplotlib:
                matplotlib.use('module://drawilleplot')

            #TODO: Set better context info
            ctx = SakCmdCtx()

            ret = self.cmd.callback(ctx)

            if has_matplotlib and isinstance(ret.retValue, matplotlib.figure.Figure):
                new_ret = ''
                for manager in drawilleplot.Gcf.get_all_fig_managers():
                    canvas = manager.canvas
                    canvas.draw()
                    new_ret += canvas.to_txt()
                    new_ret += '\n\n'
                plt.close()
                ret.retValue = new_ret

            # TODO: The return value should be wrapped in some SAK return objects (Raw text, image, ...)
            self.tui.text_field.text = str(ret.retValue)

    def asMenuItems(self) -> MenuItem:
        return MenuItem(self.cmd.name,
                children = [c.asMenuItems() for c in self.subcmds if SakCmd.EXP_WEB in c.cmd.expose],
                handler=self
                )


class MessageDialog:
    def __init__(self, title: str, text: str) -> None:
        self.future = Future()

        def set_done() -> None:
            self.future.set_result(None)

        ok_button = Button(text="OK", handler=(lambda: set_done()))

        self.dialog = Dialog(
            title=title,
            body=HSplit([Label(text=text),]),
            buttons=[ok_button],
            width=D(preferred=80),
            modal=True,
        )

    def __pt_container__(self) -> Dialog:
        return self.dialog


class SakTui(SakPlugin):
    def __init__(self) -> None:
        super(SakTui, self).__init__('tui')
        self.show_status_bar = True

    def get_statusbar_text(self) -> str:
        return "(left) Press Ctrl-Q to exit. "

    def get_statusbar_right_text(self) -> str:
        return '(right) TODO'


    def start(self, ctx: SakCmdCtx) -> SakCmdRet:

        self.text_field = TextArea(
            # lexer=DynamicLexer(
            #     lambda: PygmentsLexer.from_filename(
            #         ApplicationState.current_path or ".txt", sync_from_start=False
            #     )
            # ),
            scrollbar=True,
            line_numbers=True,
            #search_field=search_toolbar,
        )


        budy = HSplit([

            VSplit([
            # One window that holds the BufferControl with the default buffer on
            # the left.
            self.text_field,

            # A vertical line in the middle. We explicitly specify the width, to
            # make sure that the layout engine will not try to divide the whole
            # width by three for all these windows. The window will simply fill its
            # content by repeating this character.
            Window(width=1, char='|'),

            # Display the text 'Hello world' on the right.
            Window(content=FormattedTextControl(text='I could put the log here')),
            # Window(width=1, char='|'),

            # Box( Frame(
            #     TextArea(text="Hello world!\nPress control-q to quit.", width=40, height=10,)
            # )),
            ]),

            ConditionalContainer(
                content=VSplit(
                    [
                        Window(
                            FormattedTextControl(self.get_statusbar_text), style="class:status"
                        ),
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
            ),
        ])

        cmdTree = SakTuiCmd(self, self.context.pluginManager.generateCommandsTree())

        def show_message(title: str, text: str) -> None:
            async def coroutine() -> None:
                dialog = MessageDialog(title, text)
                await show_dialog_as_float(dialog)

            ensure_future(coroutine())

        def do_about() -> None:
            show_message("About", "SAK Text User Interface plugin.\nCreated by Fernando Witt.")
        
        root_container = MenuContainer(
            body=budy,
            menu_items=[]
                + cmdTree.asMenuItems().children
                + [
                    MenuItem("Info", children=[MenuItem("About", handler=do_about),]),
                    ]
                ,
            floats=[
                Float(
                    xcursor=True,
                    ycursor=True,
                    content=CompletionsMenu(max_height=16, scroll_offset=1),
                ),
            ],
            )



        async def show_dialog_as_float(dialog: MessageDialog):
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


        layout = Layout(container=root_container, focused_element=self.text_field)

        kb = KeyBindings()
        kb.add("tab")(focus_next)
        kb.add("s-tab")(focus_previous)

        #manager = KeyBindingManager.for_prompt()

        # Add an additional key binding for toggling this flag.
        @kb.add(Keys.F4)
        def _(event) -> None:
            " Toggle between Emacs and Vi mode. "
            # TODO: Annotate the event
            cli = event.cli

            if cli.editing_mode == EditingMode.VI:
                cli.editing_mode = EditingMode.EMACS
            else:
                cli.editing_mode = EditingMode.VI

        @kb.add('c-q')
        def exit_(event) -> None:
            # TODO: Annotate the event
            """ Pressing Ctrl-Q to exit.  """
            event.app.exit()

        style = Style.from_dict({"status": "reverse", "shadow": "bg:#440044",})

        app = Application(layout=layout,
                key_bindings=kb,
                full_screen=True,
                mouse_support=True,
                style=style,
                enable_page_navigation_bindings=True,
                )
        app.run()

        return ctx.get_ret()

    def exportCmds(self, base: SakCmd) -> None:
        tui = SakCmd('tui')

        start = SakCmd('start', self.start)
        tui.addSubCmd(start)
        
        base.addSubCmd(tui)

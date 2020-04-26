# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__version__ = "0.0.0"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

import sys, os
import argparse
from argparse import Namespace, ArgumentParser, REMAINDER
import functools
from typing import Optional, Callable, Dict, Any, List

try:
    from StringIO import StringIO ## for Python 2
except ImportError:
    from io import StringIO ## for Python 3

hasArgcomplete = False
try:
    import argcomplete
    hasArgcomplete = True
except:
    pass


class SakCompleterArg(object):
    def __init__(self,
            prefix: str,
            action: Any, # TODO: Restrict Any
            parser: Any, # TODO: Restrict Any
            parsed_args: Namespace
            ):
        '''
        Example of parameters from argcomplete
        {
            'prefix': '',
            'action': IntrospectAction(option_strings=['--account', '-a'], dest='account', nargs=None, const=None, default=None, type=None, choices=None, help='', metavar=None),
            'parser': MonkeyPatchedIntrospectiveArgumentParser(prog='sak fin total', usage=None, description=None, formatter_class=<class 'argparse.HelpFormatter'>, conflict_handler='error', add_help=True),
            'parsed_args': Namespace(account=None, currency=None, sak_callback=<bound method SakFin.total of <sak_fin.SakFin object at 0x7fe68bbb8390>>)
        }
        '''
        super(SakCompleterArg, self).__init__()
        self.prefix = prefix
        self.action = action
        self.parser = parser
        self.parsed_args = parsed_args


class SakDecorator:        
    def __init__(self, *args, **vargs):
        self.args = args
        self.vargs = vargs
        self.func = None
    def __call__(self, func):
        self.func = func
        @functools.wraps(func)
        def wrapper(*args, **vargs):
            return self.func(*args, **vargs)
        wrapper._sak_dec_chain = self        
        return wrapper



class SakArg(SakDecorator):
    def __init__(self,
            name:str,
            helpmsg:str = '',
            short_name:Optional[str] = None,
            completercb:Optional[Callable[[Optional[SakCompleterArg]], List[Any]]] = None,
            **vargs: Any
        ) -> None:
        super(SakArg, self).__init__()
        self.name = name
        self.helpmsg = helpmsg
        self.short_name = short_name
        self.vargs = vargs
        self.completercb = completercb

    def addToArgParser(self, parser: ArgumentParser) -> None:
        pargs = []
        pargs += ['--%s' % self.name]
        if self.short_name:
            pargs += ['-%s' % self.short_name]

        aux = parser.add_argument(*pargs, help=self.helpmsg, **self.vargs)

        completercb = self.completercb
        if hasArgcomplete and (completercb is not None):
            def completercbWrapper(**vargs: Any) -> List[Any]:
                arg = SakCompleterArg(
                        prefix=vargs['prefix'],
                        action=vargs['action'],
                        parser=vargs['parser'],
                        parsed_args=vargs['parsed_args'],
                       )
                return completercb(arg) # type: ignore
            aux.completer = completercbWrapper # type: ignore


class SakCmdRet(object):
    """docstring for SakCmdRet"""
    def __init__(self) -> None:
        super(SakCmdRet, self).__init__()
        self.retValue: Optional[Any] = None


class SakCmdIO(StringIO): # type: ignore
    def __init__(self) -> None:
        super(SakCmdIO, self).__init__()


class SakCmdCtx(object):
    def __init__(self) -> None:
        super(SakCmdCtx, self).__init__()
        self.kwargs: Dict[str, Any] = {}

        self.stdout = SakCmdIO()
        self.stderr = SakCmdIO()

    def get_ret(self) -> SakCmdRet:
        # TODO: I can fill the return with some context stuff
        return SakCmdRet()

class SakCmd(SakDecorator):
    EXP_CLI = 'cli'
    EXP_WEB = 'web'

    def __init__(self,
            name:str,
            # Deprecated
            callback: Optional[Callable[[SakCmdCtx], SakCmdRet]]=None,
            args:List[SakArg]=[],
            expose:List[str]=[],
            helpmsg:str = ''
            ) -> None:
        super(SakCmd, self).__init__()

        self.name = name
        self.callback = callback
        self.subcmds: List[SakCmd] = []
        self.args = args or []

        self.helpmsg = helpmsg

        self.parent: Optional[SakCmd] = None
        self.expose = expose or [SakCmd.EXP_CLI]

    # Deprecated
    def addSubCmd(self, subcmd: 'SakCmd') -> None:
        subcmd.setParent(self)
        self.subcmds.append(subcmd)

    def addExpose(self, expose: List[str] = []) -> None:
        for exp in expose:
            if exp not in self.expose:
                self.expose.append(exp)
        if self.parent:
            self.parent.addExpose(expose)

    def setParent(self, parent: 'SakCmd') -> None:
        self.parent = parent
        self.addExpose(self.expose)

    def addArg(self, arg: SakArg) -> None:
        self.args.append(arg)

    def runArgParser(self, args=None, subparsers=None, root_parser=None, level=1, show_help=False, nm=None) -> None:

        # _nm = {}
        # _nm.update(nm or {})
        # nm = _nm

        args = args or []
        if ('-h' in args) or ('--help' in args):
            show_help = True
            args = [x for x in args if x != '-h' and x != '--help']

        # Register command
        parser = None
        if subparsers is None:

            error_status = {}
            def exit(p: ArgumentParser,
                     status: Optional[str] = None,
                     message: Optional[str] = None) -> None:
                error_status['status'] = status
                error_status['message'] = message

            d = "Group everyday developer's tools in a swiss-army-knife command."
            parser = ArgumentParser(prog=self.name, description=d)
            #parser.exit = exit
        else:
            parser = subparsers.add_parser(self.name, help=self.helpmsg)
        parser.set_defaults(sak_callback=self.callback, sak_cmd=self, sak_parser=parser)

        if root_parser is None:
            root_parser = parser

        for arg in self.args:
            arg.addToArgParser(parser)


        if level <= 0:
            return

        # Check if its auto completion
        is_in_completion = False
        comp_line = os.environ.get("COMP_LINE", None)
        if comp_line is not None:
            # What is this COMP_POINT?
            comp_point = int(os.environ.get("COMP_POINT", 0))
            is_in_completion = True
            _, _, _, comp_words, _ = argcomplete.split_line(comp_line, comp_point)
            if not args:
                args = comp_words[1:]

        # Register only the next level of the subcommands
        if self.subcmds:
            subparsers = parser.add_subparsers()
            for i in self.subcmds:
                #print('register first level ', i.name)
                i.runArgParser([], subparsers, root_parser, 0, show_help, nm)

        all_satisfied = False
        rargs = []
        try:
            #if 'sak_callback' in nm:
            #    nm.pop('sak_callback')
            #if 'sak_cmd' in nm:
            #    nm.pop('sak_cmd')
            #if 'sak_parser' in nm:
            #    nm.pop('sak_parser')

            nm, rargs = parser.parse_known_args(args, namespace=nm)

            #nm.update(_nm)
            all_satisfied = True
            #nm['args'] = rargs
        except:
            import traceback
            traceback.print_exc(file=sys.stdout)
            print('Failed')
            return False
            pass

        print(80*'-')
        print(rargs, nm)

        # I have consumed all the arguments, stop the tree search
        if all_satisfied:
            if self.subcmds and nm.sak_cmd and (nm.sak_cmd != self):
                # Step into the commands tree
                if nm.sak_cmd.runArgParser(rargs, subparsers, root_parser, 1, show_help, nm):
                    return True

        # Auto completion
        if hasArgcomplete:
            argcomplete.autocomplete(root_parser)

        # Reached as LEAF!

        nm = vars(nm)

        if ('sak_callback' not in nm) or (nm['sak_callback'] is None):
            show_help = True
        if show_help:
            parser.print_help()
            return True

        if rargs:
            # There are remaining unparsed arguments, report error
            msg = 'unrecognized arguments: %s'
            parser.error(msg % ' '.join(args))
            return

        # All the arguments must have been consumed!
        callback: Callable[[SakCmdCtx], SakCmdRet] = nm.pop('sak_callback')
        if callback:
            ctx = SakCmdCtx()
            ctx.kwargs = nm
            ret = callback(ctx)
            if has_matplotlib and isinstance(ret.retValue,
                                             matplotlib.figure.Figure):
                plt.show()
            elif ret.retValue is not None:
                # TODO: Standardize the output from the plugin endpoints!
                print(ret.retValue)

        return True

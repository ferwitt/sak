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
from contextlib import redirect_stderr, redirect_stdout

from collections.abc import Iterable 
import inspect

from sakconfig import install_core_requirements

#try:
#    from StringIO import StringIO ## for Python 2
#except ImportError:
#    from io import StringIO ## for Python 3
from io import StringIO ## for Python 3

hasArgcomplete = False
try:
    import argcomplete #type: ignore
    hasArgcomplete = True
except:
    pass

try:
    # Try to import owlready2 and redirect stderr to string IO
    f = StringIO()
    with redirect_stderr(f):
        import owlready2 as owl #type: ignore
except ImportError:
    # If import fails, then ask if the user wants to try to update the requirements
    install_core_requirements()


# TODO: Sanityze the penv
def object_to_dict(d):
    if not isinstance(d, dict):
        #if isinstance(d, list) or inspect.isgenerator(d):
        if isinstance(d, str) or isinstance(d, int) or isinstance(d, float):
            _ret_str = d
            def _sak_ret_value_():
                return _ret_str
            d = {'_sak_cmd_callback': _sak_ret_value_, '_sak_cmd':None, '_sak_cmd_args':[]}
        #elif isinstance(d, tuple):
        #    nenv = {}
        #    for idx, v in enumerate(d):
        #        k = str(idx)
        #        nenv[k] = v
        #    d = nenv
        elif isinstance(d, Iterable):
            nenv = {}
            for idx, v in enumerate(d):
                #TODO: If it is a thing, I can put the name in the index
                k = str(idx)
                if hasattr(v, '_sak_dec_chain'):
                    k = v.__name__
                try:
                    k = v.name
                except:
                    pass
                k  = k.replace('/', '__')
                nenv[k] = v
            d = nenv
        elif inspect.ismethod(d) or inspect.isfunction(d):
            if hasattr(d, '_sak_dec_chain'):
                chain = d._sak_dec_chain
                cb = d

                d = {'_sak_cmd_callback': cb, '_sak_cmd':None, '_sak_cmd_args':[]}
                while chain is not None:
                    if isinstance(chain, SakProperty):
                        d['_sak_cmd_callback'] = None
                        d.update(object_to_dict(cb()))
                        break
                    elif isinstance(chain, SakCmd):
                        d['_sak_cmd'] = chain
                    elif isinstance(chain, SakArg):
                        d['_sak_cmd_args'].append(chain)

                    if hasattr(chain.func, '_sak_dec_chain'):
                        chain = chain.func._sak_dec_chain
                    else:
                        chain = None
            else:
                # TODO: Remove this
                #TODO: I believe I suggested removing because it can be dangerous to call functions everywhere...
                #      But maybe I could use some introspection and check the areguments... then build a proper command.
                cb = d
                d = { '_sak_cmd_callback': lambda **x: cb(), '_sak_cmd':None, '_sak_cmd_args':[] }
        else:
            obj = d
            d = None
            if isinstance(obj, owl.Thing) or isinstance(obj, owl.Ontology) or isinstance(obj, owl.ThingClass):

                d = {'_sak_cmd_callback': None, '_sak_cmd':None, '_sak_cmd_args':[]}

                if callable(obj):
                    if hasattr(obj.__call__, '_sak_dec_chain'):
                        d['_sak_cmd_callback'] = obj
                        chain = obj.__call__._sak_dec_chain
                        while chain is not None:
                            if isinstance(chain, SakCmd):
                                d['_sak_cmd'] = chain
                            elif isinstance(chain, SakArg):
                                #TODO(witt): I think it would be nice to store everything inside the command object. What do you think?
                                d['_sak_cmd_args'].append(chain)
                            if hasattr(chain.func, '_sak_dec_chain'):
                                chain = chain.func._sak_dec_chain
                            else:
                                chain = None

                if not d['_sak_cmd']:
                    d['_sak_cmd'] = SakCmd()

                if not d['_sak_cmd'].helpmsg:
                    docstring = inspect.getdoc(obj)
                    if docstring:
                        d['_sak_cmd'].helpmsg = inspect.cleandoc(docstring)

                for k in dir(obj):
                    if k.startswith('_'): continue

                    dd = getattr(obj, k)

                    #print(k, type(dd), repr(dd))

                    if not hasattr(dd, '_sak_dec_chain'):
                        if (not isinstance(dd, owl.Thing)) and (not isinstance(dd, owl.prop.IndividualValueList)):
                            continue
                            pass

                    k = k.replace('/', '__')
                    if inspect.ismethod(dd) or inspect.isfunction(dd):
                        dd = object_to_dict(dd)

                    if dd is None:
                        continue

                    d[k] = dd
    return d


def argcomplete_args():
    args = []
    # Check if its auto completion
    #is_in_completion = False
    comp_line = os.environ.get("COMP_LINE", None)
    if comp_line is not None:
        # What is this COMP_POINT?
        comp_point = int(os.environ.get("COMP_POINT", 0))
        #is_in_completion = True
        _, _, _, comp_words, _ = argcomplete.split_line(comp_line, comp_point)
        if not args:
            args = comp_words[1:]
    return args


def sak_arg_parser(base_cmd, args=None
        #, as_json=False
        ) -> None:

    args = args or argcomplete_args()

    # Remove the help flag from args and set show_help
    args = args or []
    sak_show_help = False
    if ('-h' in args) or ('--help' in args):
        sak_show_help = True
        args = [x for x in args if x != '-h' and x != '--help']

    # The root parser
    description = "TODO!" # base_cmd.description or base_cmd.helpmsg
    name = "sak" # TODO I can get some introspection? # base_cmd.name
    root_parser = ArgumentParser(prog=name, description=description)

    # Prepare the variables for the tree decend
    cmd = base_cmd
    parser = root_parser
    base_cmd_callback = None # base_cmd.callback
    nm = Namespace(sak_callback=base_cmd_callback, sak_cmd=base_cmd, sak_parser=parser)

    ret = {
            'argparse': {},
            'ret': None
            }

    while True:
        cmd = object_to_dict(cmd)

        if '_sak_cmd_args' in cmd:
            for arg in cmd['_sak_cmd_args']:
                arg.addToArgParser(parser)

        # Register only the next level of the subcommands
        subparsers = None
        for subcmdname, subcmd in cmd.items():
            if subcmd is None:
                continue
            if subcmdname.startswith('_sak'):
                continue

            subcmd = object_to_dict(subcmd)
            if subcmd is None:
                continue

            if subparsers is None:
                subparsers = parser.add_subparsers()

            description = "" # subcmd.description or subcmd.helpmsg
            helpmsg = "" # subcmd.helpmsg
            _subcmd = subcmd.get('_sak_cmd', None)
            if _subcmd:
                description = _subcmd.description or _subcmd.helpmsg
                helpmsg = _subcmd.helpmsg
                subcmdname = _subcmd.name or subcmdname

            subcmd_callback = subcmd.get('_sak_cmd_callback', None) # subcmd.callback

            sub_parser = subparsers.add_parser(subcmdname, help=helpmsg, description=description)
            sub_parser.set_defaults(sak_callback=subcmd_callback, sak_cmd=subcmd, sak_parser=sub_parser)

        rargs: List[str] = []
        success = False
        try:
            f = StringIO()
            with redirect_stderr(f):
                nm, rargs = parser.parse_known_args(args, namespace=nm)

            # Go a level doen in the tree
            if (nm.sak_parser != parser) and (cmd.keys()):
                args = rargs
                parser = nm.sak_parser
                cmd = nm.sak_cmd
                continue

            success = True
        except:
            # Parse failed, show error message only if it is not help command
            if not sak_show_help:
                #if as_json:
                ret['argparse']['error'] = f.getvalue()
                #else:
                #    # TODO(witt): Maybe redirect to the json
                #    sys.stderr.write(f.getvalue())

        # Here we have consumed all the arguments and completly built the parser
        # Register auto completion
        if hasArgcomplete:
            #if not as_json:
            argcomplete.autocomplete(root_parser)
            #else:
            #    #TODO(witt): How to do suggestions based on json API?
            #    pass

        ret['cmd'] = cmd
        ret['nm'] = nm

        # We reached the leaf in the tree, but only want to get the help
        if nm.sak_callback is None:
            sak_show_help = True
        if sak_show_help:
            f = StringIO()
            with redirect_stdout(f):
                parser.print_help()

            #if as_json:
            #    if as_json:
            ret['argparse']['help'] = f.getvalue()
            #    else:
            #        # TODO(witt): Maybe redirect to the json
            #        print(f.getvalue())
            return ret

        # The parsing failed, so we just abort
        if not success:
            # TODO(witt): There should be no return
            return ret

        if rargs:
            f = StringIO()
            parser.print_usage(f)
            msg = '%(usage)s\n%(prog)s: error: %(message)s\n' % {
                    'usage': f.getvalue(),
                    'prog': parser.prog,
                    'message':  'unrecognized arguments: %s' % ' '.join(rargs),
                    }
            #if as_json:
            ret['argparse']['error'] = msg
            #else:
            #    sys.stderr.write(msg)
            return ret

        # Parse success and not arguments left.
        nm_dict: Dict[str, Any] = vars(nm)
        sak_cmd = nm_dict.pop('sak_cmd')
        sak_parser = nm_dict.pop('sak_parser')
        callback = nm_dict.pop('sak_callback')
        if callback:
            ret_value = callback(**nm_dict)

            #if as_json:
            ret['value'] = ret_value
            #else:
            #    if 'matplotlib.figure.Figure' in str(type(ret_value)):
            #        import pylab as pl #type: ignore
            #        pl.show()
            #    elif ret_value is not None:
            #        print(ret_value)

        # TODO(witt): There should be no return
        return ret

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
            #print(args, vargs)
            return self.func(*args, **vargs)
        wrapper._sak_dec_chain = self        
        return wrapper

class SakProperty(SakDecorator):
    pass


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


#class SakCmdRet(object):
#    """docstring for SakCmdRet"""
#    def __init__(self) -> None:
#        super(SakCmdRet, self).__init__()
#        self.retValue: Optional[Any] = None


# class SakCmdIO(StringIO): # type: ignore
#     def __init__(self) -> None:
#         super(SakCmdIO, self).__init__()
# class SakCmdCtx(object):
#     def __init__(self) -> None:
#         super(SakCmdCtx, self).__init__()
#         self.kwargs: Dict[str, Any] = {}
# 
#         self.stdout = SakCmdIO()
#         self.stderr = SakCmdIO()
# 
#     def get_ret(self) -> SakCmdRet:
#         # TODO: I can fill the return with some context stuff
#         return SakCmdRet()

class SakCmd(SakDecorator):
    EXP_CLI = 'cli'
    EXP_WEB = 'web'

    def __init__(self,
            name:str='', 
            # Deprecated
            #callback: Optional[Callable]=None,
            #args:List[SakArg]=[],
            expose:List[str]=[],
            helpmsg:str = ''
            ) -> None:
        super(SakCmd, self).__init__()

        self.name = name
        #self.callback = None
        self.subcmds: List[SakCmd] = []
        #self.args = args or []

        self.helpmsg = helpmsg
        self.description = None

        self.parent: Optional[SakCmd] = None
        self.expose = expose or [SakCmd.EXP_CLI]

    # # Deprecated
    # def addSubCmd(self, subcmd: 'SakCmd') -> None:
    #     subcmd.setParent(self)
    #     self.subcmds.append(subcmd)

    # def addExpose(self, expose: List[str] = []) -> None:
    #     for exp in expose:
    #         if exp not in self.expose:
    #             self.expose.append(exp)
    #     if self.parent:
    #         self.parent.addExpose(expose)

    # def setParent(self, parent: 'SakCmd') -> None:
    #     self.parent = parent
    #     self.addExpose(self.expose)

    # def addArg(self, arg: SakArg) -> None:
    #     self.args.append(arg)


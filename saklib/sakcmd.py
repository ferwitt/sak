# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

import copy

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
from io import StringIO  ## for Python 3

hasArgcomplete = False
try:
    import argcomplete  #type: ignore
    hasArgcomplete = True
except:
    pass

try:
    # Try to import owlready2 and redirect stderr to string IO
    f = StringIO()
    with redirect_stderr(f):
        import owlready2 as owl  #type: ignore
except ImportError:
    # If import fails, then ask if the user wants to try to update the requirements
    install_core_requirements()


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


class SakProperty(SakDecorator):
    pass


class SakCompleterArg(object):
    def __init__(
            self,
            prefix: str,
            action: Any,  # TODO: Restrict Any
            parser: Any,  # TODO: Restrict Any
            parsed_args: Namespace):
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


class SakArg(SakDecorator):
    def __init__(self,
                 name: str,
                 helpmsg: str = '',
                 short_name: Optional[str] = None,
                 completercb: Optional[Callable[[Optional[SakCompleterArg]],
                                                List[Any]]] = None,
                 **vargs: Any) -> None:
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
                return completercb(arg)  # type: ignore

            aux.completer = completercbWrapper  # type: ignore


class SakCmd(SakDecorator):
    EXP_CLI = 'cli'
    EXP_WEB = 'web'

    def __init__(self,
                 name: str = '',
                 expose: List[str] = [],
                 helpmsg: str = '') -> None:
        super(SakCmd, self).__init__()

        self.name = name
        self.callback = None
        self.subcmds: List[SakCmd] = []
        self.args = []

        self.helpmsg = helpmsg
        self.description = None


class SakCmdWrapper:
    def __init__(self,
                 wrapped_content=None,
                 name: str = None,
                 callback: Optional[Callable] = None,
                 args: List[SakArg] = None,
                 helpmsg: str = None,
                 subcmds=None,
                 cmd=None):
        d = wrapped_content

        self._wrapped_content = wrapped_content
        self._name = name
        self._callback = callback
        self._subcmds: List[SakCmd] = []
        self._args = args or []
        self._helpmsg = helpmsg
        self._description = subcmds
        self._cmd = cmd

        if isinstance(d, SakCmdWrapper):
            self._wrapped_content = d._wrapped_content
            self._name = d._name
            self._callback = d._callback
            self._subcmds: List[SakCmd] = d._subcmds
            self._args = d._args
            self._helpmsg = d._helpmsg
            self._description = d._subcmds
            self._cmd = d._cmd
        elif isinstance(d, SakCmd):
            self._cmd = d

    @property
    def name(self):
        cmd = self.cmd
        if cmd:
            if cmd.name:
                return cmd.name

        if self._name:
            return self._name

        d = self._wrapped_content
        if isinstance(d, owl.Thing) or isinstance(
                d, owl.Ontology) or isinstance(d, owl.ThingClass):
            return d.name

        return None

    @property
    def callback(self):
        if self._callback:
            return self._callback

        if self._wrapped_content:
            d = self._wrapped_content

            if inspect.ismethod(d) or inspect.isfunction(d):
                if hasattr(d, '_sak_dec_chain'):
                    cb = d
                    if cb:
                        return cb
                # TODO(witt): I dont think I should return the result from the callback here :/
                #return SakCmdWrapper(
                #        callback = lambda **x: cb()
                #        ) #{ '_sak_cmd_callback': lambda **x: cb(), '_sak_cmd':None, '_sak_cmd_args':[] }
        return None

    @property
    def subcmds(self):
        if self._subcmds:
            return self._subcmds

        cmd = self.cmd
        if cmd:
            if cmd.subcmds:
                return cmd.subcmds

        if self._wrapped_content:
            d = self._wrapped_content

            if isinstance(d, owl.Thing) or isinstance(d, owl.ThingClass):
                subcmds = []
                for k in dir(d):
                    if k.startswith('_'): continue
                    dd = getattr(d, k)

                    if not hasattr(dd, '_sak_dec_chain'):
                        if (not isinstance(dd, owl.Thing)) and (not isinstance(
                                dd, owl.prop.IndividualValueList)):
                            continue

                    dd = SakCmdWrapper(wrapped_content=dd, name=k)
                    subcmds.append(dd)
                if subcmds:
                    return subcmds

            if isinstance(d, Iterable):
                subcmds = []
                for idx, v in enumerate(d):
                    k = str(idx)
                    if hasattr(v, '_sak_dec_chain'):
                        k = v.__name__
                    try:
                        k = v.name
                    except:
                        pass
                    subcmds.append(SakCmdWrapper(wrapped_content=v, name=k))
                if subcmds:
                    return subcmds

        return []

    @property
    def args(self):
        if self._args:
            return self._args

        if self._wrapped_content:
            d = self._wrapped_content

            if inspect.ismethod(d) or inspect.isfunction(d):
                if hasattr(d, '_sak_dec_chain'):
                    args = []
                    chain = d._sak_dec_chain
                    while chain is not None:
                        if isinstance(chain, SakArg):
                            args.append(chain)
                        if hasattr(chain.func, '_sak_dec_chain'):
                            chain = chain.func._sak_dec_chain
                        else:
                            chain = None
                    if args:
                        return args
                # TODO: If does not have decorators, I can try to inspect the arguments here
        return []

    @property
    def helpmsg(self):
        if self._helpmsg:
            return self._helpmsg

        if self._description:
            return self._description

        cmd = self.cmd
        if cmd:
            if cmd.helpmsg:
                return cmd.helpmsg
            if cmd.description:
                return self.cmd.description

        d = self._wrapped_content
        if isinstance(d, owl.Thing) or isinstance(
                d, owl.Ontology) or isinstance(d, owl.ThingClass):
            docstring = inspect.getdoc(d)
            if docstring:
                return inspect.cleandoc(docstring)

        # TODO(witt): I did my best to get the help message, but no success
        return ''

    @property
    def description(self):
        return self._description

    @property
    def cmd(self):
        if self._cmd:
            return self._cmd

        if self._wrapped_content:
            d = self._wrapped_content

            if isinstance(d, SakCmd):
                return d

            if inspect.ismethod(d) or inspect.isfunction(d):
                if hasattr(d, '_sak_dec_chain'):
                    cmd = None
                    chain = d._sak_dec_chain
                    while chain is not None:
                        if isinstance(chain, SakCmd):
                            cmd = chain
                        if hasattr(chain.func, '_sak_dec_chain'):
                            chain = chain.func._sak_dec_chain
                        else:
                            chain = None
                    if cmd:
                        return cmd
        return None


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


def sak_arg_parser(base_cmd, args=None) -> None:
    args = args or argcomplete_args()

    # Remove the help flag from args and set show_help
    args = args or []
    sak_show_help = False
    if ('-h' in args) or ('--help' in args):
        sak_show_help = True
        args = [x for x in args if x != '-h' and x != '--help']

    # The root parser
    description = base_cmd.description or base_cmd.helpmsg
    name = base_cmd.name
    root_parser = ArgumentParser(prog=name, description=description)

    # Prepare the variables for the tree decend
    cmd = base_cmd
    parser = root_parser
    base_cmd_callback = None  # base_cmd.callback
    nm = Namespace(sak_callback=base_cmd_callback,
                   sak_cmd=base_cmd,
                   sak_parser=parser)

    ret = {'argparse': {}, 'ret': None}

    while True:
        cmd = SakCmdWrapper(cmd)

        for arg in cmd.args:
            arg.addToArgParser(parser)

        # Register only the next level of the subcommands
        subparsers = None
        for subcmd in cmd.subcmds:
            if subcmd is None:
                continue

            subcmdname = subcmd.name
            subcmd = SakCmdWrapper(subcmd)

            if not subcmdname:
                #TODO(witt): It makes no sense to have a subcmd without name....
                continue

            if subparsers is None:
                subparsers = parser.add_subparsers()

            description = subcmd.description or subcmd.helpmsg
            helpmsg = subcmd.helpmsg
            subcmd_callback = subcmd.callback

            sub_parser = subparsers.add_parser(subcmdname,
                                               help=helpmsg,
                                               description=description)
            sub_parser.set_defaults(sak_callback=subcmd_callback,
                                    sak_cmd=subcmd,
                                    sak_parser=sub_parser)

        rargs: List[str] = []
        success = False
        try:
            f = StringIO()
            with redirect_stderr(f):
                nm, rargs = parser.parse_known_args(args, namespace=nm)

            # Go a level down in the tree
            if (nm.sak_parser != parser) and (len(cmd.subcmds) > 0):
                args = rargs
                parser = nm.sak_parser
                cmd = nm.sak_cmd
                continue

            success = True
        except:
            # Parse failed, show error message only if it is not help command
            if not sak_show_help:
                ret['argparse']['error'] = f.getvalue()

        # Here we have consumed all the arguments and completly built the parser
        # Register auto completion
        if hasArgcomplete:
            argcomplete.autocomplete(root_parser)

        ret['cmd'] = cmd
        ret['nm'] = nm

        # We reached the leaf in the tree, but only want to get the help
        if nm.sak_callback is None:
            sak_show_help = True
        if sak_show_help:
            f = StringIO()
            with redirect_stdout(f):
                parser.print_help()

            ret['argparse']['help'] = f.getvalue()
            return ret

        # The parsing failed, so we just abort
        if not success:
            return ret

        if rargs:
            f = StringIO()
            parser.print_usage(f)
            msg = '%(usage)s\n%(prog)s: error: %(message)s\n' % {
                'usage': f.getvalue(),
                'prog': parser.prog,
                'message': 'unrecognized arguments: %s' % ' '.join(rargs),
            }
            ret['argparse']['error'] = msg
            return ret

        # Parse success and not arguments left.
        nm_dict: Dict[str, Any] = vars(nm)
        sak_cmd = nm_dict.pop('sak_cmd')
        sak_parser = nm_dict.pop('sak_parser')
        callback = nm_dict.pop('sak_callback')
        if callback:
            ret['value'] = callback(**nm_dict)

        return ret

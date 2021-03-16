# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

import functools
import inspect
import os
import re
from argparse import ArgumentParser, Namespace, RawTextHelpFormatter
from collections.abc import Iterable
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from typing import Any, Callable, Dict, List, Optional, Union, get_args, get_origin

from saklib.sakplugin import SakPlugin

hasArgcomplete = False
try:
    import argcomplete

    hasArgcomplete = True
except Exception as e:
    print("WARNING! argcomplete not supported.", str(e))


class SakDecorator:
    def __init__(self, *args: Any, **vargs: Any) -> None:
        self._sak_args = args
        self._sak_vargs = vargs
        self._sak_func: Callable[..., Any]

    def __call__(self, _sak_func: Callable[..., Any]) -> Callable[..., Any]:
        self._sak_func = _sak_func

        @functools.wraps(_sak_func)
        def wrapper(*args: Any, **vargs: Any) -> Any:
            return self._sak_func(*args, **vargs)

        wrapper._sak_dec_chain = self  # type: ignore
        return wrapper


class SakProperty(SakDecorator):
    pass


class SakCompleterArg(object):
    def __init__(
        self,
        prefix: Optional[str],
        action: Optional[Any],  # TODO: Restrict Any
        parser: Optional[Any],  # TODO: Restrict Any
        parsed_args: Optional[Namespace],
    ):
        """
        Example of parameters from argcomplete
        {
            'prefix': '',
            'action': IntrospectAction(
                            option_strings=['--account', '-a'],
                            dest='account',
                            nargs=None,
                            const=None,
                            default=None,
                            type=None,
                            choices=None,
                            help='',
                            metavar=None),
            'parser': MonkeyPatchedIntrospectiveArgumentParser(
                            prog='sak fin total',
                            usage=None,
                            description=None,
                            formatter_class=<class 'argparse.HelpFormatter'>,
                            conflict_handler='error', add_help=True),
            'parsed_args': Namespace(
                            account=None,
                            currency=None,
                            sak_callback=<bound method SakFin.total of <...>>
                            )
        }
        """
        super(SakCompleterArg, self).__init__()
        self.prefix = prefix
        self.action = action
        self.parser = parser
        self.parsed_args = parsed_args


class SakArg(SakDecorator):
    def __init__(
        self,
        name: str,
        helpmsg: str = "",
        short_name: Optional[str] = None,
        completercb: Optional[Callable[[Optional[SakCompleterArg]], List[Any]]] = None,
        **vargs: Any,
    ) -> None:
        super(SakArg, self).__init__()
        self.name = name
        self.helpmsg = helpmsg
        self.short_name = short_name
        self.vargs = vargs
        self.completercb = completercb

    def addToArgParser(self, parser: ArgumentParser) -> None:
        pargs = []
        pargs += ["--%s" % self.name]
        if self.short_name:
            pargs += ["-%s" % self.short_name]

        # TODO(witt): I think add_argument should accept the argument type.
        vargs = {}
        vargs.update(self.vargs)
        if "type" in vargs:
            _type = vargs.pop("type")
            if _type is not bool:
                vargs["type"] = _type

        aux = parser.add_argument(*pargs, help=self.helpmsg, **vargs)

        completercb = self.completercb
        if hasArgcomplete and (completercb is not None):

            def completercbWrapper(**vargs: Any) -> List[Any]:
                arg = SakCompleterArg(
                    prefix=vargs["prefix"],
                    action=vargs["action"],
                    parser=vargs["parser"],
                    parsed_args=vargs["parsed_args"],
                )
                return completercb(arg)  # type: ignore

            aux.completer = completercbWrapper  # type: ignore


class SakCmd(SakDecorator):
    EXP_CLI = "cli"
    EXP_WEB = "web"

    def __init__(
        self, name: str = "", expose: List[str] = [], helpmsg: str = ""
    ) -> None:
        super(SakCmd, self).__init__()

        self.name = name
        self.callback = None
        self.subcmds: List[Union[SakCmd, SakPlugin]] = []

        # TODO(witt): Can this be more specific?
        self.args: List[Any] = []

        self.helpmsg = helpmsg
        self.description = None


class SakCmdWrapper:
    def __init__(
        self,
        wrapped_content: Optional[
            Union["SakCmdWrapper", SakPlugin, SakCmd, Callable[..., Any]]
        ] = None,
        name: Optional[str] = None,
        callback: Optional[Callable[[Any], Any]] = None,
        args: Optional[List[SakArg]] = None,
        helpmsg: Optional[str] = None,
        subcmds: Optional[List[Any]] = None,  # TODO: Make this more specific
    ):
        assert name != "0"

        self._wrapped_content = wrapped_content
        self._name = name
        self._callback = callback

        self._subcmds: List[SakCmd] = []
        if subcmds is not None:
            self._subcmds = subcmds

        self._args = args or []
        self._helpmsg = helpmsg
        self._description = helpmsg
        # self._cmd = cmd
        self._cmd: Optional[SakCmd] = None

        d = wrapped_content

        if isinstance(d, SakCmdWrapper):
            self._wrapped_content = d._wrapped_content
            self._name = d._name
            self._callback = d._callback
            self._subcmds = d._subcmds
            self._args = d._args
            self._helpmsg = d._helpmsg
            self._description = d._description
            self._cmd = d._cmd
        elif isinstance(d, SakCmd):
            self._cmd = d

        if self.name is None:
            raise Exception("I failed to infer the name")

    def __str__(self) -> str:
        return f"<{self.name} {self.callback}>"

    def __repr__(self) -> str:
        return str(self)

    @property
    def name(self) -> Optional[str]:
        cmd = self.cmd
        if cmd:
            if cmd.name:
                return cmd.name

        if self._name:
            return self._name

        d = self._wrapped_content

        if isinstance(d, SakPlugin):
            return d.name

        if (
            (d is not None)
            and (not isinstance(d, SakCmdWrapper))
            and (not isinstance(d, SakCmd))
        ):
            if inspect.ismethod(d) or inspect.isfunction(d):
                return d.__name__

        return None

    @property
    def callback(self) -> Optional[Callable[[Any], Any]]:
        if self._callback:
            return self._callback

        if self._wrapped_content:
            d = self._wrapped_content

            for plain_type in [str, int, float]:
                if isinstance(d, plain_type):
                    return lambda **x: d

            if not isinstance(d, SakDecorator):
                if callable(d):  # inspect.ismethod(d) or inspect.isfunction(d):
                    return d

                # TODO(witt): I dont think I should return the result from the callback here :/
                # return SakCmdWrapper(
                #        callback = lambda **x: cb()
                #        ) #{ '_sak_cmd_callback': lambda **x: cb(), '_sak_cmd':None, '_sak_cmd_args':[] }
        return None

    @property
    def subcmds(self) -> List["SakCmdWrapper"]:
        if self._subcmds:
            return [SakCmdWrapper(x) for x in self._subcmds]

        cmd = self.cmd
        if cmd:
            if cmd.subcmds:
                return [SakCmdWrapper(x) for x in cmd.subcmds]
            else:
                return []

        if self._wrapped_content:
            d = self._wrapped_content

            if isinstance(d, dict):
                subcmds = []
                for k, v in d.items():
                    if k == "sak_subcmds":
                        if isinstance(v, dict):
                            subcmds += [
                                SakCmdWrapper(wrapped_content=y, name=x)
                                for x, y in v.items()
                            ]
                            continue
                        elif isinstance(v, list):
                            subcmds += [SakCmdWrapper(wrapped_content=x) for x in v]
                            continue

                    if hasattr(v, "_sak_dec_chain"):
                        k = v.__name__
                    # elif hasattr(v, 'name'):
                    #    k = v.name

                    if k.startswith("_"):
                        continue
                        # TODO(witt): Maybe it makes no sense to try to add a private subcommand. It
                        #             was failing because it tried to add the __doc__.
                        # subcmds.append(SakCmdWrapper(wrapped_content=v))
                    else:
                        subcmds.append(SakCmdWrapper(wrapped_content=v, name=k))

                if subcmds:
                    return subcmds

            if isinstance(d, Iterable):
                subcmds = []
                for idx, v in enumerate(d):
                    k = str(idx)
                    # if hasattr(v, "_sak_dec_chain"): #TODO(witt): What is the impact of this change?
                    if hasattr(v, "__name__"):
                        k = v.__name__
                    try:
                        k = v.name
                    except Exception as e:
                        print(
                            "WARNING! I am trying to access the name attribute but failed.",
                            str(e),
                        )
                    subcmds.append(SakCmdWrapper(wrapped_content=v, name=k))
                if subcmds:
                    return subcmds

            if True:
                subcmds = []
                for k in dir(d):
                    if k.startswith("_sak_unamed_expose_"):
                        dd = getattr(d, k)
                        subcmds.append(SakCmdWrapper(wrapped_content=dd))
                        continue

                    if k.startswith("_"):
                        continue

                    try:
                        dd = getattr(d, k)

                        dd = SakCmdWrapper(wrapped_content=dd, name=k)
                        subcmds.append(dd)
                        continue
                    except Exception as e:
                        # TODO(witt): Just does not add because of failure.
                        print("skip", k, str(e))
                        import sys
                        import traceback

                        print("Exception in user code:")
                        print("-" * 60)
                        traceback.print_exc(file=sys.stdout)
                        print("-" * 60)
                        continue

                if subcmds:
                    return subcmds

        return []

    @property
    def args(self) -> List[SakArg]:
        if self._args:
            return self._args

        if self._wrapped_content:
            d = self._wrapped_content

            if callable(d) and not isinstance(d, SakCmd):
                d_list = [d]
                if hasattr(d, "__call__"):
                    # TODO(witt): Fix this ignore?
                    d_list.append(d.__call__)  # type: ignore

                _params = {}

                _docs = {}

                docstring = inspect.getdoc(d)
                if docstring:
                    docs = inspect.cleandoc(docstring)
                    for name, doc in re.findall(r"^:(\S+): ([\S \t]+)$", docs, re.M):
                        _docs[name] = doc.strip()

                for _d in d_list:
                    # Instrospect the function signature
                    signature = inspect.signature(_d)
                    for param_name, param in signature.parameters.items():

                        if param_name.startswith("_sak_"):
                            continue

                        if str(param.kind) != "POSITIONAL_OR_KEYWORD":
                            continue

                        if param_name not in _params:
                            _helpmsg = ""
                            if param_name in _docs:
                                _helpmsg = _docs[param_name]
                            _params[param_name] = SakArg(
                                name=param_name, helpmsg=_helpmsg
                            )

                        # TODO(witt): Fix this ignore?
                        if param.default is not inspect._empty:  # type: ignore
                            _params[param_name].vargs["default"] = param.default
                            _params[param_name].vargs["required"] = False
                        else:
                            _params[param_name].vargs["required"] = True

                        # TODO(witt): Fix this ignore?
                        if param.annotation is not inspect._empty:  # type: ignore
                            _params[param_name].vargs["type"] = param.annotation

                        _type = _params[param_name].vargs.get("type", None)
                        _default = _params[param_name].vargs.get("default", None)

                        if _type is bool or isinstance(_default, bool):
                            _params[param_name].vargs["action"] = "store_true"
                            if _default is True:
                                _params[param_name].vargs["action"] = "store_false"

                        if _type is list or isinstance(_default, list):
                            _params[param_name].vargs.get("default", [])
                            _params[param_name].vargs["action"] = "append"

                        if get_origin(_type) is list:
                            _params[param_name].vargs["action"] = "append"
                            # TODO(witt): What to do when we have more then one argument?
                            _params[param_name].vargs["type"] = get_args(_type)[0]
                            if len(get_args(_type)) > 1:
                                raise Exception(
                                    "Sak does not support multiple type annotation?!"
                                )

                    # Check if there are decorators and override the info from the decorator.
                    if hasattr(_d, "_sak_dec_chain"):
                        chain = _d._sak_dec_chain  # type: ignore
                        while chain is not None:
                            if isinstance(chain, SakArg):
                                if chain.name not in _params:
                                    _params[chain.name] = chain

                                if chain.helpmsg is not None:
                                    _params[chain.name].helpmsg = chain.helpmsg
                                if chain.short_name:
                                    _params[chain.name].short_name = chain.short_name
                                if chain.completercb is not None:
                                    _params[chain.name].completercb = chain.completercb
                                _params[chain.name].vargs.update(chain.vargs)

                            if hasattr(chain._sak_func, "_sak_dec_chain"):
                                chain = chain._sak_func._sak_dec_chain
                            else:
                                chain = None

                # If there is any parameter then return it.
                if _params:
                    return list(_params.values())

        return []

    @property
    def helpmsg(self) -> str:
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

        if isinstance(d, dict):
            if "__doc__" in d:
                return (d["__doc__"] or "").strip()

        if isinstance(d, SakPlugin):
            plugin_helpmsg = d.helpmsg
            if plugin_helpmsg:
                return plugin_helpmsg

            docstring = inspect.getdoc(d)
            if docstring:
                lines = inspect.cleandoc(docstring).strip().splitlines()
                if lines:
                    return lines[0]

        # TODO(witt): How about __call__?
        if inspect.ismethod(d) or inspect.isfunction(d):
            docstring = inspect.getdoc(d)
            if docstring:
                lines = inspect.cleandoc(docstring).strip().splitlines()
                if lines:
                    return lines[0]

        # TODO(witt): I did my best to get the help message, but no success
        return ""

    @property
    def description(self) -> Optional[str]:
        if self._description:
            return self._description

        d = self._wrapped_content
        if isinstance(d, SakPlugin):
            docstring = inspect.getdoc(d)
            if docstring:
                return docstring

        if inspect.ismethod(d) or inspect.isfunction(d):
            docstring = inspect.getdoc(d)
            if docstring:
                lines = inspect.cleandoc(docstring).strip().splitlines()

                _description_lines = []
                for line in lines:
                    if line.startswith(":"):
                        break

                    _description_lines.append(line)

                if _description_lines:
                    return ("\n".join(_description_lines)).strip()

        return None

    @property
    def cmd(self) -> Optional[SakCmd]:
        if self._cmd:
            return self._cmd

        if self._wrapped_content:
            d = self._wrapped_content

            if isinstance(d, SakCmd):
                return d

            if inspect.ismethod(d) or inspect.isfunction(d):
                if hasattr(d, "_sak_dec_chain"):
                    cmd = None
                    chain = d._sak_dec_chain  # type: ignore
                    while chain is not None:
                        if isinstance(chain, SakCmd):
                            cmd = chain
                        if hasattr(chain._sak_func, "_sak_dec_chain"):
                            chain = chain._sak_func._sak_dec_chain
                        else:
                            chain = None
                    if cmd:
                        return cmd
        return None


def argcomplete_args() -> List[str]:
    args: List[str] = []
    # Check if its auto completion
    # is_in_completion = False
    comp_line = os.environ.get("COMP_LINE", None)
    if comp_line is not None:
        # What is this COMP_POINT?
        comp_point = int(os.environ.get("COMP_POINT", 0))
        # is_in_completion = True
        _, _, _, comp_words, _ = argcomplete.split_line(comp_line, comp_point)
        if not args:
            args = comp_words[1:]
    return args


def sak_arg_parser(root: Any, args: Optional[List[str]] = None) -> Dict[str, Any]:
    args = args or argcomplete_args()

    base_cmd = SakCmdWrapper(wrapped_content=root)

    # Remove the help flag from args and set show_help
    args = args or []
    sak_show_help = False
    if ("-h" in args) or ("--help" in args):
        sak_show_help = True
        args = [x for x in args if x != "-h" and x != "--help"]

    # The root parser
    description = base_cmd.description or base_cmd.helpmsg
    name = base_cmd.name
    root_parser = ArgumentParser(
        prog=name, description=description, formatter_class=RawTextHelpFormatter
    )

    # Prepare the variables for the tree decend
    cmd: Union[SakCmd, SakCmdWrapper] = base_cmd
    parser = root_parser
    base_cmd_callback = base_cmd.callback
    nm = Namespace(sak_callback=base_cmd_callback, sak_cmd=base_cmd, sak_parser=parser)

    ret: Dict[str, Any] = {"argparse": {}, "ret": None}

    while True:
        if not isinstance(cmd, SakCmdWrapper):
            cmd = SakCmdWrapper(cmd)

        for arg in cmd.args:
            arg.addToArgParser(parser)

        # Register only the next level of the subcommands
        subparsers = None
        for subcmd in cmd.subcmds:
            if subcmd is None:
                continue

            # TODO(witt): I can activate something like this is the tree is too big...
            if args:
                # TODO(witt): Does it make sense at all to have a command with null name?
                if subcmd.name is not None:
                    if not subcmd.name.startswith(args[0]):
                        continue

            subcmdname = subcmd.name

            if not isinstance(subcmd, SakCmdWrapper):
                subcmd = SakCmdWrapper(subcmd)

            if not subcmdname:
                # TODO(witt): It makes no sense to have a subcmd without name....
                continue

            if subparsers is None:
                subparsers = parser.add_subparsers()

            description = subcmd.description or subcmd.helpmsg
            helpmsg = subcmd.helpmsg
            subcmd_callback = subcmd.callback

            sub_parser = subparsers.add_parser(
                subcmdname,
                help=helpmsg,
                description=description,
                formatter_class=RawTextHelpFormatter,
            )
            sub_parser.set_defaults(
                sak_callback=subcmd_callback, sak_cmd=subcmd, sak_parser=sub_parser
            )

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

                # Flush the namespace to go a level down.
                nm = Namespace(
                    sak_callback=nm.sak_callback,
                    sak_cmd=nm.sak_cmd,
                    sak_parser=nm.sak_parser,
                )

                continue

            success = True
        except Exception as e:
            # Parse failed, show error message only if it is not help command
            if not sak_show_help:
                ret["argparse"]["error"] = f.getvalue()
            else:
                print(
                    "ERROR! Something bad happened while iterating in the command tree.",
                    str(e),
                )

        # Here we have consumed all the arguments and completly built the parser
        # Register auto completion
        if hasArgcomplete:
            argcomplete.autocomplete(root_parser)

        ret["cmd"] = cmd
        ret["nm"] = nm

        # We reached the leaf in the tree, but only want to get the help
        if nm.sak_callback is None:
            sak_show_help = True
        if sak_show_help:
            f = StringIO()
            with redirect_stdout(f):
                parser.print_help()

            ret["argparse"]["help"] = f.getvalue()
            return ret

        # The parsing failed, so we just abort
        if not success:
            return ret

        if rargs:
            f = StringIO()
            parser.print_usage(f)
            msg = "%(usage)s\n%(prog)s: error: %(message)s\n" % {
                "usage": f.getvalue(),
                "prog": parser.prog,
                "message": "unrecognized arguments: %s" % " ".join(rargs),
            }
            ret["argparse"]["error"] = msg
            return ret

        # Parse success and not arguments left.
        nm_dict: Dict[str, Any] = vars(nm)
        nm_dict.pop("sak_cmd")
        nm_dict.pop("sak_parser")
        callback = nm_dict.pop("sak_callback")

        ret["value"] = None

        if callback:
            # import pdb; pdb.set_trace()
            try:
                ret["value"] = callback(**nm_dict)
            except Exception as e:
                # TODO(witt): Implement some verbose option that allows to view the whole stack call
                verbose = True
                if verbose:
                    import sys
                    import traceback

                    print("Exception in user code:")
                    print("-" * 60)
                    traceback.print_exc(file=sys.stdout)
                    print("-" * 60)
                print(e)

        return ret

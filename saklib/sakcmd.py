# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__version__ = "0.0.0"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"


import argparse

hasArgcomplete = True
try:
    import argcomplete
except:
    hasArgcomplete = False

class SakArg(object):
    def __init__(self, name, helpmsg='', short_name=None, positional=False, completercb=None, **vargs):
        super(SakArg, self).__init__()
        self.name = name
        self.helpmsg = helpmsg
        self.short_name = short_name
        self.vargs = vargs
        self.positional = positional
        self.completercb = completercb

    def addToArgParser(self, parser):
        pargs = []
        if not self.positional:
            pargs += ['--%s' % self.name]
            if self.short_name:
                pargs += ['-%s' % self.short_name]
        else:
            pargs = [self.name]

        aux = parser.add_argument(*pargs, help=self.helpmsg, **self.vargs)

        if self.completercb:
            aux.completer = self.completercb


class SakCmd(object):
    EXP_CLI = 'cli'
    EXP_WEB = 'web'

    def __init__(self, name, callback=None, args=None, expose=[]):
        super(SakCmd, self).__init__()
        self.name = name
        self.callback = callback
        self.subcmds = []
        self.args = args or []

        self.parent = None
        self.expose = expose or [SakCmd.EXP_CLI]

    def addSubCmd(self, subcmd):
        subcmd.setParent(self)
        self.subcmds.append(subcmd)

    def addExpose(self, expose=[]):
        for exp in expose:
            if exp not in self.expose:
                self.expose.append(exp)
        if self.parent:
            self.parent.addExpose(expose)

    def setParent(self, parent):
        self.parent = parent
        self.addExpose(self.expose)

    def addArg(self, arg):
        self.args.append(arg)

    def generateArgParse(self, parser=None):
        if parser == None:
            parser = argparse.ArgumentParser(prog=self.name)
        else:
            parser = parser.add_parser(self.name, help='TODO')

        parser.set_defaults(sak_callback=self.callback)

        for arg in self.args:
            arg.addToArgParser(parser)

        if self.subcmds:
            subparsers = parser.add_subparsers()
            for subcmd in self.subcmds:
                subcmd.generateArgParse(subparsers)

        return parser

    def runArgParser(self):
        parser = self.generateArgParse()

        if hasArgcomplete:
            argcomplete.autocomplete(parser)

        args = vars(parser.parse_args())
        callback = args.pop('sak_callback')
        if callback:
            ret = callback(**args)
            if isinstance(ret, str):
                # TODO: Standardize the output from the plugin endpoints!
                print(ret)


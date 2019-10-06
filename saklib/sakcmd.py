# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__version__ = "0.0.0"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"


import argparse
import argcomplete

class SakArg(object):
    def __init__(self, name, helpmsg='', short_name=None, positional=False, **vargs):
        super(SakArg, self).__init__()
        self.name = name
        self.helpmsg = helpmsg
        self.short_name = short_name
        self.vargs = vargs
        self.positional = positional

    def addToArgParser(self, parser):
        pargs = []
        if not self.positional:
            pargs += ['--%s' % self.name]
            if self.short_name:
                pargs += ['-%s' % self.short_name]
        else:
            pargs = [self.name]

        parser.add_argument(*pargs, help=self.helpmsg, **self.vargs)

class SakCmd(object):
    def __init__(self, name, callback=None, args=None):
        super(SakCmd, self).__init__()
        self.name = name
        self.callback = callback
        self.subcmds = []
        self.args = args or []

        self.parent = None

    def addSubCmd(self, subcmd):
        subcmd.setParent(self)
        self.subcmds.append(subcmd)

    def setParent(self, parent):
        self.parent = parent

    def addArg(self, arg):
        self.args.append(arg)

    def generateArgParse(self, parser=None):
        if parser==None:
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

        argcomplete.autocomplete(parser)

        args = vars(parser.parse_args())
        callback = args.pop('sak_callback')
        if callback:
            callback(**args)


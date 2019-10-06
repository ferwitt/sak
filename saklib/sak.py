#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__version__ = "0.0.0"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

from sakcmd import SakCmd, SakArg
from sakplugin import SakPlugin, SakPluginManager
import os
import subprocess

class Sak(SakPlugin):
    def __init__(self):
        super(Sak, self).__init__('Sak')

    def show_version(self, **vargs):
        print('Version: %s' % (__version__))

    def show_argcomp(self, **vargs):
        subprocess.call(['register-python-argcomplete', 'sak', '-s', 'bash'])

    def exportCmds(self, base):
        show = SakCmd('show')

        show.addSubCmd(SakCmd('argcomp', self.show_argcomp))
        show.addSubCmd(SakCmd('version', self.show_version))

        base.addSubCmd(show)

def main():
    plm = SakPluginManager()

    plm.addPlugin(Sak())

    root = plm.generateCommandsTree()

    root.runArgParser()


if __name__ == "__main__":
    main()

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
from sakcontext import SakContext

import os
import sys
import subprocess


class Sak(SakPlugin):
    def __init__(self):
        super(Sak, self).__init__('sak')

    def show_version(self, **vargs):
        return 'Version: %s' % (__version__)

    def show_argcomp(self, **vargs):
        subprocess.call(['register-python-argcomplete', 'sak', '-s', 'bash'])

    def exportCmds(self, base):
        show = SakCmd('show')

        show.addSubCmd(SakCmd('argcomp', self.show_argcomp))
        show.addSubCmd(SakCmd('version', self.show_version, expose=[SakCmd.EXP_CLI, SakCmd.EXP_WEB]))

        base.addSubCmd(show)


class SakPlugins(SakPlugin):
    def __init__(self):
        super(SakPlugins, self).__init__('plugins')

    def show(self, **vargs):
        for plugin in self.context.getPluginManager().getPluginList():
            print(plugin.name, plugin.path)

    def exportCmds(self, base):
        show = SakCmd('plugins')

        show.addSubCmd(SakCmd('show', self.show))

        base.addSubCmd(show)


def main():

    ctx = SakContext()

    plm = SakPluginManager(ctx)

    plm.addPlugin(Sak())
    plm.addPlugin(SakPlugins())

    if ctx.sak_global:
        sys.path.append(os.path.join(ctx.sak_global, 'plugins'))
        plm.loadPlugins(os.path.join(ctx.sak_global, 'plugins'))
    if ctx.sak_local and ctx.sak_local != ctx.sak_global:
        sys.path.append(os.path.join(ctx.sak_local, 'plugins'))
        plm.loadPlugins(os.path.join(ctx.sak_local, 'plugins'))

    root = plm.generateCommandsTree()

    root.runArgParser()


if __name__ == "__main__":
    main()

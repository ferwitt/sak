#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__version__ = "0.0.0"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

from sakcmd import SakCmd, SakArg
from sakplugin import SakPlugin, SakPluginManager, SakContext

import os
import sys
import subprocess
from pathlib import Path

from typing import Optional


class Sak(SakPlugin):
    def __init__(self) -> None:
        super(Sak, self).__init__('sak')

    def getPath(self) -> Optional[Path]:
        return self.context.sak_global

    def show_version(self, **vargs):
        return 'Version: %s' % (__version__)

    def show_argcomp(self, **vargs):
        subprocess.call(['register-python-argcomplete', 'sak', '-s', 'bash'])

    def bash(self, **vargs):
        os.system('bash')

    def exportCmds(self, base):
        bash = SakCmd('bash', self.bash)
        base.addSubCmd(bash)

        show = SakCmd('show')

        show.addSubCmd(SakCmd('argcomp', self.show_argcomp))
        show.addSubCmd(SakCmd('version', self.show_version, expose=[SakCmd.EXP_CLI, SakCmd.EXP_WEB]))

        base.addSubCmd(show)


class SakPlugins(SakPlugin):
    def __init__(self) -> None:
        super(SakPlugins, self).__init__('plugins')

    def show(self, **vargs):
        for plugin in self.context.getPluginManager().getPluginList():
            # TODO: Remove this print
            print(plugin.name, plugin.getPath())

    def install(self, url, **vargs):
        subprocess.run(['git', 'clone', url],
                       check=True,
                       cwd=os.path.join(self.context.sak_global, 'plugins'))

    def update(self, **vargs):
        for plugin in self.context.getPluginManager().getPluginList():
            if plugin == self:
                continue
            print(80*'-')
            print('Updating %s' % plugin.name)
            plugin.update()

    def exportCmds(self, base):
        plugins = SakCmd('plugins')

        plugins.addSubCmd(SakCmd('show', self.show))

        install = SakCmd('install', self.install)
        install.addArg(SakArg('url', required=True))
        plugins.addSubCmd(install)

        update = SakCmd('update', self.update)
        plugins.addSubCmd(update)

        base.addSubCmd(plugins)


def main() -> None:

    ctx = SakContext()

    plm = SakPluginManager(ctx)

    plm.addPlugin(Sak())
    plm.addPlugin(SakPlugins())

    if ctx.sak_global:
        sys.path.append(ctx.sak_global / 'plugins')
        plm.loadPlugins(ctx.sak_global / 'plugins')
    if ctx.sak_local and ctx.sak_local != ctx.sak_global:
        sys.path.append(ctx.sak_local / 'plugins')
        plm.loadPlugins(ctx.sak_local / 'plugins')

    root = plm.generateCommandsTree()

    root.runArgParser()


if __name__ == "__main__":
    main()

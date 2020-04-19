#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__version__ = "0.0.0"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

from sakcmd import SakCmd, SakArg, SakCmdCtx, SakCmdRet
from sakplugin import onto, SakPlugin, SakPluginManager, SakContext

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

    def show_version(self, ctx: SakCmdCtx) -> SakCmdRet:
        ret = ctx.get_ret()
        ret.retValue = 'Version: %s' % (__version__)
        return ret

    def show_argcomp(self, ctx: SakCmdCtx) -> SakCmdRet:
        subprocess.call(['register-python-argcomplete', 'sak', '-s', 'bash'])
        #TODO: Fix this
        return ctx.get_ret()

    def bash(self, ctx: SakCmdCtx) -> SakCmdRet:
        os.system('bash')
        #TODO: Fix this!
        return ctx.get_ret()

    def exportCmds(self, base: SakCmd) -> None:
        bash = SakCmd('bash', self.bash, helpmsg='Start a bash using the SAK env variables.')
        base.addSubCmd(bash)

        show = SakCmd('show', helpmsg='General information about SAK.')

        show.addSubCmd(SakCmd('argcomp', self.show_argcomp, helpmsg='Show the autocomplete string'))
        show.addSubCmd(SakCmd('version', self.show_version, expose=[SakCmd.EXP_CLI, SakCmd.EXP_WEB], helpmsg='Show SAK version.'))

        base.addSubCmd(show)


class SakPlugins(SakPlugin):
    def __init__(self) -> None:
        super(SakPlugins, self).__init__('plugins')

    def show(self, ctx: SakCmdCtx) -> SakCmdRet:
        ret = ctx.get_ret()
        ret.retValue = ''
        for plugin in self.context.getPluginManager().getPluginList():
            ret.retValue += 'name: %s\n\tpath: %s\n' % (plugin.name, plugin.getPath())
        return ret

    def install(self, ctx: SakCmdCtx) -> SakCmdRet:
        if self.context.sak_global is not None:
            url = ctx.kwargs['url']
            name = url.split('/')[-1].replace('.git', '').replace('-', '_')
            subprocess.run(['git', 'clone', url, name],
                           check=True,
                           cwd=(self.context.sak_global / 'plugins'))

        return ctx.get_ret()

    def doUpdate(self, ctx: SakCmdCtx) -> SakCmdRet:
        ret = ctx.get_ret()

        for plugin in self.context.getPluginManager().getPluginList():
            if plugin == self:
                continue

            # TODO: Remove print!
            ctx.stdout.write(80*'-' + '\n')
            ctx.stdout.write('Updating %s\n' % plugin.name)
            plugin.update()

        return ret

    def exportCmds(self, base: SakCmd) -> None:
        plugins = SakCmd('plugins', helpmsg='Plugin manager.')

        plugins.addSubCmd(SakCmd('show', self.show, helpmsg='Show the list of plugins.'))

        install = SakCmd('install', self.install, helpmsg='Install a new plugin.')
        install.addArg(SakArg('url', required=True, helpmsg='The plugin git repo URL.'))
        plugins.addSubCmd(install)

        update = SakCmd('update', self.doUpdate, helpmsg='Update SAK and all the plugins.')
        plugins.addSubCmd(update)

        base.addSubCmd(plugins)


def main() -> None:

    ctx = SakContext()

    plm = SakPluginManager()

    ctx.has_plugin_manager = plm
    plm.has_context = ctx

    plm.addPlugin(Sak())
    plm.addPlugin(SakPlugins())

    if ctx.sak_global:
        sys.path.append(str(ctx.sak_global / 'plugins'))
        plm.loadPlugins(ctx.sak_global / 'plugins')
    if ctx.sak_local and ctx.sak_local != ctx.sak_global:
        sys.path.append(str(ctx.sak_local / 'plugins'))
        plm.loadPlugins(ctx.sak_local / 'plugins')

    onto.save()

    root = plm.generateCommandsTree()

    root.runArgParser()


if __name__ == "__main__":
    if True:
        main()
    else:
        import cProfile
        cProfile.run('main()', '/tmp/sak.profile')

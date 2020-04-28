#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__version__ = "0.0.0"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

from sakcmd import SakCmd, SakArg, SakCmdCtx, SakCmdRet, sak_arg_parser
from sakplugin import onto, SakPlugin, SakPluginManager, SakContext

import os
import sys
import subprocess
from pathlib import Path

from typing import Optional


class SakShow(SakPlugin):
    '''General information about SAK.'''
    namespace = onto

    def __init__(self, name, **kwargs) -> None:
        super(SakShow, self).__init__(name, **kwargs)

    def getPath(self) -> Optional[Path]:
        return self.context.sak_global

    @SakCmd('version', expose=[SakCmd.EXP_CLI, SakCmd.EXP_WEB], helpmsg='Show SAK version.')
    def show_version(self, ctx: SakCmdCtx) -> SakCmdRet:
        ret = ctx.get_ret()
        ret.retValue = 'Version: %s' % (__version__)
        return ret

    @SakCmd('argcomp', helpmsg='Show the autocomplete string')
    def show_argcomp(self, ctx: SakCmdCtx) -> SakCmdRet:
        subprocess.call(['register-python-argcomplete', 'sak', '-s', 'bash'])
        #TODO: Fix this
        return ctx.get_ret()

    @SakCmd()
    def bash(self, ctx: SakCmdCtx) -> SakCmdRet:
        os.system('bash')
        #TODO: Fix this!
        return ctx.get_ret()

    #def exportCmds(self, base: SakCmd) -> None:
    #    bash = SakCmd('bash', self.bash, helpmsg='Start a bash using the SAK env variables.')
    #    base.addSubCmd(bash)


class SakPlugins(SakPlugin):
    '''Plugin manager.'''

    namespace = onto
    def __init__(self, name, **kwargs) -> None:
        super(SakPlugins, self).__init__(name, **kwargs)

    @SakCmd('show', helpmsg='Show the list of plugins.')
    def show(self, ctx: SakCmdCtx) -> SakCmdRet:
        ret = ctx.get_ret()
        ret.retValue = ''
        for plugin in self.context.getPluginManager().getPluginList():
            ret.retValue += 'name: %s\n\tpath: %s\n' % (plugin.name, plugin.getPath())
        return ret

    @SakCmd('install', helpmsg='Install a new plugin.')
    @SakArg('url', required=True, helpmsg='The plugin git repo URL.')
    def install(self, ctx: SakCmdCtx) -> SakCmdRet:
        if self.context.sak_global is not None:
            url = ctx.kwargs['url']
            name = url.split('/')[-1].replace('.git', '').replace('-', '_')
            subprocess.run(['git', 'clone', url, name],
                           check=True,
                           cwd=(self.context.sak_global / 'plugins'))

        return ctx.get_ret()

    @SakCmd('update', helpmsg='Update SAK and all the plugins.')
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

def main() -> None:

    ctx = SakContext()

    plm = SakPluginManager()

    ctx.has_plugin_manager = plm
    plm.has_context = ctx

    plm.addPlugin(SakShow('show'))
    plm.addPlugin(SakPlugins('plugins'))

    if ctx.sak_global:
        sys.path.append(str(ctx.sak_global / 'plugins'))
        plm.loadPlugins(ctx.sak_global / 'plugins')
    if ctx.sak_local and ctx.sak_local != ctx.sak_global:
        sys.path.append(str(ctx.sak_local / 'plugins'))
        plm.loadPlugins(ctx.sak_local / 'plugins')


    root = plm.generateCommandsTree()

    sak_arg_parser(root, sys.argv[1:])


if __name__ == "__main__":
    if False:
        main()
    else:
        import cProfile
        cProfile.run('main()', '/tmp/sak.profile')

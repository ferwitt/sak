#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__version__ = "0.0.0"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

from sakcmd import SakCmd, SakArg, sak_arg_parser
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
    def show_version(self) -> str:
        return 'Version: %s' % (__version__)

    @SakCmd('argcomp', helpmsg='Show the autocomplete string')
    def show_argcomp(self) -> None:
        subprocess.call(['register-python-argcomplete', 'sak', '-s', 'bash'])
        return None

    @SakCmd()
    def bash(self):
        os.system('bash')
        #TODO: Fix this!
        return None


class SakPlugins(SakPlugin):
    '''Plugin manager.'''

    namespace = onto
    def __init__(self, name, **kwargs) -> None:
        super(SakPlugins, self).__init__(name, **kwargs)

    @SakCmd('show', helpmsg='Show the list of plugins.')
    def show(self) -> str:
        ret = ''
        for plugin in self.context.getPluginManager().getPluginList():
            ret += 'name: %s\n\tpath: %s\n' % (plugin.name, plugin.getPath())
        return ret

    @SakCmd('install', helpmsg='Install a new plugin.')
    @SakArg('url', required=True, helpmsg='The plugin git repo URL.')
    def install(self, url:str) -> None:
        if self.context.sak_global is not None:
            name = url.split('/')[-1].replace('.git', '').replace('-', '_')
            subprocess.run(['git', 'clone', url, name],
                           check=True,
                           cwd=(self.context.sak_global / 'plugins'))


    @SakCmd('update', helpmsg='Update SAK and all the plugins.')
    def doUpdate(self):
        for plugin in self.context.getPluginManager().getPluginList():
            if plugin == self:
                continue

            print(80*'-' + '\n')
            print('Updating %s\n' % plugin.name)
            plugin.update()

def get_context() -> SakContext:
    ctx = SakContext()

    plm = SakPluginManager()

    ctx.plugin_manager = plm
    plm.context = ctx

    plm.addPlugin(SakShow('show'))
    plm.addPlugin(SakPlugins('plugins'))

    if ctx.sak_global:
        sys.path.append(str(ctx.sak_global / 'plugins'))
        plm.loadPlugins(ctx.sak_global / 'plugins')
    if ctx.sak_local and ctx.sak_local != ctx.sak_global:
        sys.path.append(str(ctx.sak_local / 'plugins'))
        plm.loadPlugins(ctx.sak_local / 'plugins')

    return ctx


def main() -> None:

    ctx = get_context()
    plm = ctx.plugin_manager
    root = plm.root_cmd()

    args = sys.argv[1:]
    ret = sak_arg_parser(root, args)
    
    if 'error' in ret['argparse']:
        sys.stderr.write(ret['argparse']['error'])
        sys.exit(-1)

    if 'help' in ret['argparse']:
        sys.stdout.write(ret['argparse']['help'])
        sys.exit(0)

    if ret['value'] is not None:
        if 'matplotlib.figure.Figure' in str(type(ret['value'])):
            import pylab as pl #type: ignore
            pl.show()
        else:
            print(ret['value'])


if __name__ == "__main__":
    if True:
        main()
    else:
        import cProfile
        cProfile.run('main()', '/tmp/sak.profile')

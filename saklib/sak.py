#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__version__ = "0.1.0"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional

from sakconfig import install_core_requirements

try:
    from sakcmd import SakCmd, SakArg, sak_arg_parser
    from sakonto import owl, onto
    from sakplugin import SakPlugin, SakPluginManager, SakContext
except ImportError:
    import sys, traceback
    print("Exception in user code:")
    print("-"*60)
    traceback.print_exc(file=sys.stdout)
    print("-"*60)

    # If import fails, then ask if the user wants to try to update the requirements
    install_core_requirements()


class SakShow(SakPlugin):
    '''General information about SAK.'''

    @property
    def plugin_path(self) -> Optional[Path]:
        '''Plugin path.'''
        return self.has_context.sak_global

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

    @property
    def plugin_path(self) -> Optional[Path]:
        '''Plugin path.'''
        return self.has_context.sak_global

    @SakCmd('show', helpmsg='Show the list of plugins.')
    def show(self) -> str:
        ret = ''
        for plugin in self.has_context.has_plugin_manager.has_plugins:
            ret += 'name: %s\n\tpath: %s\n' % (plugin.name, plugin.plugin_path)
        return ret

    @SakCmd('install', helpmsg='Install a new plugin.')
    @SakArg('url', required=True, helpmsg='The plugin git repo URL.')
    def install(self, url:str) -> None:
        if self.has_context.sak_global is not None:
            name = url.split('/')[-1].replace('.git', '').replace('-', '_')
            subprocess.run(['git', 'clone', url, name],
                           check=True,
                           cwd=(self.has_context.sak_global / 'plugins'))


    @SakCmd('update', helpmsg='Update SAK and all the plugins.')
    def update(self):
        for plugin in self.has_context.has_plugin_manager.getPluginList():
            if plugin == self:
                continue

            print(80*'-' + '\n')
            print('Updating %s\n' % plugin.name)
            plugin.update()

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


def root_cmd():
    root = SakCmd(
        'sak',
        helpmsg=
        "Group everyday developer's tools in a swiss-army-knife command.")
    for plugin in plm.has_plugins:
        root.subcmds.append(plugin)
    return root


def main() -> None:
    root = root_cmd()

    args = sys.argv[1:]
    ret = sak_arg_parser(root, args)
    
    if 'error' in ret['argparse']:
        sys.stderr.write(ret['argparse']['error'])
        sys.exit(-1)

    if 'help' in ret['argparse']:
        sys.stdout.write(ret['argparse']['help'])
        sys.exit(0)

    if ret['value'] is not None:
        print(type(ret['value']))

        if hasattr(ret['value'], 'show'):
            ret['value'].show()
        elif 'bokeh' in str(type(ret['value'])):
            from bokeh.plotting import show
            show(ret['value'])
        else:
            print(ret['value'])

    onto.save(
            format='ntriples'
            )
    for plugin in plm.has_plugins:
        if plugin.name in ['plugins']:
            continue
        plugin.get_ontology().save(
                format='ntriples'
                )
    owl.default_world.save()


if __name__ == "__main__":
    if True:
        main()
    else:
        import cProfile
        cProfile.run('main()', '/tmp/sak.profile')

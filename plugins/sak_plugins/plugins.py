# -*- coding: UTF-8 -*-

from sak import ctx
from sakcmd import SakCmd, SakArg

@SakCmd('show', helpmsg='Show the list of plugins.')
def show() -> str:
    ret = ''
    for plugin in ctx.has_plugin_manager.has_plugins:
        ret += 'name: %s\n\tpath: %s\n' % (plugin.name, plugin.plugin_path)
    return ret

@SakCmd('install', helpmsg='Install a new plugin.')
@SakArg('url', required=True, helpmsg='The plugin git repo URL.')
def install(url:str) -> None:
    if ctx.sak_global is not None:
        name = url.split('/')[-1].replace('.git', '').replace('-', '_')
        subprocess.run(['git', 'clone', url, name], check=True, cwd=(ctx.sak_global / 'plugins'))


@SakCmd(helpmsg='Update SAK and all the plugins.')
def update_all():
    print('Update plugins')
    for plugin in ctx.has_plugin_manager.getPluginList():
        if plugin.name == 'plugins':
            continue

        print(80*'-' + '\n')
        print('Updating %s\n' % plugin.name)
        plugin.update()


EXPOSE = {
        'show': show,
        'install': install,
        'update_all': update_all,
        }

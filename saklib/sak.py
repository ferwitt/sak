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
import sys
import subprocess


def find_in_parent(dirname, name):
    if os.path.exists(os.path.join(dirname, name)):
        return os.path.join(dirname, name)
    if os.path.dirname(dirname) != '/':
        return find_in_parent(os.path.dirname(dirname), name)
    return None

SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))
CURRENT_DIR = os.path.abspath('.')

SAK_GLOBAL = find_in_parent(SCRIPT_DIR, '.sak')
SAK_LOCAL = find_in_parent(CURRENT_DIR, '.sak')

class Sak(SakPlugin):
    def __init__(self):
        super(Sak, self).__init__('sak')

    def show_version(self, **vargs):
        print('Version: %s' % (__version__))

    def show_argcomp(self, **vargs):
        subprocess.call(['register-python-argcomplete', 'sak', '-s', 'bash'])

    def exportCmds(self, base):
        show = SakCmd('show')

        show.addSubCmd(SakCmd('argcomp', self.show_argcomp))
        show.addSubCmd(SakCmd('version', self.show_version))

        base.addSubCmd(show)

class SakPlugins(SakPlugin):
    def __init__(self):
        super(SakPlugins, self).__init__('plugins')

    def show(self, **vargs):
        for plugin in self.pluginManager.getPluginList():
            print(plugin.name, plugin.path)

    def exportCmds(self, base):
        show = SakCmd('plugins')

        show.addSubCmd(SakCmd('show', self.show))

        base.addSubCmd(show)

def main():

    plm = SakPluginManager()

    plm.addPlugin(Sak())
    plm.addPlugin(SakPlugins())

    if SAK_GLOBAL:
        sys.path.append(os.path.join(SAK_GLOBAL, 'plugins'))
        plm.loadPlugins(os.path.join(SAK_GLOBAL, 'plugins'))
    if SAK_LOCAL and SAK_LOCAL != SAK_GLOBAL:
        sys.path.append(os.path.join(SAK_LOCAL, 'plugins'))
        plm.loadPlugins(os.path.join(SAK_LOCAL, 'plugins'))

    root = plm.generateCommandsTree()

    root.runArgParser()


if __name__ == "__main__":
    main()

# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__version__ = "0.0.0"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

from sakcmd import SakCmd

class SakPlugin(object):
    def __init__(self, name):
        super(SakPlugin, self).__init__()
        self.name = name

    def exportCmds(self, base):
        pass


class SakPluginManager(object):
    def __init__(self):
        super(SakPluginManager, self).__init__()
        self.plugins = []

    def addPlugin(self, plugin):
        self.plugins.append(plugin)

    def generateCommandsTree(self):
        root = SakCmd('sak', None)
        for plugin in self.plugins:
            plugin.exportCmds(root)
        return root


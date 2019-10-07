# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__version__ = "0.0.0"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

from sakcmd import SakCmd

import os

from pathlib import Path
import inspect
import pkgutil
from importlib import import_module


class SakPlugin(object):
    def __init__(self, name):
        super(SakPlugin, self).__init__()
        self.name = name
        self.pluginManager = None
        self.path = None
        self.context = None

    def setPluginPath(self, path):
        self.path = path

    def setContext(self, context):
        self.context = context

    def exportCmds(self, base):
        pass


class SakPluginManager(object):
    def __init__(self, context):
        super(SakPluginManager, self).__init__()
        self.plugins = []
        self.context = context

        context.setPluginManager(self)

    def addPlugin(self, plugin):
        plugin.setContext(self.context)
        self.plugins.append(plugin)

    def getPluginList(self):
        return self.plugins

    def generateCommandsTree(self):
        root = SakCmd('sak', None)
        for plugin in self.plugins:
            plugin.exportCmds(root)
        return root

    def loadPlugins(self, pluginsPath=None):
        if not pluginsPath:
            return
        if not os.path.exists(pluginsPath):
            return

        for p in os.listdir(pluginsPath):
            p = os.path.join(pluginsPath, p)
            if not os.path.isdir(p):
                continue

            for (_, name, _) in pkgutil.iter_modules([Path(pluginsPath)]):
                imported_module = import_module('.plugin', package=name)

                for i in dir(imported_module):
                    attribute = getattr(imported_module, i)
                    if not inspect.isclass(attribute):
                        continue
                    if not issubclass(attribute, SakPlugin):
                        continue
                    if not SakPlugin != attribute:
                        continue

                    plugin = attribute()
                    plugin.setPluginPath(p)
                    plugin.setContext(self.context)
                    self.addPlugin(plugin)

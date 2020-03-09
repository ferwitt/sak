# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__version__ = "0.0.0"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

from sakcmd import SakCmd

import os
import sys
import subprocess

from pathlib import Path
import inspect

(PYTHON_VERSION_MAJOR, PYTHON_VERSION_MINOR, _, _, _) = sys.version_info

if PYTHON_VERSION_MAJOR == 3:
    if PYTHON_VERSION_MINOR >= 6:
        import importlib.util
    else:
        from importlib.machinery import SourceFileLoader
elif PYTHON_VERSION_MAJOR == 2:
    import imp
else:
    print('Unkown python version %d' % PYTHON_VERSION_MAJOR)
    sys.exit(-1)


class SakPlugin(object):
    def __init__(self, name):
        super(SakPlugin, self).__init__()
        self.name = name
        self.pluginManager = None
        self._path = None
        self.context = None

    def setPluginPath(self, path):
        self._path = path

    def getPath(self):
        return self._path

    def setContext(self, context):
        self.context = context

    def update(self):
        if self.getPath():
            if os.path.exists(os.path.join(self.getPath(), '.git')):
                print('Updating repository for %s' % self.name)
                subprocess.run(['git', 'remote', 'update'], check=True, cwd=self.getPath())
                subprocess.run(['git', 'pull', 'origin', 'master'], check=True, cwd=self.getPath())

            if os.path.exists(os.path.join(self.getPath(), 'requirements.txt')):
                print('Updating pip dependencies for %s' % self.name)
                subprocess.run(['pip', 'install', '-r', 'requirements.txt'], check=True, cwd=self.getPath())


class SakPluginManager(object):
    def __init__(self, context):
        super(SakPluginManager, self).__init__()
        self.plugins = []
        self.context = context

        context.setPluginManager(self)

    def getPuginByName(self, name):
        for p in self.plugins:
            if p.name == name:
                return p
        return None

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

        for name in os.listdir(pluginsPath):
            plugin_path = os.path.join(pluginsPath, name)
            if not os.path.isdir(plugin_path):
                continue

            for fname in os.listdir(plugin_path):

                fname_abs = os.path.join(plugin_path, fname)
                if not fname_abs.endswith('.py'):
                    continue
                if os.path.isdir(fname_abs):
                    continue

                try:
                    if PYTHON_VERSION_MAJOR == 3:
                        if PYTHON_VERSION_MINOR >= 6:
                            spec = importlib.util.spec_from_file_location(name, fname_abs)
                            imported_module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(imported_module)
                        else:
                            imported_module = SourceFileLoader(name, fname_abs).load_module()
                    elif PYTHON_VERSION_MAJOR == 2:
                        imported_module = imp.load_source(name, fname_abs)
                except ImportError as error:
                    print('Missing modules in plugin %s' % plugin_path)
                    print(str(error))
                    print('Please, update dependencies!')

                    requirements_path = os.path.join(plugin_path, 'requirements.txt')

                    if os.path.exists(requirements_path):
                        if input("Woud you like to do this now? [Y/N]") in ['Y', 'y', 'yes']:
                            os.system('pip install -r "%s"' % requirements_path)
                        else:
                            sys.exit(-1)

                for i in dir(imported_module):
                    attribute = getattr(imported_module, i)
                    if not inspect.isclass(attribute):
                        continue
                    if not issubclass(attribute, SakPlugin):
                        continue
                    if not SakPlugin != attribute:
                        continue

                    plugin = attribute()
                    plugin.setPluginPath(plugin_path)
                    plugin.setContext(self.context)
                    self.addPlugin(plugin)
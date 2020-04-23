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

from typing import Optional, List

PYTHON_VERSION_MAJOR = sys.version_info.major
PYTHON_VERSION_MINOR = sys.version_info.minor

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


def find_in_parent(dirname: Path, name: Path) -> Optional[Path]:
    if (dirname / name).exists():
        return dirname / name
    if dirname.parent != Path('/'):
        return find_in_parent(dirname.parent, name)
    return None


class SakContext(object):
    def __init__(self) -> None:
        super(SakContext, self).__init__()

        script_dir = Path(__file__).parent.resolve()
        current_dir = Path('.').resolve()

        self.sak_global = find_in_parent(script_dir, Path('.sak'))
        self.sak_local = find_in_parent(current_dir, Path('.sak'))

        self.pluginManager: 'SakPluginManager'

    def setPluginManager(self, pluginManager: 'SakPluginManager') -> None:
        self.pluginManager = pluginManager

    def getPluginManager(self) -> 'SakPluginManager':
        return self.pluginManager


class SakPlugin(object):
    def __init__(self, name: str) -> None:
        super(SakPlugin, self).__init__()
        self.name = name
        # self.pluginManager = None
        self._path: Optional[Path] = None
        self.context: SakContext

    def setPluginPath(self, path: Path) -> None:
        self._path = path

    def getPath(self) -> Optional[Path]:
        return self._path

    def setContext(self, context: SakContext) -> None:
        self.context = context

    def update(self) -> None:
        path = self.getPath()

        if path is not None:
            if (path / '.git').exists():
                print('Updating repository for %s' % self.name)
                subprocess.run(['git', 'remote', 'update'], check=True, cwd=path)
                subprocess.run(['git', 'pull', 'origin', 'master'], check=True, cwd=path)

            if (path / 'requirements.txt').exists():
                print('Updating pip dependencies for %s' % self.name)
                subprocess.run(['pip', 'install', '-r', 'requirements.txt'], check=True, cwd=path)

    def exportCmds(self, base: SakCmd) -> None:
        pass


class SakPluginManager(object):
    def __init__(self, context: SakContext) -> None:
        super(SakPluginManager, self).__init__()
        self.plugins: List[SakPlugin] = []
        self.context = context

        context.setPluginManager(self)

    def getPuginByName(self, name: str) -> Optional[SakPlugin]:
        for p in self.plugins:
            if p.name == name:
                return p
        return None

    def addPlugin(self, plugin: SakPlugin) -> None:
        plugin.setContext(self.context)
        self.plugins.append(plugin)

    def getPluginList(self) -> List[SakPlugin]:
        return self.plugins

    def generateCommandsTree(self) -> SakCmd:
        root = SakCmd('sak', None, helpmsg='SAK - TODO')
        for plugin in self.plugins:
            plugin.exportCmds(root)
        return root

    def loadPlugins(self, pluginsPath: Optional[Path] = None) -> None:
        if pluginsPath is None:
            return
        if not pluginsPath.exists():
            return

        for plugin_path in pluginsPath.iterdir():
            name = str(plugin_path.name)
            if not plugin_path.is_dir():
                continue

            for fname_abs in plugin_path.iterdir():
                fname = str(fname_abs.name)
                if not fname.endswith('.py'):
                    continue
                if fname_abs.is_dir():
                    continue

                try:
                    if PYTHON_VERSION_MAJOR == 3:
                        if PYTHON_VERSION_MINOR >= 6:
                            spec = importlib.util.spec_from_file_location(name, fname_abs)
                            imported_module = importlib.util.module_from_spec(spec)
                            # TODO: Fix this!
                            spec.loader.exec_module(imported_module) # type: ignore
                        else:
                            # TODO: Fix this!
                            imported_module = SourceFileLoader(name, fname_abs).load_module() # type: ignore
                    elif PYTHON_VERSION_MAJOR == 2:
                        imported_module = imp.load_source(name, str(fname_abs))
                except ImportError as error:
                    print('Missing modules in plugin %s' % str(plugin_path))
                    print(str(error))
                    print('Please, update dependencies!')

                    requirements_path = plugin_path / 'requirements.txt'

                    if os.path.exists(requirements_path):
                        if input("Woud you like to do this now? [Y/N]") in ['Y', 'y', 'yes']:
                            os.system('pip install -r "%s"' % requirements_path)
                        else:
                            print('Skip adding plugin %s' % str(plugin_path))
                            continue

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

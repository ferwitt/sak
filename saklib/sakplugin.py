# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__version__ = "0.0.0"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

from sakcmd import SakCmd
from sakconfig import SAK_GLOBAL, SAK_LOCAL

import os
import sys
import subprocess

from pathlib import Path
import inspect

from typing import Optional, List

import owlready2 as owl

owl.onto_path.append(SAK_GLOBAL)
onto = owl.get_ontology("http://test.org/sak_core.owl#")

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


class SakContext(owl.Thing):
    namespace = onto

    def __init__(self, **kwargs) -> None:
        super(SakContext, self).__init__('sak_context', **kwargs)
        self.sak_global = SAK_GLOBAL
        self.sak_local = SAK_LOCAL

    @property
    def pluginManager(self) -> 'SakPluginManager':
        return self.has_plugin_manager

    def getPluginManager(self) -> 'SakPluginManager':
        return self.has_plugin_manager


class SakPlugin(owl.Thing):
    namespace = onto

    _path: Optional[Path] = None

    def __init__(self, name, **kwargs) -> None:
        super(SakPlugin, self).__init__(name, **kwargs)

        self._ontology = None

    @property
    def ontology(self):
        if self._ontology is None:
            self._ontology = owl.get_ontology('http://127.0.0.1:2020/sak/%s.owl#' % self.name)
            try:
                self._ontology.load()
            except:
                pass
        return self._ontology

    @property
    def context(self) -> SakContext:
        return self.has_context

    def setPluginPath(self, path: Path) -> None:
        self._path = path

    def getPath(self) -> Optional[Path]:
        return self._path

    def setContext(self, context: SakContext) -> None:
        self.has_context = context

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


class SakPluginManager(owl.Thing):
    namespace = onto

with onto:
    class has_context((SakPlugin | SakPluginManager) >> SakContext, owl.FunctionalProperty):
        pass

    class has_plugin_manager(SakContext >> SakPluginManager, owl.FunctionalProperty):
        pass

    class has_plugin(SakPluginManager >> SakPlugin):
        pass

    owl.AllDisjoint([SakPlugin, SakPluginManager, SakContext])

class SakPluginManager(owl.Thing):
    namespace = onto

    def __init__(self, **kwargs) -> None:
        super(SakPluginManager, self).__init__('sak_plugin_manager', **kwargs)

    def getPuginByName(self, name: str) -> Optional[SakPlugin]:
        for p in self.has_plugin:
            if p.name == name:
                return p
        return None

    def addPlugin(self, plugin: SakPlugin) -> None:
        plugin.setContext(self.has_context)
        if plugin not in self.has_plugin:
            self.has_plugin.append(plugin)

    def getPluginList(self) -> List[SakPlugin]:
        return self.has_plugin

    def generateCommandsTree(self) -> SakCmd:
        root = SakCmd('sak', helpmsg="Group everyday developer's tools in a swiss-army-knife command.")
        for plugin in self.has_plugin:
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
                if not fname.endswith('plugin.py'):
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
                        if input("Would you like to do this now? [y/N]") in ['Y', 'y', 'yes']:
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

                    plugin = attribute(name)
                    plugin.setPluginPath(plugin_path)
                    plugin.setContext(self.has_context)
                    self.addPlugin(plugin)

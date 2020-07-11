# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

from sakconfig import SAK_GLOBAL, SAK_LOCAL, CURRENT_DIR
from sakonto import owl, onto, Sak

import os
import sys
import subprocess

from pathlib import Path
import inspect

from typing import Optional, List, Dict


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

class SakContext(object):
    '''Sak plugins context.'''
    def __init__(self, **kwargs) -> None:
        super(SakContext, self).__init__()
        self.sak_global = SAK_GLOBAL
        self.sak_local = SAK_LOCAL
        self.current_dir = CURRENT_DIR

        self.has_plugin_manager = None

class SakPlugin(object):
    def __init__(self, name, **kwargs) -> None:
        super(SakPlugin, self).__init__()
        self.name = name
        self.has_plugin_path = None
        self.has_context = None


        self._ontology = None

        local_onto = self.get_ontology()
        with local_onto:
            self.onto_declare(local_onto)

    def get_ontology(self):
        #TODO(witt): This was a property before, but then the arg_parse was
        #            trying to evaluate it, which caused the system to halt, due to some
        #            deadlock in: /owlready2/triplelite.py
        if self._ontology is None:
            self._ontology = owl.get_ontology(f'http://sak.org/sak/{self.name}.owl#')
            #self._ontology = owl.get_ontology(f'file://{SAK_GLOBAL}/{self.name}.owl#')
            try:
                self._ontology.load()
            except:
                pass
            self._ontology.imported_ontologies.append(onto)
        return self._ontology

    def onto_declare(self, local_onto):
        pass

    def onto_impl(self, local_onto):
        pass

    #def get_namespace(self, namespace):
    #    return self.get_ontology().get_namespace('http://sak.org/sak/%s' % namespace)

    @property
    def plugin_path(self) -> Optional[Path]:
        '''Plugin path.'''
        return Path(self.has_plugin_path)

    def update(self) -> None:
        path = self.plugin_path

        if path is not None:
            if (path / '.git').exists():
                print('Updating repository for %s' % self.name)
                subprocess.run(['git', 'remote', 'update'],
                               check=True,
                               cwd=path)
                subprocess.run(['git', 'pull', 'origin', 'master'],
                               check=True,
                               cwd=path)

            if (path / 'requirements.txt').exists():
                print('Updating pip dependencies for %s' % self.name)
                subprocess.run(['pip', 'install', '-r', 'requirements.txt'],
                               check=True,
                               cwd=path)


class SakPluginManager(object):
    def __init__(self, **kwargs) -> None:
        super(SakPluginManager, self).__init__()
        self.has_plugins = []
        self.has_context = None

    def get_plugin(self, name: str) -> Optional[SakPlugin]:
        for p in self.has_plugins:
            if p.name == name:
                return p
        return None

    def addPlugin(self, plugin: SakPlugin) -> None:
        plugin.has_context = self.has_context
        if plugin not in self.has_plugins:
            self.has_plugins.append(plugin)

    def getPluginList(self) -> List[SakPlugin]:
        return self.has_plugins

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
                            spec = importlib.util.spec_from_file_location(
                                name, fname_abs)
                            imported_module = importlib.util.module_from_spec(
                                spec)
                            # TODO: Fix this!
                            spec.loader.exec_module(
                                imported_module)  # type: ignore
                        else:
                            # TODO: Fix this!
                            imported_module = SourceFileLoader(
                                name, fname_abs).load_module()  # type: ignore
                    elif PYTHON_VERSION_MAJOR == 2:
                        imported_module = imp.load_source(name, str(fname_abs))
                except ImportError as error:
                    print('Missing modules in plugin %s' % str(plugin_path))
                    print(str(error))
                    print('Please, update dependencies!')

                    requirements_path = plugin_path / 'requirements.txt'

                    if os.path.exists(requirements_path):
                        if input("Would you like to do this now? [y/N]") in [
                                'Y', 'y', 'yes'
                        ]:
                            os.system('pip install -r "%s"' %
                                      requirements_path)
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

                    if name.startswith('sak_'):
                        name = name.replace('sak_', '')
                    plugin = attribute(name)
                    plugin.has_plugin_path = str(plugin_path)
                    plugin.has_context = self.has_context
                    self.addPlugin(plugin)

        for plugin in self.has_plugins:
            local_onto = plugin.get_ontology()
            with local_onto:
                plugin.onto_impl(local_onto)


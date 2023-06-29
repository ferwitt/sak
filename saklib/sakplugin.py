# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from saklib.sakconfig import CURRENT_DIR, SAK_GLOBAL, SAK_LOCAL
from saklib.sakexec import run_cmd

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
    print("Unkown python version %d" % PYTHON_VERSION_MAJOR)
    sys.exit(-1)


class SakContext(object):
    """Sak plugins context."""

    def __init__(self) -> None:
        super(SakContext, self).__init__()
        self.sak_global = SAK_GLOBAL
        self.sak_local = SAK_LOCAL
        self.current_dir = CURRENT_DIR

        self.has_plugin_manager: Optional["SakPluginManager"] = None

        self.plugin_data: Dict[str, Any] = {}


class AddPath:
    def __init__(self, path: Path) -> None:
        self.path = path

    def __enter__(self) -> None:
        sys.path.insert(0, str(self.path))

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        try:
            sys.path.remove(str(self.path))
        except ValueError:
            pass


def load_file(fpath: Path, environ: Optional[Dict[str, Any]] = None) -> Any:

    # TODO(witt): Implement some sort of auto reload. Check this as inspiration
    # https://github.com/ipython/ipython/blob/cd54f15544eee69449cc5b3e926665bda5afb9fa/IPython/extensions/autoreload.py

    # cache_pickle = Path(str(fpath) + '.pk')
    # if cache_pickle.exists():
    #    with open(cache_pickle, 'rb') as f:
    #        return pickle.load(f)

    # PLUGIN_DIR = Path(__file__).resolve().parent

    try:
        if False:
            with open(fpath) as f:
                code = compile(f.read(), str(fpath), "exec")

            global_env = {"__file__": "__sak_plugin__"}  # {'__builtins__': None}
            global_env.update(environ or {})
            # global_env.update(globals())
            # global_env.update(locals())

            # locals_env = {}
            with AddPath(str(fpath.parent)):
                exec(code, global_env, global_env)
            global_env.pop("__builtins__")
            global_env.pop("__file__")
            # print(global_env)

            # with open(cache_pickle, 'wb') as f:
            #    pickle.dump(global_env, f)

            return global_env
        else:
            imported_module = None
            name = fpath.name.replace(".py", "")
            with AddPath(fpath.parent):
                if PYTHON_VERSION_MAJOR == 3:
                    if PYTHON_VERSION_MINOR >= 6:
                        spec = importlib.util.spec_from_file_location(name, fpath)
                        assert spec is not None, f"Failed to import {name} in {fpath}"
                        imported_module = importlib.util.module_from_spec(
                            spec
                        )  # TODO: Fix this!
                        spec.loader.exec_module(imported_module)  # type: ignore
                    else:
                        # TODO: Fix this!
                        imported_module = SourceFileLoader(
                            name, str(fpath)
                        ).load_module()
                elif PYTHON_VERSION_MAJOR == 2:
                    imported_module = imp.load_source(name, str(fpath))
            ret = {}
            for k in dir(imported_module):
                ret[k] = getattr(imported_module, k)
            return ret

    except ImportError as error:
        print("Missing modules in plugin %s" % str(fpath))
        print(str(error))
        print("Please, update dependencies!")
        print("Try to execute: sak plugins update_all")

        requirements_path = fpath / "requirements.txt"

        if os.path.exists(requirements_path):
            if input("Would you like to do this now? [y/N]") in ["Y", "y", "yes"]:
                os.system('pip install --upgrade -r "%s"' % requirements_path)
            else:
                print("Skip adding plugin %s" % str(fpath))
    except Exception as e:
        import traceback

        print("Exception in user code:", str(e))
        print("-" * 60)
        traceback.print_exc(file=sys.stdout)
        print("-" * 60)
    return None


# class SakPluginExposedFile(object):


class SakPlugin:
    def __init__(
        self, context: SakContext, name: str, path: Optional[Path] = None
    ) -> None:
        self._has_context = context

        self._name = name
        self._has_plugin_path = Path(path) if path is not None else None

        self._loaded = False

        # TODO(witt): What is the value of exposed?
        self._exposed: Dict[str, Any] = {}

        self._config_file = None
        if path is not None:
            self._config_file = path / "sak_config.py"

        # TODO(witt): What to do if the config_file is not a file?
        # if not self._config_file.is_file(): continue

        # TODO(witt): Maybe I could run this in a sandbox?!
        self._config = {}
        if self._config_file is not None and self._config_file.exists():
            self._config = load_file(self._config_file)

    def _get_config(self) -> Dict[str, Any]:
        return self._config

    def _load_exposes(self) -> None:

        # TODO: This loaded should be invalidated in case the stat is newer...
        # if self._loaded: return
        self._loaded = True

        expose_files = self._config.get("EXPOSE_FILES", None)

        if isinstance(expose_files, dict):
            for expose_name, expose_file_name in expose_files.items():
                expose_file = self._has_plugin_path / expose_file_name

                if not expose_file.exists():
                    raise Exception("Could not add exposed file %s" % expose_file_name)

                imp_res = load_file(expose_file)
                if imp_res is not None:
                    exp_res = imp_res.get("EXPOSE", {})

                    if expose_name == "_":
                        if isinstance(exp_res, dict):
                            for k, v in exp_res.items():
                                self._exposed[k] = v
                        elif isinstance(exp_res, list):
                            for idx, v in enumerate(exp_res):
                                self._exposed[f"_sak_unamed_expose_{idx}"] = v
                        else:
                            self._exposed["_sak_unamed_expose_"] = exp_res
                    else:
                        if isinstance(exp_res, dict) or isinstance(exp_res, list):
                            self._exposed[expose_name] = {
                                "__doc__": imp_res.get("__doc__", ""),
                                "sak_subcmds": exp_res,
                            }
                        else:
                            self._exposed["_sak_unamed_expose_"] = exp_res
                else:
                    raise Exception("Failed to load: %s" % expose_file)

        elif isinstance(expose_files, str):
            expose_file_name = expose_files
            expose_file = self._has_plugin_path / expose_file_name

            if not expose_file.exists():
                raise Exception("Could not add exposed file %s" % expose_file_name)

            imp_res = load_file(expose_file)
            if imp_res is not None:
                exp_res = imp_res.get("EXPOSE", {})
                if isinstance(exp_res, dict):
                    for k, v in exp_res.items():
                        self._exposed[k] = v
                elif isinstance(exp_res, list):
                    for idx, v in enumerate(exp_res):
                        self._exposed[f"_sak_unamed_expose_{idx}"] = v
                else:
                    self._exposed["_sak_unamed_expose_"] = exp_res
            else:
                raise Exception("Failed to load: %s" % expose_file)

    def __dir__(self) -> Set[Any]:
        self._load_exposes()
        ret = set(self._exposed.keys()) | set(super(SakPlugin, self).__dir__())

        return ret

    def __getattr__(self, name: str) -> Any:
        self._load_exposes()
        if name in self._exposed:
            return self._exposed[name]
        return super(SakPlugin, self).__getattribute__(name)

    @property
    def _plugin_path(self) -> Optional[Path]:
        """Plugin path.

        :returns: The plugin path.
        """
        if self._has_plugin_path is not None:
            return Path(self._has_plugin_path)
        return None

    def update(self, disable_repo_update: bool = False) -> None:
        """Update the plugin.

        :param disable_repo_update: Whether should disable the plugin repository pull.
        """
        path = self._plugin_path

        if path is None:
            print(f"The plugin {self._name} has not a real path")
            return

        if path is not None:
            if not disable_repo_update:
                if (path / ".git").exists():
                    print("Updating repository for %s" % self._name)
                    run_cmd(
                        ["git", "remote", "update"],
                        check=True,
                        cwd=path,
                    )
                    run_cmd(
                        ["git", "pull", "origin", "master"],
                        check=True,
                        cwd=path,
                    )
                    run_cmd(
                        ["git", "submodule", "update", "--init", "--recursive"],
                        check=True,
                        cwd=path,
                    )

            if (path / "requirements.txt").exists():
                print("Updating pip dependencies for %s" % self._name)
                run_cmd(
                    ["pip", "install", "--upgrade", "-r", "requirements.txt"],
                    check=True,
                    cwd=path,
                )

    @property
    def __doc__(self) -> str:  # type: ignore
        v = self._config.get("__doc__") or ""
        return v.strip()

    @property
    def _helpmsg(self) -> str:
        """
        Show help message.

        :returns: The help message.
        """
        lines = self.__doc__.splitlines()
        if lines:
            return lines[0]
        return ""


class SakPluginManager(object):
    def __init__(self) -> None:
        super(SakPluginManager, self).__init__()
        self.has_plugins: List[SakPlugin] = []
        self.has_context: Optional[SakContext] = None

    def get_plugin(self, name: str) -> Optional[SakPlugin]:
        for p in self.has_plugins:
            if p._name == name:
                return p
        return None

    def addPlugin(self, plugin: SakPlugin) -> None:
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

            config_file = plugin_path / "sak_config.py"
            if not config_file.is_file():
                continue

            if name.startswith("sak_"):
                name = name.replace("sak_", "")

            if self.has_context is None:
                raise Exception("No context defined")

            plugin = SakPlugin(self.has_context, name, plugin_path)
            self.addPlugin(plugin)

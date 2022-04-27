# -*- coding: UTF-8 -*-

import subprocess

from saklib.sak import ctx
from saklib.sakcmd import SakArg, SakCmd
from saklib.sakconfig import SAK_GLOBAL


@SakCmd("show", helpmsg="Show the list of plugins.")
def show() -> str:
    ret = ""
    if ctx.has_plugin_manager is None:
        raise Exception("No plugin manager specifief")
    for plugin in ctx.has_plugin_manager.has_plugins:
        ret += "name: %s\n\tpath: %s\n" % (plugin.name, plugin.plugin_path)
    return ret


@SakCmd("install", helpmsg="Install a new plugin.")
@SakArg("url", required=True, helpmsg="The plugin git repo URL.")
def install(url: str) -> None:
    if ctx.sak_global is not None:
        name = url.split("/")[-1].replace(".git", "").replace("-", "_")
        subprocess.run(
            ["git", "clone", "--recurse-submodules", url, name],
            check=True,
            cwd=(ctx.sak_global / "plugins"),
        )


@SakCmd(helpmsg="Update SAK and all the plugins.")
def update_all(disable_repo_update: bool = False) -> None:

    if SAK_GLOBAL is None:
        raise Exception("Could not define Sak location.")

    if ctx.has_plugin_manager is None:
        raise Exception("No plugin manager specified.")

    print(80 * "-" + "\n")
    print("Update pip")
    subprocess.run(["pip", "install", "--upgrade", "pip"], check=True)

    print(80 * "-" + "\n")
    print("Update sak core")
    path = SAK_GLOBAL

    if not disable_repo_update:
        if (path / ".git").exists():
            print("Updating repository for Sak global")
            subprocess.run(["git", "remote", "update"], check=True, cwd=path)
            subprocess.run(
                ["git", "pull", "origin", "master", "--rebase"], check=True, cwd=path
            )
            subprocess.run(
                ["git", "submodule", "update", "--init", "--recursive"],
                check=True,
                cwd=path,
            )

    if (path / "requirements.txt").exists():
        print("Updating pip dependencies for Sak global")
        subprocess.run(
            ["pip", "install", "--upgrade", "-r", "requirements.txt"],
            check=True,
            cwd=path,
        )

    print(80 * "-" + "\n")
    print("Update plugins")
    for plugin in ctx.has_plugin_manager.getPluginList():
        if plugin.name == "plugins":
            continue

        print(80 * "-" + "\n")
        print("Updating %s\n" % plugin.name)
        plugin.update()


EXPOSE = {"show": show, "install": install, "update_all": update_all}

# -*- coding: UTF-8 -*-


from saklib.sak import ctx
from saklib.sakcmd import SakArg, SakCmd
from saklib.sakconfig import SAK_GLOBAL
from saklib.sakexec import run_cmd


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
        run_cmd(
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
    run_cmd(
        ["pip", "install", "--upgrade", "pip"],
        check=True,
    )

    print(80 * "-" + "\n")
    print("Update sak core")
    path = SAK_GLOBAL

    if not disable_repo_update:
        if (path / ".git").exists():
            print("Updating repository for Sak global")
            run_cmd(
                ["git", "remote", "update"],
                check=True,
                cwd=path,
            )
            run_cmd(
                ["git", "pull", "origin", "master", "--rebase"],
                check=True,
                cwd=path,
            )
            run_cmd(
                ["git", "submodule", "update", "--init", "--recursive"],
                check=True,
                cwd=path,
            )

    if (path / "requirements.txt").exists():
        print("Updating pip dependencies for Sak global")
        run_cmd(
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
        plugin.update(disable_repo_update=disable_repo_update)


EXPOSE = {"show": show, "install": install, "update_all": update_all}

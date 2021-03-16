# Description

This folder should contain dynamically installed plugins

The structure for a plugin is:

    plugin folder
        - requirements.txt
        - sak_config.py
        - __init__.py
        - <plugin_code>.py
        - test/<plugin_code>_test.py

The `sak_config.py` is a description of the plugin and which files contain the plugin implementation.
For example:

```Python
# -*- coding: UTF-8 -*-

"""
Simple demonstration plugin
"""
from typing import List

PLUGIN_NAME = "cowsay"
PLUGIN_VERSION = "0.2.0"

# Specify a list of plugins that we depend and the version
DEPENDS: List[str] = []

EXPOSE_FILES = "cowsay.py"
```

The `<plugin_code>.py` should contain the plugin entry points. Using the `cowsay.py` example:

Note that the EXPOSE variable should contain all the functions to expose on the command line.

```Python
# -*- coding: UTF-8 -*-

"""Cowsay demo."""

from saklib.sakcmd import SakArg, SakCmd


@SakCmd()
@SakArg("message", short_name="m", helpmsg="The message to be printed.")
def dogsay(message: str = "Bye world") -> str:
    """Dog say something."""
    return f"""\
 _____________
< {message} >
 -------------
    \\      _
     \\/\\,_/\\|
      /==_ (
     (Y_.) /       ///
      U ) (__,_____) )
        )'   >     `/
        |._  _____  |
        | | (    \\| (
        | | |    || |
"""


@SakCmd()
@SakArg("message", short_name="m", helpmsg="The message to be printed.")
def cowsay(message: str = "Hello world") -> str:
    """Cow say something."""
    return f"""\
 _____________
< {message} >
 -------------
        \\   ^__^
         \\  (oo)\\_______
            (__)\\       )\\/\\
                ||----w |
                ||     ||
"""


EXPOSE = [dogsay, cowsay]
```

This will generate:

```
usage: sak cowsay [-h]
                  {dogsay,cowsay} ...

Simple demonstration plugin

positional arguments:
  {dogsay,cowsay,has_context,helpmsg,name,plugin_path,update}
    dogsay              Dog say something.
    cowsay              Cow say something.

optional arguments:
  -h, --help            show this help message and exit
```

And calling the command subcommand will generate:

```
$ sak cowsay cowsay
 _____________
< Hello world >
 -------------
        \   ^__^
         \  (oo)\_______
            (__)\       )\/\
                ||----w |
                ||     ||

```

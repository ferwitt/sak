# Description

This folder should contain dynamically installed plugins

The structure for a plugin is:

    plugin folder
        - __init__.py
        - plugin.py

The plugin.py should contain a class that specialized SakPlugin. For example

```Python
# -*- coding: UTF-8 -*-

from sakplugin import SakPlugin
from sakcmd import SakCmd, SakArg

import os

class CowSay(SakPlugin):
    def __init__(self):
        super(CowSay, self).__init__('cowsay')

    def cowsay(self, **vargs):
        os.system('cowsay "Hello world"')

    def exportCmds(self, base):
        show = SakCmd('cowsay', self.cowsay)
        base.addSubCmd(show)
```

This will generate:

```
$ sak -h
usage: sak [-h] {show,plugins,cowsay} ...

positional arguments:
  {show,plugins,cowsay}
    show                TODO
    plugins             TODO
    cowsay              TODO

optional arguments:
  -h, --help            show this help message and exit

```

And callong the command subcommand will generate:

```
$ sak cowsay 
 _____________
< Hello world >
 -------------
        \   ^__^
         \  (oo)\_______
            (__)\       )\/\
                ||----w |
                ||     ||
```

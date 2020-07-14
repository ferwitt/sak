# Description

This folder should contain dynamically installed plugins

The structure for a plugin is:

    plugin folder
        - __init__.py
        - plugin.py

The plugin.py should contain a class that specialized SakPlugin. For example

```Python
# -*- coding: UTF-8 -*-

class SakCowsay(SakPlugin):
    '''Cowsay demo.'''
    @SakCmd()
    @SakArg('message', short_name='m', helpmsg='The message to be printed.')
    def dogsay(self, message='Bye world'):
        '''Dog say something.'''
        return f'''\
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
'''

    @SakCmd()
    @SakArg('message', short_name='m', helpmsg='The message to be printed.')
    def __call__(self, message='Hello world'):
        '''Cow say something.'''
        return f'''\
 _____________
< {message} >
 -------------
        \\   ^__^
         \\  (oo)\\_______
            (__)\\       )\\/\\
                ||----w |
                ||     ||
'''
```

This will generate:

```
usage: sak cowsay [-h] [--message MESSAGE]
                  {dogsay}
                  ...

Cowsay demo.

positional arguments:
  {dogsay,get_ontology,has_context,has_plugin_path,name,onto_declare,onto_impl,plugin_path,update}
    dogsay              Dog say something.

optional arguments:
  -h, --help            show this help message and exit
  --message MESSAGE, -m MESSAGE
                        The message to be printed.
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

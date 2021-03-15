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

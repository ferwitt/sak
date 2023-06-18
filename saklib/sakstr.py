# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

import re


def camel_to_enum(text: str) -> str:
    """Convert camel case to ENUM case.

    :param text: CamelCase text to be converted.
    :returns: The DEFINE_CASE text.
    """
    text = text[0].upper() + text[1:]
    return "_".join(re.findall("[A-Z][a-z0-9_]*", text)).upper()


def camel_to_snake(text: str) -> str:
    return camel_to_enum(text).lower()

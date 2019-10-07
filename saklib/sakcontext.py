# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__version__ = "0.0.0"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

import os


def find_in_parent(dirname, name):
    if os.path.exists(os.path.join(dirname, name)):
        return os.path.join(dirname, name)
    if os.path.dirname(dirname) != '/':
        return find_in_parent(os.path.dirname(dirname), name)
    return None


class SakContext(object):
    def __init__(self):
        super(SakContext, self).__init__()

        script_dir = os.path.abspath(os.path.dirname(__file__))
        current_dir = os.path.abspath('.')

        self.sak_global = find_in_parent(script_dir, '.sak')
        self.sak_local = find_in_parent(current_dir, '.sak')

        self.pluginManager = None

    def setPluginManager(self, pluginManager):
        self.pluginManager = pluginManager

    def getPluginManager(self):
        return self.pluginManager

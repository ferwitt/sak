# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

from sakconfig import SAK_GLOBAL, SAK_LOCAL, CURRENT_DIR

from io import StringIO  ## for Python 3
from contextlib import redirect_stderr
f = StringIO()
with redirect_stderr(f):
    import owlready2 as owl  #type: ignore

import urllib

owl.default_world.set_backend(filename = f"{SAK_GLOBAL}/file.sqlite3", exclusive = False)

owl.onto_path.append(SAK_GLOBAL)
onto = owl.get_ontology("http://sak.org/sak_core.owl#")

try:
    onto.load()
except:
    pass

class Sak(owl.Thing):
    namespace = onto
    """Sak base class"""
    def __init__(self, name, **vargs):
        name = urllib.parse.quote(name, safe='')
        super(Sak, self).__init__(name, **vargs)


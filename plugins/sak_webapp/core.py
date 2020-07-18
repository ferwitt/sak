#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

from sak import root_cmd, plm, ctx
from sakcmd import SakCmd, SakArg, sak_arg_parser, SakCmdWrapper
from sakplugin import load_file
from sakio import register_threaded_stdout_tee, register_threaded_stderr_tee

import os
import sys
import json
import io
import base64
import uuid

from threading import Thread

from pathlib import Path

from typing import Optional

import flask

import bokeh
import bokeh.embed
import bokeh.server.server

import panel as pn


import tornado
import tornado.gen

has_pandas = False
try:
    import pandas as pd
    has_pandas = True
except:
    pass

has_matplotlib = False
try:
    import matplotlib
    import matplotlib.pyplot as plt
    has_matplotlib = True
except:
    pass



from functools import partial

import holoviews as hv
import numpy as np
import panel as pn
import param
#import pyvista as pv

#from holoviews.operation.datashader import rasterize
#from pyvista import examples
from scipy.ndimage import zoom


def set_extensions():
    pass
    # css = '''
    # .custom-wbox > div.bk {
    #     padding-right: 10px;
    # }
    # .scrollable {
    #     overflow: auto !important;
    # }

    # a:link, a:visited {
    #   background-color: #428bca;
    #   color: white;
    #   padding: 4px 5px;
    #   text-align: center;
    #   text-decoration: none;
    #   display: inline-block;
    #   width: 85%;
    # }

    # '''

    # # TODO(witt): Maybe embed those CSSs inside SAK?!
    # js_files = {'jquery': 'https://code.jquery.com/jquery-1.11.1.min.js',
    #             'goldenlayout': 'https://golden-layout.com/files/latest/js/goldenlayout.min.js'}
    # css_files = ['https://golden-layout.com/files/latest/css/goldenlayout-base.css',
    #              'https://golden-layout.com/files/latest/css/goldenlayout-light-theme.css']

    # pn.extension(
    #         #'vtk',
    #         js_files=js_files, raw_css=[css], css_files=css_files)

    # #hv.renderer('bokeh').theme = 'dark_minimal'
    # hv.opts.defaults(hv.opts.Image(responsive=True, tools=['hover']))


def modify_doc(doc):
    webapp_file = Path(__file__).resolve().parent / 'webapp.py'
    webapp = load_file(webapp_file)

    # Get the doc object
    newdoc = webapp['SakDoc'](doc)

    newdoc.server_doc()

    return
    newdoc_layout = newdoc.view()

    doc.add_root(newdoc_layout.get_root(doc))

    return



    args = doc.session_context.request.arguments

    path = ''
    try:
        path = args['path'][0].decode("utf-8")
    except:
        pass

    # TODO(witt): Make some way to cache this and not reload the module all the time!
    try:
        webapp_file = Path(__file__).resolve().parent / 'webapp.py'
        webapp = load_file(webapp_file)

        # Get the doc object
        newdoc = webapp['get_callback_object'](doc, path)
        newdoc_layout = newdoc.layout

        doc.add_root(newdoc_layout.get_root(doc))
    except:
        #TODO(witt): I could update the doc with some nice error message :)
        pass


def bk_worker(bokeh_port):
    pn.extension()
    server = bokeh.server.server.Server({'/': modify_doc},
            io_loop=tornado.ioloop.IOLoop(),
            allow_websocket_origin=[f'127.0.0.1:{bokeh_port}'],
            port=bokeh_port)
    server.start()
    server.io_loop.start()


@SakCmd('start', helpmsg='Start webapp')
@SakArg('port', short_name='p', helpmsg='The Bokeh server port (default: 5006)')
def start(port:int=2020):
    set_extensions()

    register_threaded_stdout_tee()
    register_threaded_stderr_tee()

    print(f'Running on http://127.0.0.1:{port}/')
    bk_worker(port)

def jupyter():
    sys.path.append(ctx.sak_global / 'saklib')
    os.environ['PATH'] = str(ctx.sak_global / 'saklib') + ':' + os.environ['PATH']
    os.system('jupyter lab')


EXPOSE = {'start': start, 'jupyter': jupyter}

# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__version__ = "0.0.0"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

import os
import sys
import platform
import subprocess


CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))
SAK_GLOBAL = os.path.abspath(os.path.join(os.environ.get('HOME'), '.sak'))

# SAK will not use the system python, but will download miniconda
SAK_PYTHON = os.path.join(SAK_GLOBAL, 'python')
SAK_PYTHON_BIN = os.path.join(SAK_PYTHON, 'miniconda3', 'bin', 'python3')

def check_python():
    return os.path.exists(SAK_PYTHON_BIN)

def pip_install():
    pass

def install_python(ask_confirm=True):
    if check_python():
        return

    if ask_confirm:
        if not input("No python found, would like to install? [Y/N]") in ['Y', 'y', 'yes']:
            return

    if not os.path.exists(SAK_PYTHON):
        os.makedirs(SAK_PYTHON)

    miniconda_installer = os.path.join(SAK_PYTHON, 'miniconda.sh')
    if not os.path.exists(miniconda_installer):
        subprocess.check_call([
            'wget',
            'https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh',
            '-O',
            miniconda_installer])

    instalation_prefix = os.path.join(SAK_PYTHON, 'miniconda3')
    subprocess.check_call(['/usr/bin/env', 'bash', miniconda_installer, '-b', '-p', instalation_prefix])


def install():
    install_python(ask_confirm=False)

def run():
    # TODO: This must be the leader pid, so if it dies it will kill all the subprocesses
    #os.killpg(os.getpgid(pro.pid), signal.SIGTERM) 

    if 'x86' in platform.machine():
        install()

        os.environ['PATH'] = os.path.dirname(SAK_PYTHON_BIN) + ':' + os.environ['PATH']

        ## TODO: Tryied to use subprocess, but argcomplete didnt work
        cmd = [SAK_PYTHON_BIN, os.path.join(SAK_GLOBAL,'saklib', 'sak.py') ] + sys.argv[1:]
        sys.exit(os.system(' '.join(['"%s"' % x for x in cmd])))
    else:
        sys.path.append(os.path.join(SAK_GLOBAL,'saklib'))
        import sak
        sak.main()


    #sys.exit(subprocess.call([SAK_PYTHON_BIN,
    #    os.path.join(SAK_GLOBAL,'saklib', 'sak.py')
    #    ] + sys.argv[1:]))

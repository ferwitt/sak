# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__version__ = "0.0.0"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

from sakcmd import SakCmd, SakArg

def show_version(**vargs):
    print('Version: %s' % (__version__))

def sak_cb(**vargs):
    print('Nothing to do')

def s_cb(**vargs):
    print(vargs)

def main():
    root = SakCmd('sak', sak_cb)
    
    version_cmd = SakCmd('version', show_version)
    root.addSubCmd(version_cmd)

    parser = root.generateArgParse()
    args = vars(parser.parse_args())
    callback = args.pop('sak_callback')
    callback(**args)



if __name__ == "__main__":
    main()

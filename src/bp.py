#!/usr/bin/env python


### BITPIM
###
### Copyright (C) 2003 Roger Binns <rogerb@rogerbinns.com>
###
### This software is under the Artistic license.
### Please see the accompanying LICENSE file
###
### $Id$

"""Main entry point to Bitpim

It invokes BitPim in gui or commandline mode as appropriate

@Note: Only gui mode is supported at the moment
"""

# only gui mode support at the moment

if __name__ == '__main__':
    import sys  
    import gui

    gui.run(sys.argv)

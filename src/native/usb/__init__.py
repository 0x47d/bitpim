### BITPIM
###
### Copyright (C) 2003-2004 Roger Binns <rogerb@rogerbinns.com>
### Copyright (C) 2010 Nathan Hjelm <hjelmn@uses.sourceforge.net>
###
### This software is under the same license as libusb
###
### $Id: styles.xy,v 1.4 2003/12/07 06:23:44 rogerb Exp$

# Drop libusb support for Windows
import sys

if sys.platform=='win32':
    raise ImportError("libusb not supported on win32")

# Keep python happy that this is a module
# bring everything into ournamespace
from usb import *

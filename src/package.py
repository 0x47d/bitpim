#!/usr/bin/env python
### BITPIM
###
### Copyright (C) 2003-2006 Roger Binns <rogerb@rogerbinns.com>
### Copyright (C) 2003-2004 Steven Palm <n9yty@n9yty.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

# This file provides the packaging definitions used by the buildrelease system

import sys

import version

def sanitycheck():
    "Check everything is ok"
    print "=== Sanity check ==="

    print "python version",
    if sys.version_info[:2]!=(2,3):
       raise Exception("Should be  Python 2.3 - this is "+sys.version)
    print "  OK"

    print "wxPython version",
    import wx
    if wx.VERSION[:4]!=(2,6,2,1):
        raise Exception("Should be wxPython 2.6.2.1.  This is "+`wx.VERSION`)
    print "  OK"

    print "wxPython is unicode build",
    if not wx.USE_UNICODE:
        raise Exception("You need a unicode build of wxPython")
    print "  OK"

    if sys.platform!='win32':
        print "native.usb",
        import native.usb
        print "  OK"

    print "pycrypto version",
    expect='2.0.1'
    import Crypto
    if Crypto.__version__!=expect:
        raise Exception("Should be %s version of pycrypto - you have %s" % (expect, Crypto.__version__))
    print "  OK"

    print "paramiko version",
    expect='1.4 (oddish)'
    import paramiko
    if paramiko.__version__!=expect:
        raise Exception("Should be %s version of paramiko - you have %s" % (expect, paramiko.__version__))
    print "  OK"
    
    print "bitfling",
    import bitfling
    print "  OK"

    print "pyserial",
    import serial
    print "  OK"

    print "apsw",
    import apsw
    ver="3.2.7-r1"
    if apsw.apswversion()!=ver:
        raise Exception("Should be apsw version %s - you have %s" % (ver, apsw.apswversion()))
    print "  OK"

    print "sqlite",
    ver="3.2.7"
    if apsw.sqlitelibversion()!=ver:
        raise Exception("Should be sqlite version %s - you have %s" % (ver, apsw.sqlitelibversion()))
    print "  OK"

        
    print "jaro/winkler string matcher",
    import native.strings.jarow
    print "  OK"

    # bsddb (Linux only, for evolution)
    if sys.platform=="linux2":
        print "bsddb ",
        import bsddb
        print "  OK"

    # libusb on Windows
        # check libusb
    import win32api
    try:
        win32api.FreeLibrary(win32api.LoadLibrary("libusb0.dll"))
    except:
        raise Exception("You need libusb0.dll to be available to do a build.  You only need the dll, not the rest of libusb-win32.  (It doesn't have to be available on the end user system, but does need to be present to do a correct build")


    print "=== All checks out ==="

def resources():
    """Get a list of the resources (images, executables, sounds etc) we ship

    @rtype: dict
    @return: The key for each entry in the dict is a directory name, and the value
             is a list of files within that directory"""
    tbl={}
    # list of files
    exts=[ '*.xy', '*.png', '*.ttf', '*.wav', '*.jpg', '*.css', '*.pdc', '*.ids']
    if sys.platform=='win32':
        # on windows we also want the chm help file and the manifest needed to get Xp style widgets
        exts=exts+['*.chm', '*.manifest', '*.ico']
        exts=exts+['helpers/*.exe','helpers/*.dll']
    if sys.platform=='linux2':
        exts=exts+['helpers/*.lbin', '*.htb']
    if sys.platform=='darwin':
        exts=exts+['helpers/*.mbin', '*.htb']
    # list of directories to look in
    dirs=[ os.path.join('.', 'resources'), '.' ]
    # don't ship list
    dontship.append("pvconv.exe")  # Qualcomm won't answer if I can ship this
    for wildcard in exts:
        for dir in dirs:
            for file in glob.glob(os.path.join(dir, wildcard)):
                if os.path.basename(file).lower() in dontship: continue 
                d=os.path.dirname(file)
                if not tbl.has_key(d):
                    tbl[d]=[]
                tbl[d].append(file)

    files=[]
    for i in tbl.keys():
        files.append( (i, tbl[i]) )

    return files

def isofficialbuild():
    "Work out if this is an official build"
    import socket
    h=socket.gethostname().lower()
    # not built by rogerb (or stevep/n9yty) are unofficial
    return h in ('rh9bitpim.rogerbinns.com', "roger-sqyvr14d3",
             "smpbook.n9yty.com", "smpbook.local.", "rogerbmac.rogerbinns.com", "rogerbmac.local")

def ensureofficial():
    """If this is not an official build then ensure that version.vendor doesn't say it is"""
    if not isofficialbuild():
        if version.vendor=="official":
            # it isn't official, so modify file
            f=open("version.py", "rt").read()
            newf=f.replace('vendor="official"', 'vendor="unofficial"')
            assert newf!=f
            open("version.py", "wt").write(newf)
            reload(version)

def getversion():
    return version.version

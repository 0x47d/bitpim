### BITPIM
###
### Copyright (C) 2003-2004 Stephen Wood <sawecw@users.sf.net>
### Copyright (C) 2003-2004 Roger Binns <rogerb@rogerbinns.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"Routines to do various file format conversions"

import os
import tempfile
import sys

import common


def convertto8bitpng(pngdata, maxsize):
    "Convert a PNG file to 8bit color map"
    size=len(pngdata)
    if size<=maxsize:
        return pngdata

    p=sys.path[0]
    if os.path.isfile(p):
        p=os.path.dirname(p)
    helpersdirectory=os.path.abspath(os.path.join(p, 'helpers'))
    print "Helper Directory: "+helpersdirectory
    if sys.platform=='win32':
        osext=".exe"
    if sys.platform=='darwin':
        osext=".mbin"
    if sys.platform=='linux2':
        osext=".lbin"
        
    pngtopnmbin=os.path.join(helpersdirectory,'pngtopnm')+osext
    ppmquantbin=os.path.join(helpersdirectory,'ppmquant')+osext
    pnmtopngbin=os.path.join(helpersdirectory,'pnmtopng')+osext
    print "pngtopnm: "+pngtopnmbin
    print "ppmquant: "+ppmquantbin
    print "pnmtopng: "+pnmtopngbin

    # Binary search to find largest # of colors with a file size still
    # less than maxsize

    ncolormax=257
    ncolormin=1
    ncolortry=256
    ncolor=ncolortry

    while size>maxsize or ncolormax-ncolor>1:
        ncolor=ncolortry
        pnm=common.gettempfilename("pnm")
        f=os.popen(pngtopnmbin + '>'+pnm,'w')
        f.write(pngdata)
        f.close()
        f = os.popen(ppmquantbin+' '+`ncolortry`+' '+pnm+ '|'+pnmtopngbin,'r')

        pngquantdata=f.read()
        f.close
        os.remove(pnm)
        size=len(pngquantdata)
        print `ncolor`+' '+`size`
        if size>maxsize:
            ncolormax=ncolor
            ncolortry=(ncolor+ncolormin)/2
        else:
            ncolormin=ncolor
            ncolortry=(ncolor+ncolormax)/2
            
    return pngquantdata
        

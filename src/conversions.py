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
import wx

import common

def convertto8bitpng(pngdata, maxsize):
    "Convert a PNG file to 8bit color map"

    # Return files small enough, or not PNG as is
    size=len(pngdata)
    if size<=maxsize or pngdata[1:4]!='PNG':
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

    # Write original image to a temp file
    png=common.gettempfilename("png")
    open(png, "wb").write(pngdata)

    # Convert this image to pnm
    pnm=common.gettempfilename("pnm")
    s='"'+pngtopnmbin+'"' + ' < '+png+' > '+pnm
    os.system(s)
    #self.log(s)
    os.remove(png)

    # Binary search to find largest # of colors with a file size still
    # less than maxsize

    ncolormax=257
    ncolormin=1
    ncolortry=256
    ncolor=ncolortry
    pnmq=common.gettempfilename("pnm")

    while size>maxsize or ncolormax-ncolor>1:
        ncolor=ncolortry
        s='"'+ppmquantbin+'"'+' '+`ncolortry`+' '+pnm+ ' > '+pnmq
        #self.log(s)
        os.system(s)
        s ='"'+pnmtopngbin+'"' + ' < ' + pnmq + ' > '+png
        #self.log(s)
        os.system(s)
        os.remove(pnmq)
        pngquantdata=open(png,"rb").read()
        os.remove(png)
        size=len(pngquantdata)
        print `ncolor`+' '+`size`
        if size>maxsize:
            ncolormax=ncolor
            ncolortry=(ncolor+ncolormin)/2
        else:
            ncolormin=ncolor
            ncolortry=(ncolor+ncolormax)/2

    os.remove(pnm)
    return pngquantdata

def convertto8bitpng(pngdata):
    "Convert a PNG file to 8bit color map"
    "Separate routine for now so not to screw up existing one, may merge later"
    if pngdata[1:4]!='PNG':
        return pngdata
    # get the path to helper
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
    # Write original image to a temp file
    png=common.gettempfilename("png")
    open(png, "wb").write(pngdata)
    num_of_colors=wx.Image(png).ComputeHistogram(wx.ImageHistogram())
    print 'number of colors:', num_of_colors
    if num_of_colors>256:
        # no optimization possible, just return
        os.remove(png)
        return pngdata
    # else optimize it
    # Convert this image to pnm
    pnm=common.gettempfilename("pnm")
    s='"'+pngtopnmbin+'"' + ' < '+png+' > '+pnm
    os.system(s)
    os.remove(png)
    # quantize & convert
    pnmq=common.gettempfilename("pnm")
    s='"'+ppmquantbin+'"'+' '+`num_of_colors`+' '+pnm+ ' > '+pnmq
    os.system(s)
    s ='"'+pnmtopngbin+'"' + ' < ' + pnmq + ' > '+png
    os.system(s)
    os.remove(pnmq)
    pngquantdata=open(png, 'rb').read()
    os.remove(png)
    os.remove(pnm)
    print 'old size: ',len(pngdata),', new size: ',len(pngquantdata)
    return pngquantdata

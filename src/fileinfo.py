### BITPIM
###
### Copyright (C) 2005 Roger Binns <rogerb@rogerbinns.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"Returns information about files"

import os

class FailedFile:
    def GetBytes(*args):   return None
    def GetLSBUint32(*args): return None
    def GetLSBUint16(*args): return None
    def GetByte(*args): return None
    def GetMSBUint32(*args): return None
    def GetMSBUint16(*args): return None

class SafeFileWrapper:
    """Wraps a file object letting you get various parts without exceptions"""

    def __init__(self, filename):
        try:
            self.file=open(filename, "rb")
            self.size=os.stat(filename).st_size
            self.data=self.file.read(1024)
            self.offset=len(self.data)
        except (OSError,IOError):
            # change our class
            self.size=-1
            self.__class__=FailedFile

    def EnsureRange(self, offset, length):
        if offset+length<=len(self.data):
            return True
        if offset+length>self.size:
            return False
        more=self.file.read(offset+length-self.offset)
        self.offset+=len(more)
        self.data+=more
        return offset+length<=len(self.data)

    def GetBytes(self, offset, length):
        if not self.EnsureRange(offset, length):
            return None
        return self.data[offset:offset+length]

    def GetLSBUint32(self, offset):
        v=self.GetBytes(offset, 4)
        if v is None: return v
        return ord(v[0])+(ord(v[1])<<8)+(ord(v[2])<<16)+(ord(v[3])<<24)

    def GetLSBUint16(self, offset):
        v=self.GetBytes(offset, 2)
        if v is None: return v
        return ord(v[0])+(ord(v[1])<<8)

    def GetMSBUint32(self, offset):
        v=self.GetBytes(offset, 4)
        if v is None: return v
        return ord(v[3])+(ord(v[2])<<8)+(ord(v[1])<<16)+(ord(v[0])<<24)

    def GetMSBUint16(self, offset):
        v=self.GetBytes(offset, 2)
        if v is None: return v
        return ord(v[1])+(ord(v[0])<<8)

    def GetByte(self, offset):
        v=self.GetBytes(offset,1)
        if v is None: return v
        return ord(v)

class ImgFileInfo:
    "Wraps information about a file"

    # These will always be present
    attrnames=("width", "height", "format", "bpp", "size")

    def __init__(self, f, **kwds):
        for a in self.attrnames:
            setattr(self, a, None)
        self.size=f.size
        self.__dict__.update(kwds)

    def shortdescription(self):
        v=getattr(self, "_shortdescription", None)
        if v is not None:
            return v(self)        
        res=[]
        if self.width is not None and self.height is not None:
            res.append( "%d x %d" % (self.width, self.height) )
        if self.format is not None:
            res.append( self.format)
        if self.bpp is not None:
            res.append( "%d bpp" % (self.bpp,))

        if len(res):
            return " ".join(res)
        return "Unknown format"

    def longdescription(self):
        v=getattr(self, "_longdescription", None)
        if v is not None:
            return v(self)
        return self.shortdescription()

def idimg_BMP(f):
    "Identify a Windows bitmap"
    # 40 is header size for windows bmp, different numbers are used by OS/2
    if f.GetBytes(0,2)=="BM" and f.GetLSBUint16(14)==40:
        d={'format': "BMP"}
        d['width']=f.GetLSBUint32(18)
        d['height']=f.GetLSBUint32(22)
        d['bpp']=f.GetLSBUint16(28)
        d['compression']=f.GetLSBUint32(30)
        d['ncolours']=f.GetLSBUint32(46)
        d['nimportantcolours']=f.GetLSBUint32(50)
        d['_longdescription']=fmt_BMP
        for i in d.itervalues():
            if i is None:  return None
        ifi=ImgFileInfo(f,**d)
        return ifi
    return None

def fmt_BMP(ifi):
    "Long description for BMP"
    res=[ifi.shortdescription()]
    if ifi.compression==0:
        res.append("No compression")
    elif ifi.compression==1:
        res.append("8 bit run length encoding")
    elif ifi.compression==2:
        res.append("4 bit run length encoding")
    elif ifi.compression==3:
        res.append("RGB bitmap with mask")
    else:
        res.append("Unknown compression "+`ifi.compression`)
    if ifi.ncolours:
        res.append("%d colours" % (ifi.ncolours,))
        if ifi.nimportantcolours:
            res[-1]=res[-1]+(" (%d important)" % (ifi.nimportantcolours,))
    return "\n".join(res)
    
def idimg_PNG(f):
    "Identify a PNG"
    if f.GetBytes(0,8)=="\x89PNG\r\n\x1a\n" and f.GetBytes(12,4)=="IHDR":
        d={'format': "PNG"}
        d['width']=f.GetMSBUint32(16)
        d['height']=f.GetMSBUint32(20)
        d['bitdepth']=f.GetByte(24)
        d['colourtype']=f.GetByte(25)
        d['compression']=f.GetByte(26)
        d['filter']=f.GetByte(27)
        d['interlace']=f.GetByte(28)
        d['_shortdescription']=fmts_PNG
        d['_longdescription']=fmt_PNG
        for i in d.itervalues():
            if i is None:  return None
        ifi=ImgFileInfo(f,**d)
        return ifi
    return None

def fmts_PNG(ifi, short=True):
    res=[]
    res.append( "%d x %d" % (ifi.width, ifi.height) )
    res.append( ifi.format)
    if ifi.colourtype in (0,4):
        res.append("%d bit grayscale" % (ifi.bitdepth,))
    elif ifi.colourtype in (2,6):
        res.append("truecolour (%d bit)" % (ifi.bitdepth*3,))
    elif ifi.colourtype==3:
        res.append("%d colours" % (2**ifi.bitdepth,))
    if not short and ifi.colourtype in (4,6):
            res.append("with transparency")
    return " ".join(res)

def fmt_PNG(ifi):
    "Long description for PNG"
    res=[fmts_PNG(ifi, False)]

    if ifi.compression==0:
        res.append("Deflate compressed")
    else:
        res.append("Unknown compression "+`ifi.compression`)

    if ifi.filter==0:
        res.append("Adaptive filtering")
    else:
        res.append("Unknown filtering "+`ifi.filter`)

    if ifi.interlace==0:
        res.append("No interlacing")
    elif ifi.interlace==1:
        res.append("Adam7 interlacing")
    else:
        res.append("Unknown interlacing "+`ifi.interlace`)
    return "\n".join(res)
                   
def idimg_BCI(f):
    "Identify a Brew Compressed Image"
    if f.GetBytes(0,4)=="BCI\x00":
        d={'format': "BCI"}
        d['width']=f.GetLSBUint16(0x0e)
        d['height']=f.GetLSBUint16(0x10)
        d['bpp']=8
        d['ncolours']=f.GetLSBUint16(0x1a)
        d['_longdescription']=fmt_BCI
        for i in d.itervalues():
            if i is None:  return None
        ifi=ImgFileInfo(f,**d)
        return ifi
    return None

def fmt_BCI(ifi):
    "Long description for BCI"
    res=[ifi.shortdescription()]
    res.append("%d colour palette" % (ifi.ncolours,))
    return "\n".join(res)

def idimg_JPG(f):
    "Identify a JPEG image"
    # The people who did jpeg decided to see just how complicated an image
    # format they could make.
    if f.GetBytes(0,2)=="\xff\xd8":
        # in theory we could also parse EXIF information
        offset=2
        while True:
            # we just skip the segments until we find SOF0 (0xc0)
            # I can't figure out from the docs if we should also care about SOF1/SOF2 etc
            if f.GetByte(offset)!=0xff:
                return None
            id=f.GetByte(offset+1)
            offset+=2
            seglen=f.GetMSBUint16(offset)
            if seglen is None or id is None: return None
            if id!=0xc0:
                offset+=seglen
                continue
            offset+=2
            d={'format': 'JPEG'}
            d['bpp']=3*f.GetByte(offset)
            d['height']=f.GetMSBUint16(offset+1)
            d['width']=f.GetMSBUint16(offset+3)
            d['components']=f.GetByte(offset+5)
            d['_shortdescription']=fmts_JPG
            for i in d.itervalues():
                if i is None:  return None
            ifi=ImgFileInfo(f,**d)
            return ifi            
    return None

def fmts_JPG(ifi):
    res=[]
    res.append( "%d x %d" % (ifi.width, ifi.height) )
    res.append( ifi.format)
    if ifi.components==1:
        res.append("(greyscale)")
    elif ifi.components==3:
        res.append("(RGB)") # technically it is YcbCr ...
    elif ifi.components==4:
        res.append("(CMYK)")
    else:
        res.append("Unknown components "+`ifi.components`)
    return " ".join(res)

imageids=[globals()[f] for f in dir() if f.startswith("idimg_")]
def identify_imagefile(filename):
    fo=SafeFileWrapper(filename)
    for f in imageids:
        obj=f(fo)
        if obj is not None:
            return obj
    return ImgFileInfo(fo)

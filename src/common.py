### BITPIM
###
### Copyright (C) 2003-2004 Roger Binns <rogerb@rogerbinns.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$


# Documentation
"""Various classes and functions that are used by GUI and command line versions of BitPim"""

# standard modules
import string
import cStringIO
import StringIO
import sys
import traceback
import tempfile

class FeatureNotAvailable(Exception):
     """The device doesn't support the feature"""
     def __init__(self, device, message="The device doesn't support the feature"):
          Exception.__init__(self, "%s: %s" % (device, message))
          self.device=device
          self.message=message

class IntegrityCheckFailed(Exception):
     def __init__(self, device, message):
          Exception.__init__(self, "%s: %s" % (device, message))
          self.device=device
          self.message=message
                  

# generic comms exception and then various specialisations
class CommsException(Exception):
     """Generic commmunications exception"""
     def __init__(self, message, device="<>"):
        Exception.__init__(self, "%s: %s" % (device, message))
        self.device=device
        self.message=message

class CommsNeedConfiguring(CommsException):
     """The communication settings need to be configured"""
     pass

class CommsDeviceNeedsAttention(CommsException):
     """The communication port or device attached to it needs some
     manual intervention"""
     pass

class CommsDataCorruption(CommsException):
     """There was some form of data corruption"""
     pass

class CommsTimeout(CommsException):
    """Timeout while reading or writing the commport"""
    pass

class CommsOpenFailure(CommsException):
    """Failed to open the communications port/device"""
    pass

class CommsWrongPort(CommsException):
     """The wrong port has been selected, typically the modem port on an LG composite device"""
     pass

class AutoPortsFailure(CommsException):
     """Failed to auto detect a useful port"""
     def __init__(self, portstried):
          self.device="auto"
          self.message="Failed to auto-detect the port to use.  "
          if portstried is not None and len(portstried):
               self.message+="I tried "+", ".join(portstried)
          else:
               self.message+="I couldn't detect any candidate ports"
          CommsException.__init__(self, self.message, self.device)

def datatohexstring(data):
    """Returns a pretty printed hexdump of the data

    @rtype: string"""
    res=cStringIO.StringIO()
    lchar=""
    lhex="00000000 "
    for count in range(0, len(data)):
        b=ord(data[count])
        lhex=lhex+"%02x " % (b,)
        if b>=32 and string.printable.find(chr(b))>=0:
            lchar=lchar+chr(b)
        else:
            lchar=lchar+'.'

        if (count+1)%16==0:
            res.write(lhex+"    "+lchar+"\n")
            lhex="%08x " % (count+1,)
            lchar=""
    if len(data):
        while (count+1)%16!=0:
            count=count+1
            lhex=lhex+"   "
        res.write(lhex+"    "+lchar+"\n")
    return res.getvalue()

def hexify(data):
     "Turns binary data into a hex string (like the output of MD5/SHA hexdigest)"
     return "".join(["%02x" % (ord(x),) for x in data])

def prettyprintdict(dictionary, indent=0):
     """Returns a pretty printed version of the dictionary

     The elements are sorted into alphabetical order, and printed
     one per line.  Dictionaries within the values are also pretty
     printed suitably indented.

     @rtype: string"""

     res=cStringIO.StringIO()

     # the indent string
     istr="  "

     # opening brace
     res.write("%s{\n" % (istr*indent,))
     indent+=1

     # sort the keys
     keys=dictionary.keys()
     keys.sort()

     # print each key
     for k in keys:
          v=dictionary[k]
          # is it a dict
          if isinstance(v, dict):
               res.write("%s%s:\n%s\n" % (istr*indent, `k`, prettyprintdict(v, indent+1)))
          else:
               # is it a list of dicts?
               if isinstance(v, list):
                    dicts=0
                    for item in v:
                         if isinstance(item, dict):
                              dicts+=1
                    if dicts and dicts==len(v):
                         res.write("%s%s:\n%s[\n" % (istr*indent,`k`,istr*(indent+1)))
                         for item in v:
                              res.write(prettyprintdict(item, indent+2))
                         res.write("%s],\n" % (istr*(indent+1)))
                         continue
               res.write("%s%s: %s,\n" % (istr*indent, `k`, `v`))

     # closing brace
     indent-=1
     if indent>0:
          comma=","
     else:
          comma=""
     res.write("%s}%s\n" % (istr*indent,comma))

     return res.getvalue()

     
class exceptionwrap:
     """A debugging assist class that helps in tracking down functions returning exceptions"""
     def __init__(self, callable):
          self.callable=callable
          
     def __call__(self, *args, **kwargs):
          try:

               return self.callable(*args, **kwargs)
          except:
               print "in exception wrapped call", `self.callable`
               print formatexception()
               raise

def readversionedindexfile(filename, dict, versionhandlerfunc, currentversion):
     assert currentversion>0
     execfile(filename, dict, dict)
     if not dict.has_key('FILEVERSION'):
          version=0
     else:
          version=dict['FILEVERSION']
          del dict['FILEVERSION']
     if version<currentversion:
          versionhandlerfunc(dict, version)

def writeversionindexfile(filename, dict, currentversion):
     assert currentversion>0
     f=open(filename, "w")
     for key in dict:
          v=dict[key]
          if isinstance(v, type({})):
               f.write("result['%s']=%s\n" % (key, prettyprintdict(dict[key])))
          else:
               f.write("result['%s']=%s\n" % (key, `v`))
     f.write("FILEVERSION=%d\n" % (currentversion,))
     f.close()

def formatexception(excinfo=None, lastframes=8):
     """Pretty print exception, including local variable information.

     See Python Cookbook, recipe 14.4.

     @param excinfo: tuple of information returned from sys.exc_info when
               the exception occurred.  If you don't supply this then
               information about the current exception being handled
               is used
     @param lastframes: local variables are shown for these number of
                  frames
     @return: A pretty printed string
               """
     if excinfo is None:
          excinfo=sys.exc_info()

     s=StringIO.StringIO()
     traceback.print_exception(*excinfo, **{'file': s})
     tb=excinfo[2]

     while True:
          if not tb.tb_next:
               break
          tb=tb.tb_next
     stack=[]
     f=tb.tb_frame
     while f:
          stack.append(f)
          f=f.f_back
     stack.reverse()
     if len(stack)>lastframes:
          stack=stack[-lastframes:]
     print >>s, "\nVariables by last %d frames, innermost last" % (lastframes,)
     for frame in stack:
          print >>s, ""
          print >>s, "Frame %s in %s at line %s" % (frame.f_code.co_name,
                                                    frame.f_code.co_filename,
                                                    frame.f_lineno)
          for key,value in frame.f_locals.items():
               # filter out modules
               if type(value)==type(sys):
                    continue
               print >>s,"%15s = " % (key,),
               try:
                    print >>s,`value`[:80]
               except:
                    print >>s,"(Exception occurred printing value)"
     return s.getvalue()
                    
def gettempfilename(extension):
    "Returns a filename to be used for a temporary file"
    try:
        # safest Python 2.3 method
        x=tempfile.NamedTemporaryFile(suffix="."+extension)
        n=x.name
        x.close()
        del x
        return n
    except:
        # Predictable python 2.2 method
        return tempfile.mktemp("."+extension)

def getfullname(name):
     """Returns the object corresponding to name.
     Imports will be done as necessary to resolve
     every part of the name"""
     mods=name.split('.')
     dict={}
     for i in range(len(mods)):
          # import everything
          try:
               exec "import %s" % (".".join(mods[:i])) in dict, dict
          except:
               pass
     # ok, we should have the name now
     return eval(name, dict, dict)

def list_union(*lists):
     res=[]
     for l in lists:
          for item in l:
               if item not in res:
                    res.append(item)
     return res

# unicode byte order markers to codecs
# this really should be part of the standard library

# we try to import the encoding first.  that has the side
# effect of ensuring that the freeze tools pick up the
# right bits of code as well
import codecs

_boms=[]
# 64 bit 
try:
     import encodings.utf_64
     _boms.append( (codecs.BOM64_BE, "utf_64") )
     _boms.append( (codecs.BOM64_LE, "utf_64") )
except:  pass

# 32 bit
try:
     import encodings.utf_32
     _boms.append( (codecs.BOM_UTF32, "utf_32") )
     _boms.append( (codecs.BOM_UTF32_BE, "utf_32") )
     _boms.append( (codecs.BOM_UTF32_LE, "utf_32") )
except:  pass

# 16 bit
try:
     import encodings.utf_16
     _boms.append( (codecs.BOM_UTF16, "utf_16") )
     _boms.append( (codecs.BOM_UTF16_BE, "utf_16") )
     _boms.append( (codecs.BOM_UTF16_LE, "utf_16") )
except:  pass

# 8 bit
try:
     import encodings.utf_8
     _boms.append( (codecs.BOM_UTF8, "utf_8") )
except: pass

# NB: the 32 bit and 64 bit versions have the BOM constants defined in Py 2.3
# but no corresponding encodings module.  They are here for completeness.
# The order of above also matters since the first ones have longer
# boms than the latter ones, and we need to be unambiguous

_maxbomlen=max([len(bom) for bom,codec in _boms])

def opentextfile(name):
     """This function detects unicode byte order markers and if present
     uses the codecs module instead to open the file instead with
     appropriate unicode decoding, else returns the file using standard
     open function"""
     f=open(name, "rb")
     start=f.read(_maxbomlen)
     for bom,codec in _boms:
          if start.startswith(bom):
               f.close()
               # some codecs don't do readline, so we have to vector via stringio
               # many postings also claim that the BOM is returned as the first
               # character but that hasn't been the case in my testing
               return StringIO.StringIO(codecs.open(name, "r", codec).read())
     f.close()
     return open(name, "rtU")


# don't you just love i18n

# the following function is actually defined in guihelper and
# inserted into this module.  the intention is to ensure this
# module doesn't have to import wx.  The guihelper version
# checks if wx is in unicode mode

#def strorunicode(s):
#     if isinstance(s, unicode): return s
#     return str(s)

def forceascii(s):
     try:
          return str(s)
     except UnicodeEncodeError:
          return s.encode("ascii", 'replace')

### BITPIM
###
### Copyright (C) 2003 Roger Binns <rogerb@rogerbinns.com>
###
### This software is under the Artistic license.
### http://www.opensource.org/licenses/artistic-license.php
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

# generic comms exception and then various specialisations
class CommsException(Exception):
     """Generic commmunications exception"""
     def __init__(self, device, message):
        Exception.__init__(self, "%s: %s" % (device, message))
        self.device=device
        self.message=message

class CommsNeedConfiguring(CommsException):
     """The communication settings need to be configured"""
     def __init__(self, device, message):
        CommsException.__init__(self, device, message)
        self.device=device
        self.message=message

class CommsDeviceNeedsAttention(CommsException):
    """The communication port or device attached to it needs some
    manual intervention"""
    def __init__(self, device, message):
        CommsException.__init__(self, device, message)
        self.device=device
        self.message=message

class CommsTimeout(CommsException):
    """Timeout while reading or writing the commport"""
    def __init__(self, device, message):
        CommsException.__init__(self, device, message)
        self.device=device
        self.message=message

class CommsOpenFailure(CommsException):
    """Failed to open the communications port/device"""
    def __init__(self, device, message):
        CommsException.__init__(self, device, message)
        self.device=device
        self.message=message

class AutoPortsFailure(CommsException):
     """Failed to auto detect a useful port"""
     def __init__(self, portstried):
          self.device="auto"
          self.message="Failed to auto-detect the port to use.  "
          if portstried is not None and len(portstried):
               self.message+="I tried "+", ".join(portstried)
          else:
               self.message+="I couldn't detect any candidate ports"
          CommsException.__init__(self, self.device, self.message)

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

def prettyprintdict(dictionary, indent=0):
     """Returns a pretty printed version of the dictionary

     The elements are sorted into alphabetical order, and printed
     one per line.  Dictionaries within the values are also pretty
     printed suitably indented.

     @rtype: string"""

     res=""
     
     # the indent string
     istr="  "

     # opening brace
     res+="%s{\n" % (istr*indent,)
     indent+=1

     # sort the keys
     keys=dictionary.keys()
     keys.sort()

     # print each key
     for k in keys:
          v=dictionary[k]
          if isinstance(v, dict):
               res+="%s%s:\n%s\n" % (istr*indent, `k`, prettyprintdict(v, indent+1))
          else:
               res+="%s%s: %s,\n" % (istr*indent, `k`, `v`)

     # closing brace
     indent-=1
     if indent>0:
          comma=","
     else:
          comma=""
     res+="%s}%s\n" % (istr*indent,comma)

     return res

     
class exceptionwrap:
     """A debugging assist class that helps in tracking down functions returning exceptions"""
     def __init__(self, callable):
          self.callable=callable
          
     def __call__(self, *args, **kwargs):
          try:
               print "in exception wrapped call"
               res=self.callable(*args, **kwargs)
               print `self.callable`, "returned", datatohexstring(res)
               return res
          except:
               import traceback
               traceback.print_stack()
               traceback.print_exc()
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
          f.write("result['%s']=%s\n" % (key, prettyprintdict(dict[key])))
     f.write("FILEVERSION=%d\n" % (currentversion,))
     f.close()

def formatexception(excinfo=None, lastframes=6):
     """Pretty print exception, including local variable information.

     See Python Cookbook, recipe 14.4.

     @param excinfo: tuple of information returned from sys.exc_info when
               the exception occurred.  If you don't supply this then
               information about the current exception being handled
               is used
     @param lastframes: local variables are shown for these number of
                  frames
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
                    print >>s,`value`[:60]
               except:
                    print >>s,"(Exception occurred printing value)"
     return s.getvalue()
                    
          
     

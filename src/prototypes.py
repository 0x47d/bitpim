### BITPIM
###
### Copyright (C) 2003-2004 Roger Binns <rogerb@rogerbinns.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""The various types used in protocol descriptions

To implement a type used for protocol descriptions,
examine the code for UINTlsb in this file.  Of note:

  - Inherit from BaseProtogenClass
  - Call superclass constructors using super()
  - Do not process any of the args or kwargs in the constructor unless
    you need them to alter how you are constructed
  - At the end of the constructor, call _update if you are the most
    derived class
  - In _update, call super()._update, and then delete keyword arguments
    as you process them (consider using L{BaseProtogenClass._consumekw} function)
  - If you are the most derived class, complain about
    unused keyword arguments (consider using
    L{BaseProtogenClass._complainaboutunusedargs} function)
  - set _bufferstartoffset and _bufferendoffset whenever
    you are read or written from a buffer
  - (optionally) define a getvalue() method that returns
    a better type.  For example if your class is integer
    like then this would return a real int.  If string like,
    then this will return a real string.
  - If you are a container, override iscontainer.  You will
    also need to provide a containerelements() method which
    lets you iterate over the entries.

containerelements method:

  - You should return tuples of (fieldname, fieldvalue, descriptionstring or None)
  - fieldvalue should be the actual object, not a pretty version (eg a STRING not str)
  
    
"""

import cStringIO

import common

class ProtogenException(Exception):
    """Base class for exceptions encountered with data marshalling"""
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

class SizeNotKnownException(ProtogenException):
    "Unable to marshal since size isn't known"
    def __init__(self):
        ProtogenException.__init__(self, "The size of this item is not known and hence cannot be en/decoded")

class ValueNotSetException(ProtogenException):
    "Value not been set"
    def __init__(self):
        ProtogenException.__init__(self, "The value for this object has not been set.")

class ValueException(ProtogenException):
    "Some sort of problem with the value"
    def __init__(self, str):
        ProtogenException.__init__(self,str)

class NotTerminatedException(ProtogenException):
    "The value should have been terminated and wasn't"
    def __init__(self):
        ProtogenException.__init__(self,"The value should have been terminated and wasn't")

class ValueLengthException(ProtogenException):
    "The value is the wrong size (too big or too small)"
    def __init__(self, sz, space):
        ProtogenException.__init__(self, "The value (length %d) is the wrong size for space %d" % (sz,space))
    
class MissingQuotesException(ProtogenException):
    "The value does not have quotes around it"
    def __init__(self):
        ProtogenException.__init__(self, "The value does not have the required quote characters around it")
    

class BaseProtogenClass(object):
    """All types are derived from this"""
    def packetsize(self):
        "Returns size in bytes that we occupy"
        # This is implemented by writing to a buffer and seeing how big the result is.
        # The code generator used to make one per class but it was so rarely used (twice)
        # that this implementation is available instead
        b=buffer()
        self.writetobuffer(b)
        return len(b.getvalue())
        
    def writetobuffer(self, buf):
        "Scribble ourselves to the buf"
        raise NotImplementedError("writetobuffer()")
    def readfrombuffer(self, buf):
        "Get our value from the buffer"
        raise NotImplementedError("readfrombuffer()")
    def getvalue(self):
        "Returns our underlying value if sensible (eg an integer, string or list) else returns self"
        return self
    def packetspan(self):
        """Returns tuple of begining,end offsets from last packet we were read or written from.

        Note that in normal Python style, end is one beyond the last byte we
        actually own"""
        return self._bufferstartoffset, self._bufferendoffset
    def _consumekw(self, dict, consumelist):
        """A helper function for easily setting internal values from the dict

        For each name in consumelist, we look for it in the dict and
        set self._name to the value from dict.  The key is then deleted
        from the dict."""
        for name in consumelist:
            if dict.has_key(name):
                setattr(self, "_"+name, dict[name])
                del dict[name]
    def _complainaboutunusedargs(self, klass, dict):
        """A helper function that will raise an exception if there are unused keyword arguments.

        @Note: that we only complain if in the most derived class, so it is safe
        to always call this helper as the last line of your constructor.

        @param klass:  This should be the class you are calling this function from
        @param dict:   The keyword arguments still in play
        """
        if len(dict) and self.__class__.__mro__[0]==klass:
            raise TypeError('Unexpected keyword args supplied: '+`dict`)

    def _ismostderived(self, klass):
        
        return self.__class__.__mro__[0]==klass

    def _update(self, args, kwargs):
        return

    def iscontainer(self):
        """Do we contain fields?"""
        return False

    def update(self, *args, **kwargs):
        self._update(args, kwargs)

class UINTlsb(BaseProtogenClass):
    "An integer in Least Significant Byte first order"
    def __init__(self, *args, **kwargs):
        """
        An integer value can be specified in the constructor, or as the value keyword arg.

        @keyword constant:  (Optional) A constant value.  All reads must have this value
        @keyword sizeinbytes: (Mandatory for writing, else Optional) How big we are in bytes
        @keyword default:  (Optional) Our default value
        @keyword value: (Optional) The value
        """
        super(UINTlsb, self).__init__(*args, **kwargs)
        self._constant=None
        self._sizeinbytes=None
        self._value=None
        self._default=None

        if self._ismostderived(UINTlsb):
            self._update(args,kwargs)


    def _update(self, args, kwargs):
        super(UINTlsb,self)._update(args, kwargs)
        
        self._consumekw(kwargs, ("constant", "sizeinbytes", "default", "value"))
        self._complainaboutunusedargs(UINTlsb,kwargs)

        # Set our value if one was specified
        if len(args)==0:
            pass
        elif len(args)==1:
            self._value=int(args[0])
        else:
            raise TypeError("Unexpected arguments "+`args`)

        if self._value is None and self._default is not None:
            self._value=self._default

        if self._value is None and self._constant is not None:
            self._value=self._constant

        if self._constant is not None and self._constant!=self._value:
            raise ValueException("This field is a constant of %d.  You tried setting it to %d" % (self._constant, self._value))


    def readfrombuffer(self, buf):
        if self._sizeinbytes is None:
            raise SizeNotKnownException()
        self._bufferstartoffset=buf.getcurrentoffset()
        # lsb read
        res=0
        shift=0
        for dummy in range(self._sizeinbytes):
            res|=buf.getnextbyte()<<shift
            shift+=8
        self._value=res
        self._bufferendoffset=buf.getcurrentoffset()
        if self._constant is not None and self._value!=self._constant:
            raise ValueException("The value read should be a constant of %d, but was %d instead" % (self._constant, self._value))
         
    def writetobuffer(self, buf):
        if self._sizeinbytes is None:
            raise SizeNotKnownException()
        if self._value is None:
            raise ValueNotSetException()
        
        self._bufferstartoffset=buf.getcurrentoffset()
        # lsb write
        res=self._value
        for dummy in range(self._sizeinbytes):
            buf.appendbyte(res&0xff)
            res>>=8
        self._bufferendoffset=buf.getcurrentoffset()

    def packetsize(self):
        if self._sizeinbytes is None:
            raise SizeNotKnownException()
        return self._sizeinbytes
        
    def getvalue(self):
        """Returns the integer we are"""
        if self._value is None:
            raise ValueNotSetException()
        return self._value

class BOOLlsb(UINTlsb):
    "An Boolean in Least Significant Byte first order"
    def __init__(self, *args, **kwargs):
        """
        A boolean value can be specified in the constructor.

        Keyword arguments are the same a UINTlsb
        """
        super(BOOLlsb, self).__init__(*args, **kwargs)

        if self._ismostderived(BOOLlsb):
            self._update(args,kwargs)

    def _update(self, args, kwargs):
        super(BOOLlsb,self)._update(args,kwargs)
        self._complainaboutunusedargs(BOOLlsb,kwargs)
        self._boolme()

    def _boolme(self):
        if self._value is not None:
            self._value=bool(self._value)

    def readfrombuffer(self, buf):
        UINTlsb.readfrombuffer(self,buf)
        self._boolme()
    

class STRING(BaseProtogenClass):
    "A text string"
    def __init__(self, *args, **kwargs):
        """
        A string value can be specified to this constructor, or in the value keyword arg.

        @keyword constant: (Optional) A constant value.  All reads must have this value
        @keyword terminator: (Default=0) The string terminator (or None).  If set there will
             always be a terminator when writing.  The terminator is not returned when getting
             the value.
        @keyword pad: (Default=0) The padding byte if fixed length when writing, or stripped off
                       when reading
        @keyword sizeinbytes: (Optional) Set if fixed length.
             If not set, then the terminator will be used to find the end of strings on reading.
             If not set and the terminator is None, then reads will be entire rest of buffer.
        @keyword default: (Optional) Our default value
        @keyword raiseonunterminatedread: (Default True) raise L{NotTerminatedException} if there is
             no terminator on the value being read in.  terminator must also be set.
        @keyword raiseontruncate: (Default True) raise L{ValueLengthException} if the supplied
             value is too large to fit within sizeinbytes.
        @keyword value: (Optional) Value
        @keyword pascal: (Default False) The string is preceded with one byte giving the length
                         of the string (including terminator if there is one)
        """
        super(STRING, self).__init__(*args, **kwargs)
        
        self._constant=None
        self._terminator=0
        self._pad=0
        self._sizeinbytes=None
        self._default=None
        self._raiseonunterminatedread=True
        self._raiseontruncate=True
        self._value=None
        self._pascal=False

        if self._ismostderived(STRING):
            self._update(args,kwargs)

    def _update(self, args, kwargs):
        super(STRING,self)._update(args, kwargs)

        self._consumekw(kwargs, ("constant", "terminator", "pad", "pascal",
        "sizeinbytes", "default", "raiseonunterminatedread", "value", "raiseontruncate"))
        self._complainaboutunusedargs(STRING,kwargs)

        # Set our value if one was specified
        if len(args)==0:
            pass
        elif len(args)==1:
            self._value=common.forceascii(args[0])
            if self._constant is not None and self._constant!=self._value:
                raise ValueException("This field is a constant of '%s'.  You tried setting it to '%s'" % (self._constant, self._value))
        else:
            raise TypeError("Unexpected arguments "+`args`)
        if self._value is None and self._default is not None:
            self._value=self._default

        if self._value is not None:
            self._value=str(self._value) # no unicode here!
            if self._sizeinbytes is not None:
                l=len(self._value)
                if self._terminator is not None:
                    l+=1
                if l>self._sizeinbytes:
                    if self._raiseontruncate:
                        raise ValueLengthException(l, self._sizeinbytes)
                    
                    self._value=self._value[:self._sizeinbytes]
                    if len(self._value) and self._terminator is not None:
                        self._value=self._value[:-1]

    def readfrombuffer(self, buf):
        self._bufferstartoffset=buf.getcurrentoffset()

        if self._pascal:
            self._sizeinbytes=buf.getnextbyte()

        if self._sizeinbytes is not None:
            # fixed size
            self._value=buf.getnextbytes(self._sizeinbytes)
            if self._terminator is not None:
                # using a terminator
                pos=self._value.find(chr(self._terminator))
                if pos>=0:
                    self._value=self._value[:pos]
                elif self._raiseonunterminatedread:
                    raise NotTerminatedException()
            elif self._pad is not None:
                # else remove any padding
                while len(self._value) and self._value[-1]==chr(self._pad):
                    self._value=self._value[:-1]
        else:
            if self._terminator is None:
                # read in entire rest of packet
                self._value=buf.getremainingbytes()
            else:
                # read up to terminator
                self._value=""
                while buf.hasmore():
                    self._value+=chr(buf.getnextbyte())
                    if self._value[-1]==chr(self._terminator):
                        break
                if self._value[-1]!=chr(self._terminator):
                    if self._raiseonunterminatedread:
                        raise NotTerminatedException()
                else:
                    self._value=self._value[:-1]

        if self._constant is not None and self._value!=self._constant:
            raise ValueException("The value read was not the constant")

        self._bufferendoffset=buf.getcurrentoffset()

    def writetobuffer(self, buf):
        if self._value is None:
            raise ValueNotSetException()
                
        self._bufferstartoffset=buf.getcurrentoffset()
        if self._pascal:
            l=len(self._value)
            if self._terminator is not None:
                l+=1
            buf.appendbyte(l)
        buf.appendbytes(self._value)
        l=len(self._value)
        if self._terminator is not None:
            buf.appendbyte(self._terminator)
            l+=1
        if self._sizeinbytes is not None:
            if l<self._sizeinbytes:
                buf.appendbytes(chr(self._pad)*(self._sizeinbytes-l))

        self._bufferendoffset=buf.getcurrentoffset()

    def packetsize(self):
        if self._sizeinbytes is not None:
            return self._sizeinbytes

        if self._value is None:
            raise ValueNotSetException()

        l=len(self._value)
        if self._terminator is not None:
            l+=1

        return l

    def getvalue(self):
        """Returns the string we are"""
        if self._value is None:
            raise ValueNotSetException()
        return self._value

class SAMSTRING(BaseProtogenClass):
    """A text string enclosed in quotes, with a way to escape quotes that a supposed
    to be part of the string.  Typical of Samsung phones."""
    # Is there a better name for this than SAMSTRING?  Perhaps QUOTEDSTRING,
    # ASCIISTRING, CSVSTRING...?
    def __init__(self, *args, **kwargs):
        """
        A string value can be specified to this constructor, or in the value keyword arg.

        @keyword constant: (Optional) A constant value.  All reads must have this value
        @keyword terminator: (Default=,) The string terminator (or None).  If set there will
             always be a terminator when writing.  The terminator is not returned when getting
             the value.
        @keyword quotechar: (Default=Double Quote) Quote character that surrounds string
        @keyword readescape: (Default=True) Interpret PPP escape char (0x7d)
        @keywors writeescape: (Default=False) Escape quotechar.  If false, drop quotechar in string.
        @keyword maxsizeinbytes: (Optional) On writing, truncate strings longer than this (length is before
                       any escaping and quoting
        @keyword default: (Optional) Our default value
        @keyword raiseonunterminatedread: (Default True) raise L{NotTerminatedException} if there is
             no terminator on the value being read in.  terminator must also be set.
        @keyword raiseontruncate: (Default True) raise L{ValueLengthException} if the supplied
             value is too large to fit within sizeinbytes.
        @keyword raiseonmissingquotes: (Default True) raise L{MissingQuotesException} if the string does
             not have quote characters around it
        @keyword value: (Optional) Value
        """
        super(SAMSTRING, self).__init__(*args, **kwargs)
        
        self._constant=None
        self._terminator=ord(',')
        self._quotechar=ord('"')
        self._readescape=True
        self._writeescape=False
        self._maxsizeinbytes=None
        self._default=None
        self._raiseonunterminatedread=True
        self._raiseontruncate=True
        self._raiseonmissingquotes=True
        self._value=None

        if self._ismostderived(SAMSTRING):
            self._update(args,kwargs)

    def _update(self, args, kwargs):
        super(SAMSTRING,self)._update(args, kwargs)

        self._consumekw(kwargs, ("constant", "terminator", "quotechar", "readescape",
        "writeescape", "maxsizeinbytes", "default",
        "raiseonunterminatedread", "value", "raiseontruncate","raiseonmissingquotes"))
        self._complainaboutunusedargs(SAMSTRING,kwargs)

        # Set our value if one was specified
        if len(args)==0:
            pass
        elif len(args)==1:
            self._value=common.forceascii(args[0])
            if self._constant is not None and self._constant!=self._value:
                raise ValueException("This field is a constant of '%s'.  You tried setting it to '%s'" % (self._constant, self._value))
        else:
            raise TypeError("Unexpected arguments "+`args`)
        if self._value is None and self._default is not None:
            self._value=self._default

        if self._value is not None:
            self._value=str(self._value) # no unicode here!
            if self._maxsizeinbytes is not None:
                l=len(self._value)
                if l>self._maxsizeinbytes:
                    if self._raiseontruncate:
                        raise ValueLengthException(l, self._sizeinbytes)
                    
                    self._value=self._value[:self._sizeinbytes]

    def readfrombuffer(self, buf):
        self._bufferstartoffset=buf.getcurrentoffset()

        # First character better be a terminator
        # Raise on, first char not quote, trailing quote never found, character after last quote
        # not , or EOL.  Will need an option to not raise if initial quote not found

        if self._terminator is None:
            # read in entire rest of packet
            # Ignore maxsizeinbytes
            # Check for leading and trailing quotes later
            self._value=buf.getremainingbytes()
        else:
            # Possibly quoted string.  If first character is not a quote, read until
            # terminator or end of line.  Exception will be thrown after reading if
            # the string was not quoted and it was supposed to be.
            self._value=chr(buf.getnextbyte())
            if self._value == ',':
                self._value = ''
            else:
                inquotes=False
                if self._quotechar is not None:
                    if self._value[0]==chr(self._quotechar):
                        inquotes=True
                while buf.hasmore():
                    self._value+=chr(buf.getnextbyte())
                    if inquotes:
                        if self._value[-1]==chr(self._quotechar):
                            inquotes=False
                    else:
                        if self._value[-1]==chr(self._terminator):
                            break
                if self._value[-1]==self._terminator:
                    if self._raiseonunterminatedread:
                        raise NotTerminatedException()
                else:
                    self._value=self._value[:-1]

        if self._quotechar is not None:
            if self._value[0]==chr(self._quotechar) and self._value[-1]==chr(self._quotechar):
                self._value=self._value[1:-1]
            else:
                raise MissingQuotesException()

        if self._readescape:
            self._value=common.pppunescape(self._value)
            
        if self._constant is not None and self._value!=self._constant:
            raise ValueException("The value read was not the constant")

        self._bufferendoffset=buf.getcurrentoffset()

    def writetobuffer(self, buf):
        # Need to raise exception if string exceeds maxsizeinbytes
        if self._value is None:
            raise ValueNotSetException()
                
        self._bufferstartoffset=buf.getcurrentoffset()

        if self._quotechar is not None:
            buf.appendbyte(self._quotechar)
        buf.appendbytes(self._value)
        if self._quotechar is not None:
            buf.appendbyte(self._quotechar)
        if self._terminator is not None:
            buf.appendbyte(self._terminator)

        self._bufferendoffset=buf.getcurrentoffset()

    def packetsize(self):
        if self._sizeinbytes is not None:
            return self._sizeinbytes

        if self._value is None:
            raise ValueNotSetException()

        l=len(self._value)
        if self._terminator is not None:
            l+=1

        return l

    def getvalue(self):
        """Returns the string we are"""
        if self._value is None:
            raise ValueNotSetException()
        return self._value

class SAMINT(SAMSTRING):
    """Integers in CSV lines"""
    def __init__(self, *args, **kwargs):
        super(SAMINT,self).__init__(*args, **kwargs)

        self._quotechar=None

        if self._ismostderived(SAMINT):
            self._update(args,kwargs)

    def _update(self, args, kwargs):
        for k in 'constant', 'default', 'value':
            if kwargs.has_key(k):
                kwargs[k]=str(kwargs[k])
        if len(args)==0:
            pass
        elif len(args)==1:
            args=(str(args[0]),)
        else:
            raise TypeError("expected integer as arg")
            
        super(SAMINT,self)._update(args,kwargs)
        self._complainaboutunusedargs(SAMINT,kwargs)
        
    def getvalue(self):
        """Convert the string into an integer

        @rtype: integer
        """

        # Will probably want an flag to allow null strings, converting
        # them to a default value
        
        val=super(SAMINT,self).getvalue()
        try:
            ival=int(val)
        except:
            try:
                ival=int(self._default)
            except:
                raise ValueException("The field '%s' is not an integer" % (val))
        return ival

class SAMDATE(SAMSTRING):
    """Dates in CSV lines"""
    def __init__(self, *args, **kwargs):
        super(SAMDATE,self).__init__(*args, **kwargs)

        self._valuedate=(0,0,0) # Year month day

        self._quotechar=None
        
        if self._ismostderived(SAMDATE):
            self._update(args,kwargs)

    def _update(self, args, kwargs):
        for k in 'constant', 'default', 'value':
            if kwargs.has_key(k):
                kwargs[k]=self._converttostring(kwargs[k])
        if len(args)==0:
            pass
        elif len(args)==1:
            args=(self._converttostring(args[0]),)
        else:
            raise TypeError("expected (year,month,day) as arg")

        super(SAMDATE,self)._update(args, kwargs) # we want the args
        self._complainaboutunusedargs(SAMDATE,kwargs)

    def getvalue(self):
        """Unpack the string into the date

        @rtype: tuple
        @return: (year, month, day)
        """

        s=super(SAMDATE,self).getvalue()
        val=s.split("/") # List of of Month, day, year
        year=int(val[2])
        month=int(val[0])
        day=int(val[1])
        return (year, month, day)
        
    def _converttostring(self, date):
        year,month,day=date
        s='%2.2d/%2.2d/%4.4d'%(month, day, year)
        return s
        

class SAMTIME(SAMSTRING):
    """Timestamp in CSV lines"""
    def __init__(self, *args, **kwargs):
        super(SAMTIME,self).__init__(*args, **kwargs)

        self._valuetime=(0,0,0,0,0,0) # Year month day, hour, minute, second

        self._quotechar=None
        
        if self._ismostderived(SAMTIME):
            self._update(args,kwargs)

    def _update(self, args, kwargs):
        for k in 'constant', 'default', 'value':
            if kwargs.has_key(k):
                kwargs[k]=self._converttostring(kwargs[k])
        if len(args)==0:
            pass
        elif len(args)==1:
            args=(self._converttostring(args[0]),)
        else:
            raise TypeError("expected (year,month,day) as arg")

        super(SAMTIME,self)._update(args, kwargs) # we want the args
        self._complainaboutunusedargs(SAMTIME,kwargs)

    def getvalue(self):
        """Unpack the string into the date

        @rtype: tuple
        @return: (year, month, day)
        """

        s=super(SAMTIME,self).getvalue()
        year=int(s[0:4])
        month=int(s[4:6])
        day=int(s[6:8])
        hour=int(s[9:11])
        minute=int(s[11:13])
        second=int(s[13:15])
        return (year, month, day, hour, minute, second)
        
    def _converttostring(self, time):
        year,month,day,hour,minute,second=time
        s='%4.4d%2.2d%2.2dT%2.2d%2.2d%2.2d'%(year, month, day, hour, minute, second)
        return s
        

class COUNTEDBUFFEREDSTRING(BaseProtogenClass):
    """A string as used on Audiovox.  There is a one byte header saying how long the string
    is, followed by the string in a fixed sized buffer"""
    def __init__(self, *args, **kwargs):
        """
        A string value can be specified to this constructor, or in the value keyword arg.

        @keyword constant: (Optional) A constant value.  All reads must have this value
        @keyword pad: (Default=32 - space) When writing, what to pad the rest of the buffer with
        @keyword default: (Optional) Our default value
        @keyword raiseontruncate: (Default True) raise L{ValueLengthException} if the supplied
             value is too large to fit within the buffer.
        @keyword value: (Optional) Value
        @keyword sizeinbytes: (Mandatory) Size of the buffer, including the count byte
        """
        super(COUNTEDBUFFEREDSTRING,self).__init__(*args, **kwargs)

        self._constant=None
        self._pad=32
        self._sizeinbytes=None
        self._default=None
        self._raiseontruncate=True
        self._value=None

        if self._ismostderived(COUNTEDBUFFEREDSTRING):
            self._update(args, kwargs)

    def _update(self, args, kwargs):
        super(COUNTEDBUFFEREDSTRING,self)._update(args, kwargs)

        self._consumekw(kwargs, ("constant", "pad", "sizeinbytes", "default", "raiseontruncate", "value"))
        self._complainaboutunusedargs(COUNTEDBUFFEREDSTRING,kwargs)
        # Set our value if one was specified
        if len(args)==0:
            pass
        elif len(args)==1:
            self._value=str(args[0])
            if self._constant is not None and self._constant!=self._value:
                raise ValueException("This field is a constant of '%s'.  You tried setting it to '%s'" % (self._constant, self._value))
        else:
            raise TypeError("Unexpected arguments "+`args`)
        if self._value is None and self._default is not None:
            self._value=self._default

        if self._sizeinbytes is None:
            raise ValueException("sizeinbytes must be specified for COUNTEDBUFFEREDSTRING")

        if self._value is not None:
            l=len(self._value)
            if l>self._sizeinbytes-1:
                if self._raiseontruncate:
                    raise ValueLengthException(l, self._sizeinbytes-1)
                    
                self._value=self._value[:self._sizeinbytes-1]

    def readfrombuffer(self, buf):
        assert self._sizeinbytes is not None
        self._bufferstartoffset=buf.getcurrentoffset()

        strlen=buf.getnextbyte()
        if strlen>self._sizeinbytes-1:
            raise ValueException("counter specifies size of %d which is greater than remaining stringbuffer size of %d!" % (strlen, self._sizeinbytes-1))
        self._value=buf.getnextbytes(self._sizeinbytes-1) # -1 due to counter byte
        self._value=self._value[:strlen]
        if self._constant is not None and self._value!=self._constant:
            raise ValueException("The value read was not the constant")

        self._bufferendoffset=buf.getcurrentoffset()

    def writetobuffer(self, buf):
        assert self._sizeinbytes is not None
        if self._value is None:
            raise ValueNotSetException()

        self._bufferstartoffset=buf.getcurrentoffset()
        buf.appendbyte(len(self._value))
        buf.appendbytes(self._value)
        if len(self._value)+1<self._sizeinbytes:
            buf.appendbytes(chr(self._pad)*(self._sizeinbytes-1-len(self._value)))

        self._bufferendoffset=buf.getcurrentoffset()

    def packetsize(self):
        assert self._sizeinbytes is not None
        return self._sizeinbytes

    def getvalue(self):
        """Returns the string we are"""
        if self._value is None:
            raise ValueNotSetException()
        return self._value
            
class DATA(BaseProtogenClass):
    "A block of bytes"
    def __init__(self, *args, **kwargs):
        """
        A data value can be specified to this constructor or in the value keyword arg

        @keyword constant: (Optional) A constant value.  All reads must have this value
        @keyword pad: (Default=0) The padding byte if fixed length when writing and the
             value isn't long enough
        @keyword sizeinbytes: (Optional) Set if fixed length.
             If not set, then the rest of the packet will be consumed on reads.
        @keyword default: (Optional) Our default value
        @keyword raiseonwrongsize: (Default True) raise L{ValueLengthException} if the supplied
             value is too large to fit within sizeinbytes.
        """
        super(DATA, self).__init__(*args, **kwargs)
        
        self._constant=None
        self._pad=0
        self._sizeinbytes=None
        self._default=None
        self._raiseonwrongsize=True
        self._value=None

        if self._ismostderived(DATA):
            self._update(args,kwargs)

    def _update(self, args, kwargs):
        super(DATA,self)._update(args, kwargs)

        self._consumekw(kwargs, ("constant", "pad", "sizeinbytes", "default", "raiseonwrongsize", "value"))
        self._complainaboutunusedargs(DATA,kwargs)

        # Set our value if one was specified
        if len(args)==0:
            pass
        elif len(args)==1:
            self._value=args[0]
            if self._constant is not None and self._constant!=self._value:
                raise ValueException("This field is a constant and you set it to a different value")
        else:
            raise TypeError("Unexpected arguments "+`args`)
        if self._value is None and self._default is not None:
            self._value=self._default

        if self._value is not None:
            if self._sizeinbytes is not None:
                l=len(self._value)
                if l<self._sizeinbytes:
                    if self._pad is not None:
                        self._value+=chr(self._pad)*(self._sizeinbytes-l)

                l=len(self._value)

                if l!=self._sizeinbytes:
                    if self._raiseonwrongsize:
                        raise ValueLengthException(l, self._sizeinbytes)
                    else:
                        self._value=self._value[:self._sizeinbytes]


    def readfrombuffer(self, buf):
        self._bufferstartoffset=buf.getcurrentoffset()

        if self._sizeinbytes is not None:
            # fixed size
            self._value=buf.getnextbytes(self._sizeinbytes)
        else:
            # read in entire rest of packet
            self._value=buf.getremainingbytes()

        if self._constant is not None and self._value!=self._constant:
            raise ValueException("The value read was not the constant")
        self._bufferendoffset=buf.getcurrentoffset()

    def writetobuffer(self, buf):
        if self._value is None:
            raise ValueNotSetException()
                
        self._bufferstartoffset=buf.getcurrentoffset()
        buf.appendbytes(self._value)
        self._bufferendoffset=buf.getcurrentoffset()

    def packetsize(self):
        if self._sizeinbytes is not None:
            return self._sizeinbytes

        if self._value is None:
            raise ValueNotSetException()

        l=len(self._value)

        return l

    def getvalue(self):
        """Returns the bytes we are"""
        if self._value is None:
            raise ValueNotSetException()
        return self._value


class UNKNOWN(DATA):
    "A block of bytes whose purpose we don't know"

    def __init__(self, *args, **kwargs):
        """
        Same arguments as L{DATA.__init__}.  We default to a block
        of pad chars (usually \x00)
        """
        dict={'pad':0 , 'default': ""}
        dict.update(kwargs)
        super(UNKNOWN,self).__init__(*args, **dict)

        if self._ismostderived(UNKNOWN):
            self._update(args,dict)

    def _update(self, args, kwargs):
        super(UNKNOWN,self)._update(args, kwargs)
        self._complainaboutunusedargs(UNKNOWN,kwargs)

        # Was a value specified?
        if len(args):
            raise TypeError("Unexpected arguments "+`args`)

class LIST(BaseProtogenClass):
    """A list of items

    You can generally treat this class as though it is a list.  Note that some
    list like methods haven't been implemented (there are so darn many!)  If you
    are missing one you want to use, please add it to this class.
    """

    def __init__(self, *args, **kwargs):
        """
        You can pass objects to start the list with, or to the value keyword arg

        @keyword createdefault:  (Default False) Creates default members of the list if enough
            were not supplied before writing.
        @keyword length:  (Optional) How many items there are in the list
        @keyword raiseonbadlength: (Default True) raises L{ValueLengthException} if there are
            the wrong number of items in the list.  Note that this checking is only done
            when writing or reading from a buffer.  length must be set for this to have any
            effect.  If you have createdefault set then having less than length elements will
            not cause the exception.
        @keyword elementclass: (Mandatory) The class of each element
        @keyword elementinitkwargs: (Optional) KWargs for the constructor of each element
        @keyword value: (Optional) Value
        """
        self._thelist=[]
        super(LIST, self).__init__(*args, **kwargs)
        self._createdefault=False
        self._length=None
        self._raiseonbadlength=True
        self._elementclass=None
        self._elementinitkwargs={}

        if self._ismostderived(LIST):
            self._update(args,kwargs)

    def _update(self, args, kwargs):
        super(LIST,self)._update(args, kwargs)
        self._consumekw(kwargs, ("createdefault","length","raiseonbadlength","elementclass","elementinitkwargs"))
        if kwargs.has_key("value"):
            self._thelist=list(kwargs['value'])
            del kwargs['value']
            
        self._complainaboutunusedargs(LIST,kwargs)

        if self._elementclass is None:
            raise TypeError("elementclass argument was not supplied")
        
        if len(args):
            self.extend(args)

    def readfrombuffer(self,buf):
        self._bufferstartoffset=buf.getcurrentoffset()
        # delete all existing items
        self._thelist=[]
            
        if self._length is None:
            # read rest of buffer
            while buf.hasmore():
                x=self._makeitem()
                x.readfrombuffer(buf)
                self._thelist.append(x)
        else:
            for dummy in range(self._length):
                # read specified number of items
                x=self._makeitem()
                x.readfrombuffer(buf)
                self._thelist.append(x)

        self._bufferendoffset=buf.getcurrentoffset()

    def writetobuffer(self, buf):
        self._bufferstartoffset=buf.getcurrentoffset()

        self._ensurelength()
        for i in self:
            i.writetobuffer(buf)

        self._bufferendoffset=buf.getcurrentoffset()

    def packetsize(self):
        self._ensurelength()
        sz=0
        for item in self:
            sz+=item.packetsize()
        return sz

    def iscontainer(self):
        return True

    def containerelements(self):
        self._ensurelength()
        for i,v in enumerate(self._thelist):
            yield "["+`i`+"]",v,None
        

    # Provide various list methods.  I initially tried just subclassing list,
    # but it was impossible to tell which methods needed to be reimplemented.
    # I was concerned about double conversions.
    # For example if my append turned the item into elementclass
    # and then the builtin list append called setitem to do the append, which I
    # also override so it then converts the elementclass into another
    # elementclass.
    def append(self, item):
        self._thelist.append(self._makeitem(item))

    def extend(self, items):
        self._thelist.extend(map(self._makeitem, items))

    def insert(self, index, item):
        self._thelist.insert(index, self._makeitem(item))

    def __getitem__(self, index):
        return self._thelist[index]

    def __iter__(self):
        try:
            return self._thelist.__iter__()
        except:
            return self.__fallbackiter()

    def __fallbackiter(self):
        # used for Python 2.2 which doesn't have list.__iter__
        for item in self._thelist:
            yield item

    def __len__(self):
        return self._thelist.__len__()

    def __setitem__(self, index, value):
        self._thelist.__setitem__(index, self._makeitem(value))

    def __delitem__(self, index):
        self._thelist.__delitem__(index)
        

    def _makeitem(self, *args, **kwargs):
        "Creates a child element"
        # if already of the type, then return it
        if len(args)==1 and isinstance(args[0], self._elementclass):
            return args[0]
        d={}
        d.update(self._elementinitkwargs)
        d.update(kwargs)
        return self._elementclass(*args, **d)

    def _ensurelength(self):
        "Ensures we are the correct length"
        if self._createdefault and self._length is not None and len(self._thelist)<self._length:
            while len(self._thelist)<self._length:
                x=self._makeitem()
                self._thelist.append(x)
            return
        if self._length is not None and self._raiseonbadlength and len(self._thelist)!=self._length:
            raise ValueLengthException(len(self), self._length)

# Strictly speaking, this should be in one of the LG files
class LGCALDATE(UINTlsb):
    def __init__(self, *args, **kwargs):
        """A date/time as used in the LG calendar"""
        super(LGCALDATE,self).__init__(*args, **kwargs)
        self._valuedate=(0,0,0,0,0)  # year month day hour minute

        dict={'sizeinbytes': 4}
        dict.update(kwargs)

        if self._ismostderived(LGCALDATE):
            self._update(args,kwargs)

    def _update(self, args, kwargs):
        for k in 'constant', 'default', 'value':
            if kwargs.has_key(k):
                kwargs[k]=self._converttoint(kwargs[k])
        if len(args)==0:
            pass
        elif len(args)==1:
            args=(self._converttoint(args[0]),)
        else:
            raise TypeError("expected (year,month,day,hour,minute) as arg")

        super(LGCALDATE,self)._update(args, kwargs) # we want the args
        self._complainaboutunusedargs(LGCALDATE,kwargs)
        assert self._sizeinbytes==4

    def getvalue(self):
        """Unpack 32 bit value into date/time

        @rtype: tuple
        @return: (year, month, day, hour, minute)
        """
        val=super(LGCALDATE,self).getvalue()
        min=val&0x3f # 6 bits
        val>>=6
        hour=val&0x1f # 5 bits (uses 24 hour clock)
        val>>=5
        day=val&0x1f # 5 bits
        val>>=5
        month=val&0xf # 4 bits
        val>>=4
        year=val&0xfff # 12 bits
        return (year, month, day, hour, min)

    def _converttoint(self, date):
        assert len(date)==5
        year,month,day,hour,min=date
        if year>4095:
            year=4095
        val=year
        val<<=4
        val|=month
        val<<=5
        val|=day
        val<<=5
        val|=hour
        val<<=6
        val|=min
        return val

            


class buffer:
    "This is used for reading and writing byte data"
    def __init__(self, data=None):
        "Call with data to read from it, or with None to write to it"
        if data is not None:
            self._data=data
        else:
            self._buffer=cStringIO.StringIO()

        self._offset=0

    def getcurrentoffset(self):
        "Returns distance into data we are"
        return self._offset

    def peeknextbyte(self, howmuch=0):
        "Returns value of next byte, but doesn't advance position"
        if self._offset+howmuch>=len(self._data):
            return None
        return ord(self._data[self._offset+howmuch]) 

    def getnextbyte(self):
        "Returns next byte"
        if self._offset>=len(self._data):
            raise IndexError("trying to read one byte beyond end of "+`len(self._data)`+" byte buffer")
        res=ord(self._data[self._offset])
        self._offset+=1
        return res

    def getnextbytes(self, howmany):
        "Returns howmany bytes"
        assert howmany>=0
        if self._offset+howmany>len(self._data):
            raise IndexError("Trying to read "+`howmany`+" bytes starting at "+`self._offset`+" which will go beyond end of "+`len(self._data)`+" byte buffer")
        res=self._data[self._offset:self._offset+howmany]
        self._offset+=howmany
        return res

    def peeknextbytes(self, howmany):
        if self._offset+howmany>len(self._data):
            return None
        return self._data[self._offset:self._offset+howmany]

    def getremainingbytes(self):
        "Returns rest of buffer"
        sz=len(self._data)-self._offset
        return self.getnextbytes(sz)

    def hasmore(self):
        "Is there any data left?"
        return self._offset<len(self._data)

    def howmuchmore(self):
        "Returns how many bytes left"
        return len(self._data)-self._offset

    def appendbyte(self, val):
        """Appends byte to data.
        @param val: a number 0 <= val <=255
        """
        assert val>=0 and val<=255
        self._buffer.write(chr(val))
        self._offset+=1
        assert self._offset==len(self._buffer.getvalue())

    def appendbytes(self, bytes):
        "Adds bytes to end"
        self._buffer.write(bytes)
        self._offset+=len(bytes)
        assert self._offset==len(self._buffer.getvalue())

    def getvalue(self):
        "Returns the buffer being built"
        return self._buffer.getvalue()

    def getdata(self):
        "Returns the data passed in"
        return self._data
        
    

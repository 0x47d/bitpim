#!/usr/bin/env python

"""The various types used in protocol descriptions

To implement a type used for protocol descriptions,
examine the code for UINTlsb in this file.  Of note:

  - Inherit from BaseProtogenClass
  - Call superclass constructors using super()
  - Delete keyword arguments as you process them
    (consider using L{BaseProtogenClass._consumekw} function)
  - If you are the most derived class, complain about
    unused keyword arguments (consider using
    L{BaseProtogenClass._complainaboutunusedargs} function)
  - set _bufferstartoffset and _bufferendoffset whenever
    you are read or written from a buffer
  - (optionally) define a getvalue() method that returns
    a better type.  For example if your class is integer
    like then this would return a real int.  If string link,
    then this will return a real string.
  - If you are a container, override iscontainer.  You will
    also need to provide a containerelements() method which
    lets you iterate over the entries.

containerelements method:

  - You should return tuples of (fieldname, fieldvalue, descriptionstring or None)
  - fieldvalue should be the actual object, not a pretty version (eg a STRING not str)
  
    
"""

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

class ValueError(ProtogenException):
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
    

class BaseProtogenClass(object):
    """All types are derived from this"""
    def packetsize(self):
        "Returns size in bytes that we occupy"
        raise NotImplementedError("packetsize()")
    def writetobuffer(self, buffer):
        "Scribble ourselves to the buffer"
        raise NotImplementedError("writetobuffer()")
    def readfrombuffer(self, buffer):
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
        @param dict:   The keyword arguments
        """
        if len(dict) and self.__class__.__mro__[0]==klass:
            raise TypeError('Unexpected keyword args supplied: '+`dict`)

    def iscontainer(self):
        return False

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
            raise ValueError("This field is a constant of %d.  You tried setting it to %d" % (self._constant, self._value))


    def readfrombuffer(self, buffer):
        if self._sizeinbytes is None:
            raise SizeNotKnownException()
        self._bufferstartoffset=buffer.getcurrentoffset()
        # lsb read
        res=0
        shift=0
        for dummy in range(self._sizeinbytes):
            res|=buffer.getnextbyte()<<shift
            shift+=8
        self._value=res
        self._bufferendoffset=buffer.getcurrentoffset()
        if self._constant is not None and self._value!=self._constant:
            raise ValueError("The value read should be a constant of %d, but was %d instead" % (self._constant, self._value))
         
    def writetobuffer(self, buffer):
        if self._sizeinbytes is None:
            raise SizeNotKnownException()
        if self._value is None:
            raise ValueNotSetException()
        
        self._bufferstartoffset=buffer.getcurrentoffset()
        # lsb write
        res=self._value
        for dummy in range(self._sizeinbytes):
            buffer.appendbyte(res&0xff)
            res>>=8
        self._bufferendoffset=buffer.getcurrentoffset()

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
        self._complainaboutunusedargs(UINTlsb,kwargs)

        self._boolme()

    def _boolme(self):
        if self._value is not None:
            self._value=bool(self._value)

    def readfrombuffer(self, buffer):
        UINTlsb.readfrombuffer(self,buffer)
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
        @keyword pad: (Default=0) The padding byte if fixed length when writing
        @keyword sizeinbytes: (Optional) Set if fixed length.
             If not set, then the terminator will be used to find the end of strings on reading.
             If not set and the terminator is None, then reads will be entire rest of buffer.
        @keyword default: (Optional) Our default value
        @keyword raiseonunterminatedread: (Default True) raise L{NotTerminatedException} if there is
             no terminator on the value being read in.  terminator must also be set.
        @keyword raiseontruncate: (Default True) raise L{ValueLengthException} if the supplied
             value is too large to fit within sizeinbytes.
        @keyword value: (Optional) Value
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

        self._consumekw(kwargs, ("constant", "terminator", "pad",
        "sizeinbytes", "default", "raiseonunterminatedread", "value"))
        self._complainaboutunusedargs(STRING,kwargs)

        # Set our value if one was specified
        if len(args)==0:
            pass
        elif len(args)==1:
            self._value=str(args[0])
            if self._constant is not None and self._constant!=self._value:
                raise ValueError("This field is a constant of '%s'.  You tried setting it to '%s'" % (self._constant, self._value))
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

    def readfrombuffer(self, buffer):
        self._bufferstartoffset=buffer.getcurrentoffset()

        if self._sizeinbytes is not None:
            # fixed size
            self._value=buffer.getnextbytes(self._sizeinbytes)
            if self._terminator is not None:
                pos=self._value.find(chr(self._terminator))
                if pos>=0:
                    self._value=self._value[pos]
                elif self._raiseonunterminatedread:
                    raise NotTerminatedException()
        else:
            if self._terminator is None:
                # read in entire rest of packet
                self._value=buffer.getremainingbytes()
            else:
                # read up to terminator
                self._value=""
                while buffer.hasmore():
                    self._value+=chr(buffer.getnextbyte())
                    if self._value[-1]==chr(self._terminator):
                        break
                if self._value[-1]!=chr(self._terminator):
                    if self._raiseonunterminatedread:
                        raise NotTerminatedException()
                else:
                    self._value=self._value[:-1]

        if self._constant is not None and self._value!=self._constant:
            raise ValueError("The value read was not the constant")

        self._bufferendoffset=buffer.getcurrentoffset()

    def writetobuffer(self, buffer):
        if self._value is None:
            raise ValueNotSetException()
                
        self._bufferstartoffset=buffer.getcurrentoffset()
        buffer.appendbytes(self._value)
        l=len(self._value)
        if self._terminator is not None:
            buffer.appendbyte(self._terminator)
            l+=1
        if self._sizeinbytes is not None:
            if l<self._sizeinbytes:
                buffer.appendbytes(chr(self._pad)*(self._sizeinbytes-l))

        self._bufferendoffset=buffer.getcurrentoffset()

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

        self._consumekw(kwargs, ("constant", "pad", "sizeinbytes", "default", "raiseonwrongsize", "value"))
        self._complainaboutunusedargs(DATA,kwargs)

        # Set our value if one was specified
        if len(args)==0:
            pass
        elif len(args)==1:
            self._value=args[0]
            if self._constant is not None and self._constant!=self._value:
                raise ValueError("This field is a constant and you set it to a different value")
        else:
            raise TypeError("Unexpected arguments "+`args`)
        if self._value is None and self._default is not None:
            self._value=self._default

        if self._value is not None:
            if self._sizeinbytes is not None:
                l=len(self._value)
                if l>self._sizeinbytes:
                    if self._raiseonwrongsize:
                        raise ValueLengthException(l, self._sizeinbytes)
                    
                    self._value=self._value[:self._sizeinbytes]

    def readfrombuffer(self, buffer):
        self._bufferstartoffset=buffer.getcurrentoffset()

        if self._sizeinbytes is not None:
            # fixed size
            self._value=buffer.getnextbytes(self._sizeinbytes)
        else:
            # read in entire rest of packet
            self._value=buffer.getremainingbytes()

        if self._constant is not None and self._value!=self._constant:
            raise ValueError("The value read was not the constant")
        self._bufferendoffset=buffer.getcurrentoffset()

    def writetobuffer(self, buffer):
        if self._value is None:
            raise ValueNotSetException()
                
        self._bufferstartoffset=buffer.getcurrentoffset()
        buffer.appendbytes(self._value)
        self._bufferendoffset=buffer.getcurrentoffset()

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
        super(UNKNOWN,self).__init__(*args, **kwargs)
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
        self._consumekw(kwargs, ("createdefault","length","raiseonbadlength","elementclass","elementinitkwargs"))
        if kwargs.has_key("value"):
            self._thelist=list(kwargs['value'])
            del kwargs['value']
            
        self._complainaboutunusedargs(LIST,kwargs)

        if self._elementclass is None:
            raise TypeError("elementclass argument was not supplied")
        
        if len(args):
            self.extend(args)

    def readfrombuffer(self,buffer):
        self._bufferstartoffset=buffer.getcurrentoffset()
        # delete all existing items
        while len(self):
            del self[0]
            
        if self._length is None:
            # read rest of buffer
            while buffer.hasmore():
                x=self._makeitem()
                x.readfrombuffer(buffer)
                self._thelist.append(x)
        else:
            for dummy in range(self._length):
                # read specified number of items
                x=self._makeitem()
                self._thelist.append(x)

        self._bufferendoffset=buffer.getcurrentoffset()

    def writetobuffer(self, buffer):
        self._bufferstartoffset=buffer.getcurrentoffset()

        self._ensurelength()
        for i in self:
            i.writetobuffer(buffer)

        self._bufferendoffset=buffer.getcurrentoffset()

    def packetsize(self):
        self._ensurelength()
        sz=0
        for item in self:
            sz+=item.packetsize()
        return sz

    def containerelements(self):
        self._ensurelength()
        return self._thelist.__iter__()
        

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
        return self._thelist.__getitem(index)

    def __iter__(self):
        return self._thelist.__iter__()

    def __len__(self):
        return self._thelist.__len__()

    def __setitem__(self, index, value):
        self._thelist.__setitem__(index, self._makeitem(value))

    def __delitem__(self, index):
        self._thelist.__delitem__(index)
        

    def _makeitem(self, *args, **kwargs):
        "Creates a child element"
        d={}
        d.update(self._elementinitkwargs)
        d.update(kwargs)
        return self._elementclass(*args, **d)

    def _ensurelength(self):
        "Ensures we are the correct length"
        if self._createdefault and self._length is not None and len(self)<self._length:
            while len(self)<self._length:
                x=self._makeitem()
                self._thelist.append(x)
        if self._length is not None and self._raiseonbadlength:
            raise ValueLengthException(len(self), self._length)


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

    def getnextbyte(self):
        "Returns next byte"
        res=ord(self._data[self._offset])
        self._offset+=1
        return res

    def getnextbytes(self, howmany):
        "Returns howmany bytes"
        assert howmany>=0
        res=self._data[self._offset:self._offset+howmany]
        self._offset+=howmany
        return res

    def getremainingbytes(self):
        "Returns rest of buffer"
        sz=len(self._data)-self._offset
        return self.getnextbytes(sz)

    def hasmore(self):
        "Is there any data left?"
        return self._offset<len(self._data)

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

        
    

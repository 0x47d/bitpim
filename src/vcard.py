### BITPIM
###
### Copyright (C) 2003-2004 Roger Binns <rogerb@rogerbinns.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Code for reading and writing Vcard

VCARD is defined in RFC 2425 and 2426
"""

import sys
import quopri
import base64

class VFileException(Exception):
    pass

class VFile:

    def __init__(self, source):
        self.source=source
        self.saved=None

    def __iter__(self):
        return self

    def next(self):
        # Get the next non-blank line
        while True:  # python desperately needs do-while
            line=self._getnextline()
            if line is None:
                raise StopIteration()
            if len(line)!=0:
                break

        # Hack for evolution.  If ENCODING is QUOTED-PRINTABLE then it doesn't
        # offset the next line.
        normalcontinuations=True
        colon=line.find(':')
        if colon>0:
            if "quoted-printable" in line[:colon].lower().split(";"):
                normalcontinuations=False
                while line[-1]=="=":
                    line=line[:-1]+self._getnextline()

        while normalcontinuations:
            nextline=self._lookahead()
            if nextline is None:
                break
            if len(nextline)==0:
                break
            if  nextline[0]!=' ' and nextline[0]!='\t':
                break
            line+=self._getnextline()[1:]

        colon=line.find(':')
        if colon<1:
            raise VFileException("Invalid property: "+line)

        b4=line[:colon]
        line=line[colon+1:]

        # upper case and split on semicolons
        items=b4.upper().split(";")

        # ::TODO:: vcard 3.0 requires commas and semicolons to be backslash quoted
        
        newitems=[]
        for i in items:
            # ::TODO:: probably delete anything preceding a '.'
            # (see 5.8.2 in rfc 2425)
            # unencode anything that needs it
            if not i.startswith("ENCODING=") and not i=="QUOTED-PRINTABLE": # evolution doesn't bother with "ENCODING="
                newitems.append(i)
                continue
            try:
                if i=='QUOTED-PRINTABLE' or i=="ENCODING=QUOTED-PRINTABLE":
                    line=quopri.decodestring(line)
                elif i=='ENCODING=B':
                    line=base64.decodestring(line)
                else:
                    raise VFileException("unknown encoding: "+i)
            except Exception,e:
                if isinstance(e,VFileException):
                    raise e
                raise VFileException("Exception %s while processing encoding %s on data '%s'" % (str(e), i, line))
        # ::TODO:: repeat above shenanigans looking for a VALUE= thingy and
        # convert line as in 5.8.4 of rfc 2425
        if newitems==["BEGIN"] or newitems==["END"]:
            line=line.upper()
        return newitems,line

    def _getnextline(self):
        if self.saved is not None:
            line=self.saved
            self.saved=None
            return line
        else:
            return self._readandstripline()

    def _readandstripline(self):
        line=self.source.readline()
        if line is not None:
            if len(line)==0:
                return None
            elif line[-2:]=="\r\n":
                return line[:-2]
            elif line[-1]=='\r' or line[-1]=='\n':
                return line[:-1]
        return line
    
    def _lookahead(self):
        assert self.saved is None
        self.saved=self._readandstripline()
        return self.saved
        
class VCards:
    "Understands vcards in a vfile"

    def __init__(self, vfile):
        self.vfile=vfile

    def __iter__(self):
        return self

    def next(self):
        # find vcard start
        field=value=None
        for field,value in self.vfile:
            while (field,value)!=(["BEGIN"], "VCARD"):
                continue
            found=True
            break
        if (field,value)!=(["BEGIN"], "VCARD"):
            # hit eof without any BEGIN:vcard
            raise StopIteration()
        # suck up lines
        lines=[]
        for field,value in self.vfile:
            if (field,value)!=(["END"], "VCARD"):
                lines.append( (field,value) )
                continue
            break
        if (field,value)!=(["END"], "VCARD"):
            raise VFileException("There is a BEGIN:VCARD but no END:VCARD")
        return VCard(lines)

class VCard:
    "A single vcard"

    def __init__(self, lines):
        self._version=(2,0)
        self.lines=[]
        # extract version field
        for f,v in lines:
            if f==["VERSION"]:
                ver=v.split(".")
                try:
                    ver=[int(xx) for xx in ver]
                except ValueError:
                    raise VFileException(v+" is not a valid vcard version")
                self._version=ver
                continue
            self.lines.append( (f,v) )

    def version(self):
        return self._version

    def __repr__(self):
        str="Version: %s\n" % (`self.version()`)
        str+=`self.lines`
        return str

if __name__=='__main__':

    for vcard in VCards(VFile(open(sys.argv[1]))):
        print vcard
        

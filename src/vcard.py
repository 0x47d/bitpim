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
                # ::TODO:: deal with backslashes, being especially careful with ones quoting semicolons
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
        if len(newitems)==0:
            raise VFileException("Line contains no property: %s" % (line,))
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
        self._version=(2,0)  # which version of the vcard spec the card conforms to
        self._origin=None    # which program exported the vcard
        self._data={}
        self.lines=[]
        # extract version field
        for f,v in lines:
            assert len(f)
            if f==["X-EVOLUTION-FILE-AS"]: # all evolution cards have this
                self._origin="evolution"
            if f[0].startswith("ITEM") and (f[0].endswith(".X-ABADR") or f[0].endswith(".X-ABLABEL")):
                self._origin="apple"
            if len(v) and v[0].find(">!$_") > v[0].find("_$!<") >=0:
                self.origin="apple"
            if f==["VERSION"]:
                ver=v.split(".")
                try:
                    ver=[int(xx) for xx in ver]
                except ValueError:
                    raise VFileException(v+" is not a valid vcard version")
                self._version=ver
                continue
            # convert {home,work}.{tel,label} to {tel,label};{home,work}
            # this probably dates from *very* early vcards
            if f[0]=="HOME.TEL": f[0:1]=["TEL", "HOME"]
            elif f[0]=="HOME.LABEL": f[0:1]=["LABEL", "HOME"]
            elif f[0]=="WORK.TEL": f[0:1]=["TEL", "WORK"]
            elif f[0]=="WORK.LABEL": f[0:1]=["LABEL", "WORK"]
            self.lines.append( (f,v) )
        self._parse(self.lines, self._data)

    def _getfieldname(self, name, dict):
        """Returns the fieldname to use in the dict.

        For example, if name is "email" and there is no "email" field
        in dict, then "email" is returned.  If there is already an "email"
        field then "email2" is returned, etc"""
        if name not in dict:
            return name
        for i in range(2,999999):
            if name+`i` not in dict:
                return name+`i`

    def _parse(self, lines, result):
        for field,value in lines:
            if '.' in field[0]:
                f=field[0][field[0].find('.')+1:]
            else: f=field[0]
            t=f.replace("-", "_")
            func=getattr(self, "_field_"+t, self._default_field)
            func(field, value, result)

    def _field_FN(self, field, value, result):
        result[self._getfieldname("name", result)]=self.unquote(value)

    def _default_field(self, field, value, result):
        if field[0].startswith("X-"):
            print "ignoring custom field",field
            return
        print "no idea what do with"
        print "field",field
        print "value",value

    def unquote(self, value):
        # ::TODO:: do this properly
        value=value.replace(r"\;", ";")
        value=value.replace(r"\n", "\n")
        return value


    def version(self):
        "Best guess as to vcard version"
        return self._version

    def origin(self):
        "Best guess as to what program wrote the vcard"
        return self._origin

    def __repr__(self):
        str="Version: %s\n" % (`self.version()`)
        str+="Origin: %s\n" % (`self.origin()`)
        str+=`self.lines`
        return str

if __name__=='__main__':

    for vcard in VCards(VFile(open(sys.argv[1]))):
        print vcard
        

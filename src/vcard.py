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
import common

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

    # fields we ignore

    def _field_LABEL(self, field, value, result):
        # we use the ADR field instead
        pass

    # simple fields
    
    def _field_FN(self, field, value, result):
        result[self._getfieldname("name", result)]=self.unquote(value)

    def _field_TITLE(self, field, value, result):
        result[self._getfieldname("title", result)]=self.unquote(value)
    

    #
    #  Complex fields
    # 

    def _field_N(self, field, value, result):
        value=self.splitandunquote(value)
        familyname=givenname=additionalnames=honorificprefixes=honorificsuffixes=None
        try:
            familyname=value[0]
            givenname=value[1]
            additionalnames=value[2]
            honorificprefixes=value[3]
            honorificsuffixes=value[4]
        except IndexError:
            pass
        if familyname is not None and len(familyname):
            result[self._getfieldname("last name", result)]=familyname
        if givenname is not None and len(givenname):
            result[self._getfieldname("first name", result)]=givenname
        if additionalnames is not None and len(additionalnames):
            result[self._getfieldname("middle name", result)]=additionalnames
        if honorificprefixes is not None and len(honorificprefixes):
            result[self._getfieldname("prefix", result)]=honorificprefixes
        if honorificsuffixes is not None and len(honorificsuffixes):
            result[self._getfieldname("suffix", result)]=honorificsuffixes

    def _field_ORG(self, field, value, result):
        value=self.splitandunquote(value)
        if len(value):
            result[self._getfieldname("organisation", result)]=value[0]
        for f in value[1:]:
            result[self._getfieldname("organisational unit", result)]=f

    def _field_TEL(self, field, value, result):
        value=self.unquote(value)

        # work out the types
        types=[]
        for f in field[1:]:
            if f.startswith("TYPE="):
                ff=f[len("TYPE=")+1:].split(",")
            else: ff=[f]
            types.extend(ff)

        # type munging - we map vcard types to simpler ones
        munge={ "BBS": "DATA", "MODEM": "DATA", "ISDN": "DATA", "CAR": "CELL", "PCS": "CELL" }
        types=[munge.get(t, t) for t in types]

        # types now reduced to home, work, msg, pref, voice, fax, cell, video, pager, data

        # if type is in this list and voice not explicitly mentioned then it is not a voice type
        antivoice=["FAX", "PAGER", "DATA"]
        if "VOICE" in types:
            voice=True
        else:
            voice=True # default is voice
            for f in antivoice:
                if f in types:
                    voice=False
                    break
                
        preferred="PREF" in types

        # vcard allows numbers to be multiple things at the same time, such as home voice, home fax
        # and work fax so we have to test for all variations

        # if neither work or home is specified, then no default (otherwise things get really complicated)
        iswork=False
        ishome=False
        if "WORK" in types: iswork=True
        if "HOME" in types: ishome=True

        if iswork and voice: self._setnumber(result, "work", value, preferred)
        if ishome and voice: self._setnumber(result, "home", value, preferred)
        if not iswork and not ishome and "FAX" in types:
            # fax without explicit work or home
            self._setnumber(result, "fax", value, preferred)
        else:
            if iswork and "FAX" in types: self._setnumber(result, "work fax", value, preferred)
            if ishome and "FAX" in types: self._setnumber(result, "home fax", value, preferred)
        if "CELL" in types: self._setnumber(result, "cell", value, preferred)
        if "PAGER" in types: self._setnumber(result, "pager", value, preferred)
        if "DATA" in types: self._setnumber(result, "data", value, preferred)
            

    def _setnumber(self, result, type, value, preferred):
        if type not in result:
            result[type]=value
            return
        if not preferred:
            result[self._getfieldname(type, result)]=value
            return
        # we need to insert our value at the begining
        numbers=[value]
        for suffix in ("",)+range(2,100):
            if type+str(suffix) in result:
                numbers.append(result[type+str(suffix)])
            else:
                break
        for suffix in ("",)+range(2,len(numbers)+1):
            result[type+str(suffix)]

    def _field_ADR(self, field, value, result):
        # work out the type
        preferred=False
        type="business"
        for f in field[1:]:
            if f.startswith("TYPE="):
                ff=f[len("TYPE=")+1:].split(",")
            else: ff=[f]
            for x in ff:
                if x=="HOME":
                    type="home"
                if x=="PREF":
                    preferred=True
        
        value=self.splitandunquote(value)
        pobox=extendedaddress=streetaddress=locality=region=postalcode=country=None
        try:
            pobox=value[0]
            extendedaddress=value[1]
            streetaddress=value[2]
            locality=value[3]
            region=value[4]
            postalcode=value[5]
            country=value[6]
        except IndexError:
            pass
        addr={}
        if pobox is not None and len(pobox):
            addr["pobox"]=pobox
        if extendedaddress is not None and len(extendedaddress):
            addr["street2"]=extendedaddress
        if streetaddress is not None and len(streetaddress):
            addr["street"]=streetaddress
        if locality is not None and len(locality):
            addr["city"]=locality
        if region is not None and len(region):
            addr["state"]=region
        if postalcode is not None and len(postalcode):
            addr["postalcode"]=postalcode
        if country is not None and len(country):
            addr["country"]=country
        if len(addr):
            if preferred:
                addr["preferred"]=True
            result[self._getfieldname("address", result)]=addr

    def _default_field(self, field, value, result):
        if field[0].startswith("X-"):
            print "ignoring custom field",field
            return
        print "no idea what do with"
        print "field",field
        print "value",value

    def unquote(self, value):
        # ::TODO:: do this properly (deal with all backslashes)
        value=value.replace(r"\;", ";")
        value=value.replace(r"\n", "\n")
        return value

    def splitandunquote(self, value):
        # also need a splitandsplitandunquote since some ; delimited fields are then comma delimited
        res=[]
        build=""
        v=0
        while v<len(value):
            if value[v]==";":
                res.append(build)
                build=""
                v+=1
                continue
            if value[v]=="\\":
                build+=value[v:v+2]
                v+=2
                continue
            build+=value[v]
            v+=1
        if len(build):
            res.append(build)

        return [self.unquote(v) for v in res]

    def version(self):
        "Best guess as to vcard version"
        return self._version

    def origin(self):
        "Best guess as to what program wrote the vcard"
        return self._origin

    def __repr__(self):
        str="Version: %s\n" % (`self.version()`)
        str+="Origin: %s\n" % (`self.origin()`)
        str+=common.prettyprintdict(self._data)
        str+=`self.lines`
        return str+"\n"

if __name__=='__main__':

    for vcard in VCards(VFile(open(sys.argv[1]))):
        print vcard
        

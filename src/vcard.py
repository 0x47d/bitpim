### BITPIM
###
### Copyright (C) 2003 Roger Binns <rogerb@rogerbinns.com>
###
### This software is under the Artistic license.
### http://www.opensource.org/licenses/artistic-license.php
###
### $Id$

"""Code for reading and writing Vcard

VCARD is defined in RFC 2425 and 2426
"""

import sys

class VFileException(Exception):
    pass

class VFile:

    def __init__(self, source):
        self.source=source
        self.saved=None

    def __iter__(self):
        print "iter called"
        return self

    def next(self):
        # Get the next non-blank line
        while True:  # python desperately needs do-while
            line=self._getnextline()
            if line is None:
                raise StopIteration()
            if len(line)!=0:
                break

        while True:
            nextline=self._lookahead()
            if nextline is None:
                break
            if len(nextline)==0:
                break
            if  nextline[0]!=' ':
                break
            line+=self._getnextline()[1:]

        colon=line.find(':')
        if colon<1:
            raise VFileException("Invalid property: "+line)

        b4=line[:colon]
        line=line[colon+1:]
        return b4,line

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
        


if __name__=='__main__':
    vf=VFile(open(sys.argv[1]))

    for line in vf:
        print line
        

### BITPIM
###
### Copyright (C) 2003-2006 Roger Binns <rogerb@rogerbinns.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Information about BitPim version number"""

# When a release build is made, this file is run with the 'freeze' argument.
# This file is then self modified to put only one component on the
# frozen (but inside the dollar id so svn won't consider the file modified)

__FROZEN__="$Id$"

import time

name="BitPim"
vendor=""
release=0  # when rereleases of the same version happen, this gets incremented
contact="The BitPim home page is at http://www.bitpim.org.  You can post any " \
         "questions or feedback to the mailing list detailed on that page." # where users are sent to contact with feedback

svnrevision=""  # we don't know
_headurl="$HeadURL$".split()[1]
# work out our version number
_rp="https://svn.sourceforge.com/svnroot/bitpim/releases/"
if _headurl.startswith(_rp):
    def isdevelopmentversion(): return False
    version=_headurl[len(_rp):].split("/")[0]
    if len(vendor)==0:
        vendor="official"
else:
    def isdevelopmentversion(): return True
    prefix="https://svn.sourceforge.com/svnroot/bitpim/"
    version="-".join(_headurl[len(prefix):].split("/")[:-2]) # -2 to prune off src/version.py
    del prefix
    # were we frozen?
    f=__FROZEN__.split()
    if len(f)==3: # we were - add revision
        svnrevision=f[1]
        version=version+"-"+svnrevision.replace(':', '_')
    if len(vendor)==0:
        vendor="developer build"

del _headurl
del _rp

versionstring=version

if release>0:
    versionstring+="-"+`release`

if not isdevelopmentversion():
    # dotted quad version as used on Windows (a.b.c.d where all must be digits only)
    # we use major.minor.point.last
    dqver=[int(x) for x in version.split(".")]+[0,0,0,0]
    dqver=dqver[:4]
elif len(svnrevision):
    svnrevision.split(":")
    dqver=[0,0,0,svnrevision]
else:
    dqver=[0,0,0,0]

dqverstr=".".join([`x` for x in dqver])

del x


# need to fix these ...
author="Roger Binns"
author_email="rogerb@rogerbinns.com"
url="http://www.bitpim.org"

description="BitPim "+versionstring
copyright="(C) 2003-2006 Roger Binns and others - see http://www.bitpim.org"

if __name__=='__main__':
    import sys
    if len(sys.argv)==1:
        # generated for the benefit of the help
        # purposely missing " around values
        print "#define VERSION", versionstring
        print "#define DATENOW", time.strftime("%d %B %Y")
    elif sys.argv[1]=="freeze":
        # modify the frozen field with the current revision number
        import os
        svnver=os.popen("svnversion -n .", "r").read()
        if len(svnver)<4:
            print "svnversion command doesn't appear to be working."
            sys.exit(3)
        try:
            [int(x) for x in svnver.split(":")]
        except:
            print "Your tree isn't pure. Do you have files not checked in (M)?"
            print svnver,"was returned by svnversion"
            sys.exit(4)
        print "Embedding svnrevision",svnver,"into",sys.argv[0]
        result=[]
        for line in open(sys.argv[0], "rtU"):
            if line.startswith('__FROZEN__="$Id:'):
                line='__FROZEN__="$Id$"\n'
            result.append(line)

        open(sys.argv[0], "wt").write("".join(result))
                
    else:
        print "Unknown arguments",sys.argv[1:]

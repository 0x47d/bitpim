# $Id$
# Version information

"""Information about BitPim version number"""

import time

name="BitPim"
version="0.6"
release=0  # when rereleases of the same version happen, this gets incremented
testver=4  # value of zero is non-test build
extrainfo="" # More gunk should it be test version
contact="The BitPim home page is at http://bitpim.sf.net.  You can post any " \
         "questions or feedback to the mailing list detailed on that page." # where users are sent to contact with feedback

if testver:
    # Different strings in test versions
    extrainfo="This is a test build of BitPim.  Only use it if directed by the " \
               "BitPim developers.  You can find official releases at http://bitpim.sf.net"
    contact="For questions or feedback, please use the bitpim developer mailing list.  Details " \
             "are at the BitPim web site."

versionstring=version
if testver>0:
    versionstring+="-test"+`testver`
if release>0:
    versionstring+="-"+`release`

author="Roger Binns"
author_email="rogerb@users.sourceforge.net"
url="http://bitpim.sourceforge.net"

if __name__=='__main__':
    # generated for the benefit of the help
    # purposely missing " around values
    print "#define VERSION", versionstring
    print "#define DATENOW", time.strftime("%d %B %Y")

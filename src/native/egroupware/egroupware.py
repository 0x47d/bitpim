### BITPIM
###
### Copyright (C) 2004 Roger Binns <rogerb@rogerbinns.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Be at one with eGroupware"""

import xmlrpclib
import urlparse
import time
import datetime

def getsession(url, user, password, domain="default"):

    # fixup whatever the user max have given us
    scheme, location, path, query, fragment = urlparse.urlsplit(url)

    if scheme is None and location is None and query is None:
        url="http://"+url
    
    if url[-1]!="/": url+="/"
    url+="xmlrpc.php"

    sp=xmlrpclib.ServerProxy(url)

    res=sp.system.login({"username": user, "password": password, "domain": domain})

    if "sessionid" not in res or "kp3" not in res:
        raise Exception("Invalid username or password")

    scheme, location, path, query, fragment = urlparse.urlsplit(url)

    if location.find("@")>=0:
        location=location[location.find("@")+1:]

    newurl=urlparse.urlunsplit( (scheme, "%s:%s@%s" % (res["sessionid"], res["kp3"], location), path, query, fragment) )
    return Session(xmlrpclib.ServerProxy(newurl), res)

class Session:

    def __init__(self, sp, ifo):
        self.sp=sp
        self.__ifo=ifo

    def __del__(self):
        self.sp.system.logout(self.__ifo)
        self.sp=None
        self.__ifo=None

    def getyearcalendar(self, year):
        return getcalendar((year,), (year,))

    def getcalendar(self, start=(), end=()):
        if len(start)!=6 or len(end)!=6:
            t=time.localtime()
            startdefs=(t[0], 1, 1, 0,0,0)
            enddefs=(t[0],12,31,23,59,60)
            start=start+startdefs[len(start):]
            end=end+enddefs[len(end):]
        start="%04d-%02d-%02dT%02d:%02d:%02d" % start
        end="%04d-%02d-%02dT%02d:%02d:%02d" % end
        for item in self.sp.calendar.bocalendar.search({"start": start, "end": end}):
            for k in item:
                if isinstance(item[k], xmlrpclib.DateTime):
                    v=str(item[k])
                    v=[int(x) for x in v[0:4], v[5:7], v[8:10], v[11:13], v[14:16], v[17:19]]
                    item[k]=datetime.datetime(*v)
            yield item

    def getcontacts(self):
        "returns all contacts"
        # internally we read them a group at a time
        offset=0 
        limit=5

        # NB an offset of zero causes egroupware to return ALL contacts ignoring limit!
        # This has been filed as bug 1040738 at SourceForge against eGroupware.  It
        # won't hurt unless you have huge number of contacts as egroupware will try
        # to return all of them at once.  Alternatively make the simple fix as in
        # the bug report

        while True:
            contacts=self.sp.addressbook.boaddressbook.search({'start': offset, 'limit': limit})
            if len(contacts)==0:
                raise StopIteration()
            for i in contacts:
                i=dict([(k,v) for k,v in i.items() if len(v)])
                yield i
            if len(contacts)<limit:
                raise StopIteration()
            offset+=len(contacts)
            
if __name__=='__main__':
    import sys
    s=getsession(*sys.argv[1:])
    for n,i in enumerate(s.getcontacts()):
        print n,i.get('id',""),i.get('n_given', ""),i.get('n_family', "")
    

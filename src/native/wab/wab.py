import pywabimpl

class WABException(Exception):
    def __init__(self):
        Exception.__init__(pywabimpl.cvar.errorstring)

class WAB:

    def __init__(self, enableprofiles=True, filename=None):
        if filename is None:
            filename=""
        # ::TODO:: - the filename is ignored if enableprofiles is true, so
        # exception if one is supplied
        # Double check filename exists if one is supplied since
        # the wab library doesn't actually error on non-existent file
        self._wab=pywabimpl.Initialize(enableprofiles, filename)
        if self._wab is None:
            raise WABException()
        self._wab.thisown=1

    def rootentry(self):
        return pywabimpl.entryid()

    def getpabentry(self):
        pe=self._wab.getpab()
        if pe is None:
            raise WABException()
        pe.thisown=1
        return pe

    def getrootentry(self):
        return pywabimpl.entryid()

    def openobject(self, entryid):
        x=self._wab.openobject(entryid)
        if x is None:
            raise WABException()
        x.thisown=1
        if x.gettype()==x.ABCONT:
            return Container(x)
        return x

class Table:
    def __init__(self, obj):
        self.obj=obj

    def __iter__(self):
        return self

    def next(self):
        row=self.obj.getnextrow()
        if row is None:
            raise WABException()
        row.thisown=1
        if row.IsEmpty():
            raise StopIteration()
        # we return a dict, built from row
        res={}
        for i in range(row.numproperties()):
            k=row.getpropertyname(i)
            if len(k)==0:
                continue
            v=self._convertvalue(k, row.getpropertyvalue(i))
            res[k]=v
        return res

    def count(self):
        i=self.obj.getrowcount()
        if i<0:
            raise WABException()
        return i

    def _convertvalue(self,key,v):
        x=v.find(':')
        t=v[:x]
        v=v[x+1:]
        if t=='int':
            return int(v)
        elif t=='string':
            return v
        elif t=='PT_ERROR':
            return None
        elif t=='bool':
            return bool(v)
        elif key=='PR_ENTRYID':
            v=v.split(',')
            eid=self.obj.makeentryid(int(v[0]), int(v[1]))
            eid.thisown=1
            return eid
        print "Dunno how to handle key %s type %s value %s" % (key,t,v)
        return None

class Container:
    WAB_LOCAL_CONTAINERS=pywabimpl.wabobject.FLAG_WAB_LOCAL_CONTAINERS
    WAB_PROFILE_CONTENTS=pywabimpl.wabobject.FLAG_WAB_PROFILE_CONTENTS

    def __init__(self, obj):
        self.obj=obj

    def items(self, flags=0):
        x=self.obj.getcontentstable(flags)
        if x is None:
            raise WABException()
        x.thisown=1
        return Table(x)



if __name__=='__main__':
    import sys
    fn=None
    if len(sys.argv)>1:
        fn=sys.argv[1]
    wab=WAB(False, fn)
    root=wab.openobject(wab.getrootentry())
    items=root.items()
    print items.count(), "items in root"
    for i in items:
        print i
    
    
    

import pywabimpl

class WABException(Exception):
    def __init__(self):
        Exception.__init__(pywabimpl.cvar.errorstring)

constants=pywabimpl.constants

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

    def rootentry(self):
        return pywabimpl.entryid()

    def getpabentry(self):
        pe=self._wab.getpab()
        if pe is None:
            raise WABException()
        return pe

    def getrootentry(self):
        return pywabimpl.entryid()

    def openobject(self, entryid):
        x=self._wab.openobject(entryid)
        if x is None:
            raise WABException()
        if x.gettype()==constants.MAPI_ABCONT:
            return Container(x)
        return x

class Table:
    def __init__(self, obj):
        self.obj=obj

    def __iter__(self):
        return self

    def enableallcolumns(self):
        if not self.obj.enableallcolumns():
            raise WABException()

    def next(self):
        row=self.obj.getnextrow()
        if row is None:
            raise WABException()
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
            return self.obj.makeentryid(int(v[0]), int(v[1]))
        elif t=='binary':
            v=v.split(',')
            return self.obj.makebinarystring(int(v[0]), int(v[1]))
        print "Dunno how to handle key %s type %s value %s" % (key,t,v)
        return None

class Container:

    def __init__(self, obj):
        self.obj=obj

    def items(self, flags=0):
        """Returns items in the container

        @param flags: WAB_LOCAL_CONTAINERS,WAB_PROFILE_CONTENTS
        """
        x=self.obj.getcontentstable(flags)
        if x is None:
            raise WABException()
        return Table(x)



if __name__=='__main__':
    import sys
    fn=None
    if len(sys.argv)>1:
        fn=sys.argv[1]
        wab=WAB(False, fn)
    else:
        wab=WAB()
    root=wab.openobject(wab.getrootentry())
    for container in root.items(constants.WAB_LOCAL_CONTAINERS|constants.WAB_PROFILE_CONTENTS):
        print container['PR_DISPLAY_NAME']
        people=wab.openobject(container['PR_ENTRYID'])
        items=people.items()
        items.enableallcolumns()
        for i in items:
            print i
            pass
        

    
    
    

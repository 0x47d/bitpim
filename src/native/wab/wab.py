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

class Container:

    def __init__(self, obj):
        self.obj=obj



if __name__=='__main__':
    import sys
    fn=None
    if len(sys.argv)>1:
        fn=sys.argv[1]
    wab=WAB(False, fn)
    root=wab.openobject(wab.getrootentry())
    print root
    print root.gettype()
    print dir(root)
    

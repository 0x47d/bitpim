#!/usr/bin/env python

### BITPIM
###
### Copyright (C) 2003 Roger Binns <rogerb@rogerbinns.com>
###
### This software is under the Artistic license.
### http://www.opensource.org/licenses/artistic-license.php
###
### $Id$

"""Graphical view of protocol data and a decode of it"""

import sys
import re
from wxPython.wx import *

import common
import prototypes

import p_lgvx4400

class Eventlist(wxListCtrl):

    def __init__(self, parent, id=-1, events=[]):
        self.events=events
        wxListCtrl.__init__(self, parent, id, style=wxLC_REPORT|wxLC_VIRTUAL)
        self.InsertColumn(0, "Time")
        self.InsertColumn(1, "Size")
        self.InsertColumn(2, "Class")
        self.InsertColumn(3, "Description")

        self.SetColumnWidth(0, 100)
        self.SetColumnWidth(1, 50)
        self.SetColumnWidth(2, 200)
        self.SetColumnWidth(3, 1000)

        self.SetItemCount(len(events))

    def newdata(self, events):
        self.DeleteAllItems()
        self.events=events
        self.SetItemCount(len(events))

    def OnGetItemText(self, index, col):
        curtime, curdesc, curclass, curdata=self.events[index]
        if col==0:
            return curtime
        if col==1:
            if len(curdata):
                return "%5d" % (len(curdata),)
            return ""
        if col==2:
            return curclass
        if col==3:
            return curdesc
        assert False

    def OnGetItemImage(self, item):
        return -1
        
    

class Analyser(wxFrame):
    """A top level frame for analysing protocol data"""

    def __init__(self, parent=None, id=-1, title="BitPim Protocol Analyser", data=None):
        """Start the show

        @param data: data to show.  If None, then it will be obtained from the clipboard
        """
        wxFrame.__init__(self, parent, id, title, size=(800,650),
                         style=wxDEFAULT_FRAME_STYLE|wxNO_FULL_REPAINT_ON_RESIZE)


        topsplit=wxSplitterWindow(self, -1, style=wxSP_3D|wxSP_LIVE_UPDATE)

        self.list=Eventlist(topsplit, 12)

        botsplit=wxSplitterWindow(topsplit, -1, style=wxSP_3D|wxSP_LIVE_UPDATE)
        topsplit.SplitHorizontally(self.list, botsplit, 300)

        self.tree=wxTreeCtrl(botsplit, 23, style=wxTR_DEFAULT_STYLE)
        self.hex=wxTextCtrl(botsplit, -1, style=wxTE_MULTILINE| wxTE_RICH2|wxNO_FULL_REPAINT_ON_RESIZE|wxTE_DONTWRAP|wxTE_READONLY)
        # Fixed width font
        f=wxFont(10, wxMODERN, wxNORMAL, wxNORMAL )
        ta=wxTextAttr(font=f)
        self.hex.SetDefaultStyle(ta)

        botsplit.SplitHorizontally(self.tree, self.hex, 200)
        
        if data is None:
            data=self.getclipboarddata()

        self.parsedata(data)
        self.list.newdata(self.packets)

        EVT_LIST_ITEM_SELECTED(self, self.list.GetId(), self.OnListBoxItem)
        EVT_LIST_ITEM_ACTIVATED(self, self.list.GetId(), self.OnListBoxItem)
        
        self.Show()

    def OnListBoxItem(self,evt):
        index=evt.m_itemIndex
        curtime, curdesc, curclass, curdata=self.packets[index]
        self.hex.Clear()
        if len(curdata):
            self.hex.AppendText(common.datatohexstring(curdata))
            self.hex.SetInsertionPoint(0)
            self.hex.ShowPosition(self.hex.XYToPosition(0,0))
        self.tree.DeleteAllItems()
        if len(curclass):
            b=prototypes.buffer(curdata)
            try:
                klass=eval(curclass)
            except Exception,e:
                self.errorme("Finding class",e)
                return
            try:
                obj=klass()
            except Exception,e:
                self.errorme("Instantiating object",e)
                return

            try:
                obj.readfrombuffer(b)
            except Exception,e:
                self.errorme("Reading from buffer",e)
                # no return, we persevere

            root=self.tree.AddRoot(curclass)
            try:
                self.tree.SetPyData(root, obj.packetspan())
            except Exception,e:
                self.errorme("Root item has no span!",e)
            self.addtreeitems(obj, root)

    def addtreeitems(self, obj, parent):
        for name,field,desc in obj.containerelements():
            if desc is None:
                desc=""
            else:
                desc=" - "+desc
            iscontainer=False
            try:
                iscontainer=field.iscontainer()
            except:
                pass
            # Add ourselves
            s=field.__class__.__name__+" "+name
            if iscontainer:
                c=field.__class__
                s+=": <%s.%s>" % (c.__module__, c.__name__)
            else:
                v=field.getvalue()
                s+=": "+`v`
            node=self.tree.AppendItem(parent, s)
            try:
                self.tree.SetPyData(node, field.packetspan())
            except:
                pass
            if iscontainer:
                self.addtreeitems(field, node)


    def errorme(self, desc, exception=None):
        if exception is not None:
            self.hex.WriteText(exception.str()+" while ")
        self.hex.WriteText(desc+"\n")

    def getclipboarddata(self):
        """Gets text data on clipboard"""
        do=wxTextDataObject()
        wxTheClipboard.Open()
        success=wxTheClipboard.GetData(do)
        wxTheClipboard.Close()
        if not success:
            wxMessageBox("Whatever is in the clipboard isn't text", "No way Dude")
            return ""
        return do.GetText()

    patevent=re.compile(r"^(\d\d:\d\d:\d\d\.\d\d\d)(.*)")
    patdataevent=re.compile(r"^(\d\d:\d\d:\d\d\.\d\d\d)(.*)Data - \d+ bytes.*")
    patdatarow=re.compile(r"^([0-9A-Fa-f]{8})(.*)")
    patclass=re.compile(r"^<#!\s+(.*)\s+!#>")

    def parsedata(self, data):
        """Fills in our internal data structures based on contents of data"""

        # santise all the data by doing the eol nonsense
        data=data.replace("\r", "\n")
        lastlen=0
        while lastlen!=len(data):
            lastlen=len(data)
            data=data.replace("\n\n", "\n")
        
        self.packets=[]

        curtime=curdesc=curclass=curdata=""

        indata=False
        
        for line in data.split('\n'):
            # ignore blank lines
            if len(line.strip())==0:
                continue
            mo=self.patclass.match(line)
            if mo is not None:
                # found a class description
                curclass=mo.group(1)
                indata=True
                continue
            # if indata, try for some more
            if indata:
                mo=self.patdatarow.match(line)
                if mo is not None:
                    # found another data row
                    pos=int(mo.group(1), 16)
                    assert pos==len(curdata)
                    for i in range(9, min(len(line), 9+16*3), 3): # at most 16 bytes
                        s=line[i:i+2]
                        if s=="  ":
                            # last line with trailing spaces
                            continue
                        b=int(s,16)
                        curdata+=chr(b)
                    continue
                # end of data, save it
                indata=False
                self.packets.append( (curtime, curdesc, curclass, curdata) )
                curtime=curdesc=curclass=curdata=""
                # and move on
            # data event?
            mo=self.patdataevent.match(line)
            if mo is not None:
                self.packets.append( (curtime, curdesc, curclass, curdata) )
                curtime=curdesc=curclass=curdata=""
                curtime=mo.group(1)
                curdesc=mo.group(2)
                indata=True
                continue
            # ordinary event?
            mo=self.patevent.match(line)
            if mo is not None:
                self.packets.append( (curtime, curdesc, curclass, curdata) )
                curtime=curdesc=curclass=curdata=""
                curtime=mo.group(1)
                curdesc=mo.group(2)
                indata=True
                continue
            # No idea what it is, just add on end of desc
            if len(curdesc):
                curdesc+="\n"
            curdesc+=line

        # Add whatever is in variables at end
        self.packets.append( (curtime, curdesc, curclass, curdata) )

        # remove all blank lines
        # filter, reduce, map and lambda all in one go!
        self.packets=filter(lambda item: reduce(lambda x,y: x+y, map(len, item)), self.packets)
                    



if __name__=='__main__':
    app=wxPySimpleApp()
    # Find the data source
    data=None
    if len(sys.argv)==2:
        # From a file
        f=open(sys.argv[1], "r")
        data=f.read()
        f.close()
    frame=Analyser(data=data)
    app.MainLoop()

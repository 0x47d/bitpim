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
import traceback
import wx
import StringIO

import common
import prototypes

import p_lg
import p_lgvx4400
import p_brew
import p_lgtm520

class Eventlist(wx.ListCtrl):
    "List control showing the various events"

    def __init__(self, parent, id=-1, events=[]):
        self.events=events
        wx.ListCtrl.__init__(self, parent, id, style=wx.LC_REPORT|wx.LC_VIRTUAL)
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
        
    

class Analyser(wx.Frame):
    """A top level frame for analysing protocol data"""

    def __init__(self, parent=None, id=-1, title="BitPim Protocol Analyser", data=None):
        """Start the show

        @param data: data to show.  If None, then it will be obtained from the clipboard
        """
        wx.Frame.__init__(self, parent, id, title, size=(800,750),
                         style=wx.DEFAULT_FRAME_STYLE|wx.NO_FULL_REPAINT_ON_RESIZE)


        topsplit=wx.SplitterWindow(self, -1, style=wx.SP_3D|wx.SP_LIVE_UPDATE)

        self.list=Eventlist(topsplit, 12)

        botsplit=wx.SplitterWindow(topsplit, -1, style=wx.SP_3D|wx.SP_LIVE_UPDATE)
        topsplit.SplitHorizontally(self.list, botsplit, 300)

        self.tree=wx.TreeCtrl(botsplit, 23, style=wx.TR_DEFAULT_STYLE)
        self.hex=wx.TextCtrl(botsplit, -1, style=wx.TE_MULTILINE| wx.TE_RICH2|wx.NO_FULL_REPAINT_ON_RESIZE|wx.TE_DONTWRAP|wx.TE_READONLY)
        # Fixed width font
        f=wx.Font(10, wx.MODERN, wx.NORMAL, wx.NORMAL )
        ta=wx.TextAttr(font=f)
        self.hex.SetDefaultStyle(ta)

        self.highlightstyle=wx.TextAttr(font=f, colBack=wx.Colour(0xff,0xff,0))
        self.errorstyle=wx.TextAttr(font=f, colBack=wx.Colour(0xff,64,64))
        self.dataline=0

        botsplit.SplitHorizontally(self.tree, self.hex, 200)
        
        if data is None:
            data=self.getclipboarddata()

        self.newdata(data)

        wx.EVT_LIST_ITEM_SELECTED(self, self.list.GetId(), self.OnListBoxItem)
        wx.EVT_LIST_ITEM_ACTIVATED(self, self.list.GetId(), self.OnListBoxItem)

        wx.EVT_TREE_SEL_CHANGED(self, self.tree.GetId(), self.OnTreeSelection)
        
        self.Show()

    def newdata(self, data):
        "We have new data - the old data is tossed"
        self.parsedata(data)
        self.list.newdata(self.packets)

    def OnListBoxItem(self,evt):
        "The user selected an event in the listbox"
        index=evt.m_itemIndex
        curtime, curdesc, curclass, curdata=self.packets[index]
        self.hex.Clear()
        self.dataline=0
        if len(curdata):
            self.hex.AppendText(common.datatohexstring(curdata))
            self.hex.SetInsertionPoint(0)
            self.hex.ShowPosition(self.hex.XYToPosition(0,0))
        else:
            self.hex.AppendText(curdesc)
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
            except:
                self.errorme("Object did not construct correctly")
                # no return, we persevere
            self.addtreeitems(obj, root)

    def addtreeitems(self, obj, parent):
        "Add fields from obj to parent node"
        try:
            for name,field,desc in obj.containerelements():
                if desc is None:
                    desc=""
                else:
                    desc="      - "+desc
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
                    try:
                        v=field.getvalue()
                    except Exception,e:
                        v="<Exception: "+e.__str__()+">"
                    s+=": "
                    if isinstance(v, int) and not isinstance(v, bool):
                        s+="%d 0x%x" % (v,v)
                    else:
                        s+=`v`
                    if len(desc):
                        s+=desc
                node=self.tree.AppendItem(parent, s)
                try:
                    self.tree.SetPyData(node, field.packetspan())
                except:
                    pass
                if iscontainer:
                    self.addtreeitems(field, node)
        except Exception,e:
            str="<Exception: "+e.__str__()+">"
            self.tree.AppendItem(parent,str)

    def OnTreeSelection(self, evt):
        "User selected an item in the tree"
        item=evt.GetItem()
        begin=self.hex.XYToPosition(0, self.dataline)
        self.hex.SetStyle(begin,self.hex.GetLastPosition(),self.hex.GetDefaultStyle())
        try:
            start,end=self.tree.GetPyData(item)
        except:
            return
        begin=self.hex.XYToPosition(0, self.dataline+start/16)
        self.hex.ShowPosition(begin)
        self.hex.Freeze()
        for offset in range(start,end):
            fudge=0
            
            # figure out hex bytes and char for this offset
            line=self.hex.XYToPosition(0,self.dataline+offset/16)
            if offset+1==end or (offset%16)==15:
                fudge=-1
            offset%=16
            self.hex.SetStyle(line+9+offset*3, line+9+offset*3+3+fudge, self.highlightstyle)
            # and now the char
            self.hex.SetStyle(line+61+offset,  line+61+offset+1, self.highlightstyle)
        self.hex.Thaw()

    def errorme(self, desc, exception=None):
        "Put exception information into the hex pane and output traceback to console"
        if exception is not None:
            x=StringIO.StringIO()
            print >>x,exception.__str__(),
            self.hex.WriteText(x.getvalue()+" : ")
            print >>sys.stderr, common.formatexception()
        self.hex.WriteText(desc+"\n")
        for i,l in zip(range(10000), self.hex.GetValue().split("\n")):
            if len(l)>8 and l[:8]=='00000000':
                self.dataline=i
                self.hex.SetStyle(0, self.hex.XYToPosition(0, self.dataline), self.errorstyle)
                return

    def getclipboarddata(self):
        """Gets text data on clipboard"""
        do=wx.TextDataObject()
        wx.TheClipboard.Open()
        success=wx.TheClipboard.GetData(do)
        wx.TheClipboard.Close()
        if not success:
            wx.MessageBox("Whatever is in the clipboard isn't text", "No way Dude")
            return ""
        return do.GetText()

    patevent=re.compile(r"^(\d?\d:\d\d:\d\d\.\d\d\d)(.*)")
    patdataevent=re.compile(r"^(\d?\d:\d\d:\d\d\.\d\d\d)(.*)(Data - \d+ bytes.*)")
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
                        if len(s)!=2 or s=="  ":
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
                curdesc=mo.group(2)+mo.group(3)
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
    app=wx.PySimpleApp()
    # Find the data source
    data=None
    if len(sys.argv)==2:
        # From a file
        f=open(sys.argv[1], "r")
        data=f.read()
        f.close()
    frame=Analyser(data=data)
    app.MainLoop()

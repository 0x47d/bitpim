### BITPIM
###
### Copyright (C) 2003 Roger Binns <rogerb@rogerbinns.com>
###
### This software is under the Artistic license.
### Please see the accompanying LICENSE file
###
### $Id$

"""A widget for displaying/editting the phone information

The format for a phonebook entry is standardised.  It is a
dict with the following fields.  Each field is a list, most
important first, with each item in the list being a dict.

names:

   - title      ??Job title or salutation??
   - first
   - middle
   - last
   - full       You should specify the fullname or the 4 above
   - nickname   

categories:

  - category    User defined category name

emails:

  - email       Email address
  - type        (optional) 'home' or 'business'

urls:

  - url         URL
  - type        (optional) 'home' or 'business'

ringtones:

  - ringtone    Name of a ringtone
  - use         'call', 'message'

addresses:

  - type        'home' or 'business'
  - company     (only for type of 'business')
  - street      Street part of address
  - street2     Second line of street address
  - city
  - state
  - postalcode
  - country     Can also be the region

wallpapers:

  - wallpaper   Name of wallpaper
  - index       Index number of the wallpaper (fill out one of these two, not both)
  - use         see ringtones.use

flags:

  - secret     Boolean if record is private/secret

memos:

  - memo       Note

numbers:

  - number     Phone number as ascii string
  - type       'home', 'office', 'cell', 'fax', 'pager', 'data', 'none'  (if you have home2 etc, list
               them without the digits.  The second 'home' is implicitly home2 etc)
  - speeddial  (optional) Speed dial number

serials:

  - sourcetype        identifies source driver in bitpim (eg "lgvx4400", "windowsaddressbook")
  - sourceuniqueid    identifier for where the serial came from (eg ESN of phone, wab host/username)
  - *                 other names of use to sourcetype
"""

# Standard imports
import os
import cStringIO
import webbrowser
import difflib
import re
import time

# GUI
import wx
import wx.grid
import wx.html

# My imports
import common
import xyaptu
import guihelper
import phonebookentryeditor
import pubsub

###
###  Enhanced HTML Widget
###

class HTMLWindow(wx.html.HtmlWindow):
    """BitPim customised HTML Window

    Some extras on this:
    
       - You can press Ctrl-Alt-S to get a source view
       - Clicking on a link opens a window in your browser
       - Shift-clicking on a link copies it to the clipboard
    """
    def __init__(self, parent, id, relsize=0.7):
        # default sizes on windows
        basefonts=[7,8,10,12,16,22,30]
        # defaults on linux
        if guihelper.IsGtk():
            basefonts=[10,13,17,20,23,27,30]
        wx.html.HtmlWindow.__init__(self, parent, id)
        wx.EVT_KEY_UP(self, self.OnKeyUp)
        self.thetext=""
        if relsize!=1:
            self.SetFonts("", "", [int(sz*relsize) for sz in basefonts])

    def OnLinkClicked(self, event):
        # see ClickableHtmlWindow in wxPython source for inspiration
        # :::TODO::: redirect bitpim images and audio to correct
        # player
        if event.GetEvent().ShiftDown():
            wx.TheClipboard.Open()
            wx.TheClipboard.SetData(event.GetHref())
            wx.TheClipboard.Close()
        else:
            webbrowser.open(event.GetHref())

    def SetPage(self, text):
        self.thetext=text
        wx.html.HtmlWindow.SetPage(self,text)

    def OnKeyUp(self, evt):
        keycode=evt.GetKeyCode()        
        if keycode==ord('S') and evt.ControlDown() and evt.AltDown():
            vs=ViewSourceFrame(None, self.thetext)
            vs.Show(True)
            evt.Skip()

###
###  View Source Window
###            

class ViewSourceFrame(wx.Frame):
    def __init__(self, parent, text, id=-1):
        wx.Frame.__init__(self, parent, id, "HTML Source")
        stc=wx.TextCtrl(self, -1, "", style=wx.TE_MULTILINE)
        stc.AppendText(text)


###
### Phonebook entry display (Derived from HTML)
###

class PhoneEntryDetailsView(HTMLWindow):

    def __init__(self, parent, id, stylesfile, layoutfile):
        HTMLWindow.__init__(self, parent, id)
        self.stylesfile=guihelper.getresourcefile(stylesfile)
        self.stylesfilestat=None
        self.pblayoutfile=guihelper.getresourcefile(layoutfile)
        self.pblayoutfilestat=None
        self.xcp=None
        self.xcpstyles=None
        self.ShowEntry({})

    def ShowEntry(self, entry):
        if self.xcp is None or self.pblayoutfilestat!=os.stat(self.pblayoutfile):
            f=open(self.pblayoutfile, "rt")
            template=f.read()
            f.close()
            self.pblayoutfilestat=os.stat(self.pblayoutfile)
            self.xcp=xyaptu.xcopier(None)
            self.xcp.setupxcopy(template)
        if self.xcpstyles is None or self.stylesfilestat!=os.stat(self.stylesfile):
            self.xcpstyles={}
            execfile(self.stylesfile,  self.xcpstyles, self.xcpstyles)
            self.stylesfilestat=os.stat(self.stylesfile)
        self.xcpstyles['entry']=entry
        text=self.xcp.xcopywithdns(self.xcpstyles)
        self.SetPage(text)

###
### Functions used to get data from a record
###

def getdata(column, entry, default=None):
    if column=="Name":
        names=entry.get("names", [{}])
        name=names[0]
        x=formatname(name)
        if len(x)==0:
            return default
        return x

    if column=="Home":
        for number in entry.get("numbers", []):
            if number.get("type", "")=="home":
                return number['number']
        return default

    if column=="Email":
        for email in entry.get("emails", []):
            return email['email']
        return default

    assert False, "Unknown column type "+column
    return default


def formatname(name):
    # Returns a string of the name in name.
    # Since there can be many fields, we try to make sense of them
    res=""
    full=name.get("full", "")
    fml=""

    f=name.get("first", "")
    m=name.get("middle", "")
    l=name.get("last", "")
    if len(f) or len(m) or len(l):
        fml+=f
        if len(m) and len(fml) and fml[-1]!=' ':
            fml+=" "
        fml+=m
        if len(l) and len(fml) and fml[-1]!=' ':
            fml+=" "
        fml+=l

    if len(fml) or len(full):
        # are they the same
        if fml==full:
            res+=full
        else:
            # different
            if len(full):
                res+=full
            if len(fml):
                if len(res):
                    res+=" | "
                res+=fml

    if name.has_key("nickname"):
        res+=" ("+name["nickname"]+")"
    return res

def formatsimplename(name):
    # like formatname, except we use the first matching component
    if len(name.get("full", "")):
        return name.get("full")
    f=name.get("first", "")
    m=name.get("middle", "")
    l=name.get("last", "")
    if len(f) or len(m) or len(l):
        res=""
        if len(f):
            res+=f
        if len(m):
            if len(res) and res[-1]!=" ":
                res+=" "
            res+=m
        if len(l):
            if len(res) and res[-1]!=" ":
                res+=" "
            res+=l
        return res
    return name['nickname']

        
class CategoryManager:

    # this is only used to prevent the pubsub module
    # from being GC while any instance of this class exists
    __publisher=pubsub.Publisher

    def __init__(self):
        self.categories=[]
        pubsub.subscribe(pubsub.REQUEST_CATEGORIES, self, "OnListRequest")
        pubsub.subscribe(pubsub.SET_CATEGORIES, self, "OnSetCategories")
        pubsub.subscribe(pubsub.MERGE_CATEGORIES, self, "OnMergeCategories")
        pubsub.subscribe(pubsub.ADD_CATEGORY, self, "OnAddCategory")

    def OnListRequest(self, msg=None):
        print "publish all categories", self.categories
        # nb we publish a copy of the list, not the real
        # thing.  otherwise other code inadvertently modifies it!
        pubsub.publish(pubsub.ALL_CATEGORIES, self.categories[:])

    def OnAddCategory(self, msg):
        name=msg.data
        if name in self.categories:
            return
        self.categories.append(name)
        self.categories.sort()
        self.OnListRequest()

    def OnSetCategories(self, msg):
        cats=msg.data[:]
        self.categories=cats
        self.categories.sort()
        self.OnListRequest()

    def OnMergeCategories(self, msg):
        cats=msg.data[:]
        newcats=self.categories[:]
        for i in cats:
            if i not in newcats:
                newcats.append(i)
        newcats.sort()
        if newcats!=self.categories:
            self.categories=newcats
            self.OnListRequest()

CategoryManager=CategoryManager() # shadow out class name

###
### We use a table for speed
###

class PhoneDataTable(wx.grid.PyGridTableBase):

    def __init__(self, widget):
        self.main=widget
        self.rowkeys=self.main._data.keys()
        self.rowkeys.sort()
        wx.grid.PyGridTableBase.__init__(self)
        self.oddattr=wx.grid.GridCellAttr()
        self.oddattr.SetBackgroundColour("OLDLACE")
        self.evenattr=wx.grid.GridCellAttr()
        self.evenattr.SetBackgroundColour("ALICE BLUE")
        self.columns=['Name', 'Home', 'Email']

    def GetColLabelValue(self, col):
        return self.columns[col]

    def OnDataUpdated(self):
        newkeys=self.main._data.keys()
        newkeys.sort()
        oldrows=self.rowkeys
        self.rowkeys=newkeys
        lo=len(oldrows)
        ln=len(self.rowkeys)
        if ln>lo:
            msg=wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED, ln-lo)
        elif lo>ln:
            msg=wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_NOTIFY_ROWS_DELETED, 0, lo-ln)
        else:
            msg=None
        if msg is not None:
            self.GetView().ProcessTableMessage(msg)
        msg=wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_REQUEST_VIEW_GET_VALUES)
        self.GetView().AutoSizeColumns()


    def IsEmptyCell(self, row, col):
        return False

    def GetNumberRows(self):
        return len(self.rowkeys)

    def GetNumberCols(self):
        return len(self.columns)

    def GetValue(self, row, col):
        try:
            entry=self.main._data[self.rowkeys[row]]
        except:
            print "bad row", row
            return "<error>"

        return getdata(self.columns[col], entry, "")

    def GetAttr(self, row, col, _):
        r=[self.evenattr, self.oddattr][row%2]
        r.IncRef()
        return r

class PhoneWidget(wx.Panel):
    """Main phone editing/displaying widget"""
    CURRENTFILEVERSION=2
    def __init__(self, mainwindow, parent):
        wx.Panel.__init__(self, parent,-1)
        # keep this around while we exist
        self.categorymanager=CategoryManager
        self.SetBackgroundColour("ORANGE")
        split=wx.SplitterWindow(self, -1, style=wx.SP_3D|wx.SP_LIVE_UPDATE)
        self.mainwindow=mainwindow
        self._data={}
        self.categories=[]
        self.modified=False
        self.table=wx.grid.Grid(split, wx.NewId())
        self.table.EnableGridLines(False)
        self.dt=PhoneDataTable(self)
        self.table.SetTable(self.dt, False, wx.grid.Grid.wxGridSelectRows)
        self.table.SetSelectionMode(wx.grid.Grid.wxGridSelectRows)
        self.table.SetRowLabelSize(0)
        self.table.EnableEditing(False)
        self.table.EnableDragRowSize(False)
        self.table.SetMargins(1,0)
        self.preview=PhoneEntryDetailsView(split, -1, "styles.xy", "pblayout.xy")
        # for some reason, preview doesn't show initial background
        wx.CallAfter(self.preview.ShowEntry, {})
        split.SplitVertically(self.table, self.preview, -300)
        self.split=split
        bs=wx.BoxSizer(wx.VERTICAL)
        bs.Add(split, 1, wx.EXPAND)
        self.SetSizer(bs)
        self.SetAutoLayout(True)
        wx.EVT_IDLE(self, self.OnIdle)
        wx.grid.EVT_GRID_SELECT_CELL(self, self.OnCellSelect)
        wx.grid.EVT_GRID_CELL_LEFT_DCLICK(self, self.OnCellDClick)
        pubsub.subscribe(pubsub.ALL_CATEGORIES, self, "OnCategoriesUpdate")


    def OnCategoriesUpdate(self, msg):
        if self.categories!=msg.data:
            print "categories updated"
            self.categories=msg.data[:]
            self.modified=True

    def OnIdle(self, _):
        "We save out changed data"
        if self.modified:
            print "Saving phonebook"
            self.modified=False
            self.populatefs(self.getdata({}))

    def OnCellSelect(self, event):
        event.Skip()
        row=event.GetRow()
        self.SetPreview(self._data[self.dt.rowkeys[row]]) # bad breaking of abstraction referencing dt!

    def OnCellDClick(self, event):
        row=event.GetRow()
        key=self.dt.rowkeys[row]
        data=self._data[key]
        dlg=phonebookentryeditor.Editor(self, data)
        if dlg.ShowModal()==wx.ID_OK:
            data=dlg.GetData()
            self._data[key]=data
            self.dt.OnDataUpdated()
            self.SetPreview(data)
            self.modified=True
        dlg.Destroy()

    def OnAdd(self, _):
        dlg=phonebookentryeditor.Editor(self, {'names': [{'full': 'New Entry'}]})
        if dlg.ShowModal()==wx.ID_OK:
            data=dlg.GetData()
            while True:
                key=int(time.time())
                if key in self._data:
                    continue
                break
            self._data[key]=data
            self.dt.OnDataUpdated()
            self.SetPreview(data)
            self.modified=True
        dlg.Destroy()

    def OnDelete(self,_):
        rows=[]
        gcr=self.table.GetGridCursorRow()
        set1=self.table.GetSelectionBlockTopLeft()
        set2=self.table.GetSelectionBlockBottomRight()
        if len(set1):
            assert len(set1)==len(set2)
            for i in range(len(set1)):
                for row in range(set1[i][0], set2[i][0]+1): # range in wx is inclusive of last element
                    if row not in rows:
                        rows.append(row)
        else:
            rows.append(gcr)

        self.table.ClearSelection()
        rowkeys=[]
        for r in rows:
            rowkeys.append(self.dt.rowkeys[r])
        for r in rowkeys:
            del self._data[r]
        self.dt.OnDataUpdated()
        self.modified=True

    def SetPreview(self, entry):
        self.preview.ShowEntry(entry)

    def getdata(self, dict):
        dict['phonebook']=self._data.copy()
        dict['categories']=self.categories[:]
        return dict


    def versionupgrade(self, dict, version):
        """Upgrade old data format read from disk

        @param dict:  The dict that was read in
        @param version: version number of the data on disk
        """

        # version 0 to 1 upgrade
        if version==0:
            version=1  # they are the same

        # 1 to 2 etc
        if version==1:
            wx.MessageBox("BitPim can't upgrade your old phone data stored on disk, and has discarded it.  Please re-read your phonebook from the phone.  If you downgrade, please delete the phonebook directory in the BitPim data directory first", "Phonebook file format not supported", wx.OK|wx.ICON_EXCLAMATION)
            version=2
            dict['phonebook']={}
            dict['categories']=[]
            
    def clear(self):
        self._data={}
        self.dt.OnDataUpdated()

    def getfromfs(self, dict):
        self.thedir=self.mainwindow.phonebookpath
        try:
            os.makedirs(self.thedir)
        except:
            pass
        if not os.path.isdir(self.thedir):
            raise Exception("Bad directory for phonebook '"+self.thedir+"'")
        if os.path.exists(os.path.join(self.thedir, "index.idx")):
            d={'result': {}}
            common.readversionedindexfile(os.path.join(self.thedir, "index.idx"), d, self.versionupgrade, self.CURRENTFILEVERSION)
            dict.update(d['result'])
        else:
            dict['phonebook']={}
            dict['categories']=[]
        return dict

    def populate(self, dict):
        self.clear()
        pubsub.publish(pubsub.MERGE_CATEGORIES, dict.get('categories', []))
        pb=dict['phonebook']
        cats=[]
        for i in pb:
            for cat in pb[i].get('categories', []):
                cats.append(cat['category'])
        pubsub.publish(pubsub.MERGE_CATEGORIES, cats)                
        k=pb.keys()
        k.sort()
        self.clear()
        self._data=pb.copy()
        self.dt.OnDataUpdated()
        self.modified=True

    def populatefs(self, dict):
        self.thedir=self.mainwindow.phonebookpath
        try:
            os.makedirs(self.thedir)
        except:
            pass
        if not os.path.isdir(self.thedir):
            raise Exception("Bad directory for phonebook '"+self.thedir+"'")
        for f in os.listdir(self.thedir):
            # delete them all!
            os.remove(os.path.join(self.thedir, f))
        d={}
        d['phonebook']=dict['phonebook']
        if len(dict.get('categories', [])):
            d['categories']=dict['categories']
        
        common.writeversionindexfile(os.path.join(self.thedir, "index.idx"), d, self.CURRENTFILEVERSION)
        return dict
    
    def converttophone(self, data):
        self.mainwindow.phoneprofile.convertphonebooktophone(self, data)


    class ConversionFailed(Exception):
        pass

    def _getentries(self, list, min, max, name):
        candidates=[]
        for i in list:
            # ::TODO:: possibly ensure that a key appears in each i
            candidates.append(i)
        if len(candidates)<min:
            # ::TODO:: log this
            raise ConversionFailed("Too few %s.  Need at least %d but there were only %d" % (name,min,len(candidates)))
        if len(candidates)>max:
            # ::TODO:: mention this to user
            candidates=candidates[:max]
        return candidates

    def _getfield(self,list,name):
        res=[]
        for i in list:
            res.append(i[name])
        return res

    def _truncatefields(self, list, truncateat):
        if truncateat is None:
            return list
        res=[]
        for i in list:
            if len(i)>truncateat:
                # ::TODO:: log truncation
                res.append(i[:truncateat])
            else:
                res.append(i)
        return res

    def _findfirst(self, candidates, required, key, default):
        """Find first match in candidates that meets required and return value of key

        @param candidates: list of dictionaries to search through
        @param required: a dict of what key/value pairs must exist in an entry
        @param key: for a matching entry, which key's value to return
        @param default: what value to return if there is no match
        """
        for dict in candidates:
            ok=True
            for k in required:
                if dict[k]!=required[k]:
                   ok=False
                   break # really want break 2
            if not ok:
                continue
            return dict[key]
        return default

    def getfullname(self, names, min, max, truncateat=None):
        "Return at least min and at most max fullnames from the names list"
        # ::TODO:: possibly deal with some names having the fields, and some having full
        return self._truncatefields(self._getfield(self._getentries(names, min, max, "names"), "full"), truncateat)

    def getcategory(self, categories, min, max, truncateat=None):
        "Return at least min and at most max categories from the categories list"
        return self._truncatefields(self._getfield(self._getentries(categories, min, max, "categories"), "category"), truncateat)

    def getemails(self, emails, min, max, truncateat=None):
        "Return at least min and at most max emails from the emails list"
        return self._truncatefields(self._getfield(self._getentries(emails, min, max, "emails"), "email"), truncateat)

    def geturls(self, urls, min, max, truncateat=None):
        "Return at least min and at most max urls from the urls list"
        return self._truncatefields(self._getfield(self._getentries(urls, min, max, "urls"), "url"), truncateat)
        

    def getmemos(self, memos, min, max, truncateat=None):
        "Return at least min and at most max memos from the memos list"
        return self._truncatefields(self._getfield(self._getentries(memos, min, max, "memos"), "memo"), truncateat)

    def getnumbers(self, numbers, min, max):
        "Return at least min and at most max numbers from the numbers list"
        return self._getentries(numbers, min, max, "numbers")

    def getserial(self, serials, sourcetype, id, key, default):
        "Gets a serial if it exists"
        return self._findfirst(serials, {'sourcetype': sourcetype, 'sourceuniqueid': id}, key, default)
        
    def getringtone(self, ringtones, use, default):
        "Gets a ringtone of type use"
        return self._findfirst(ringtones, {'use': use}, 'ringtone', default)

    def getwallpaper(self, wallpapers, use, default):
        "Gets a wallpaper of type use"
        return self._findfirst(wallpapers, {'use': use}, 'wallpaper', default)

    def getwallpaperindex(self, wallpapers, use, default):
        "Gets a wallpaper index of type use"
        return self._findfirst(wallpapers, {'use': use}, 'index', default)

    def getflag(self, flags, name, default):
        "Gets value of flag named name"
        for i in flags:
            if i.has_key(name):
                return i[name]
        return default

    def importdata(self, importdata, categoriesinfo=[], merge=True):
        if merge:
            d=self._data
        else:
            d={}
        dlg=ImportDialog(self, d, importdata)
        result=None
        if dlg.ShowModal()==wx.ID_OK:
            result=dlg.resultdata
        dlg.Destroy()
        if result is not None:
            d={}
            d['phonebook']=result
            d['categories']=categoriesinfo
            self.populatefs(d)
            self.populate(d)
            


class ImportDataTable(wx.grid.PyGridTableBase):
    ADDED=0
    UNALTERED=1
    CHANGED=2
    DELETED=3
    
    def __init__(self, widget):
        self.main=widget
        self.rowkeys=[]
        wx.grid.PyGridTableBase.__init__(self)
        self.columns=['Confidence', 'Name', 'Home', 'Email']
        self.addedattr=wx.grid.GridCellAttr()
        self.addedattr.SetBackgroundColour("HONEYDEW")
        self.unalteredattr=wx.grid.GridCellAttr()
        self.unalteredattr.SetBackgroundColour("WHITE")
        self.changedattr=wx.grid.GridCellAttr()
        self.changedattr.SetBackgroundColour("LEMON CHIFFON")
        self.deletedattr=wx.grid.GridCellAttr()
        self.deletedattr.SetBackgroundColour("ROSYBROWN1")

    def GetColLabelValue(self, col):
        return self.columns[col]

    def IsEmptyCell(self, row, col):
        return False

    def GetNumberCols(self):
        return len(self.columns)

    def GetNumberRows(self):
        return len(self.rowkeys)

    def GetAttr(self, row, col, _):
        try:
            # it likes to ask for non-existent cells
            row=self.main.rowdata[self.rowkeys[row]]
        except:
            return None
        v=None
        if row[3] is None:
            v=self.DELETED
        if v is None and (row[1] is not None and row[2] is not None):
            v=self.CHANGED
        if v is None and (row[1] is not None and row[2] is None):
            v=self.ADDED
        if v is None:
            v=self.UNALTERED
        r=[self.addedattr, self.unalteredattr, self.changedattr, self.deletedattr][v]
        r.IncRef()
        return r
                
    def GetValue(self, row, col):
        try:
            row=self.main.rowdata[self.rowkeys[row]]
        except:
            print "bad row", row
            return "<error>"
        
        if self.columns[col]=='Confidence':
            return row[0]

        for i,ptr in (3,self.main.resultdata), (1,self.main.importdata), (2, self.main.existingdata):
            if row[i] is not None:
                return getdata(self.columns[col], ptr[row[i]], "")
        return ""
            
    def OnDataUpdated(self):
        newkeys=self.main.rowdata.keys()
        newkeys.sort()
        oldrows=self.rowkeys
        self.rowkeys=newkeys
        lo=len(oldrows)
        ln=len(self.rowkeys)
        if ln>lo:
            msg=wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED, ln-lo)
        elif lo>ln:
            msg=wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_NOTIFY_ROWS_DELETED, 0, lo-ln)
        else:
            msg=None
        if msg is not None:
            self.GetView().ProcessTableMessage(msg)
        msg=wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_REQUEST_VIEW_GET_VALUES)
        self.GetView().AutoSizeColumns()
    

class ImportDialog(wx.Dialog):
    "The dialog for mixing new (imported) data with existing data"

    def __init__(self, parent, existingdata, importdata):
        wx.Dialog.__init__(self, parent, id=-1, title="Import Phonebook data", style=wx.CAPTION|
                 wx.SYSTEM_MENU|wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER|wx.NO_FULL_REPAINT_ON_RESIZE,
                           size=(740,680))

        # the data already in the phonebook
        self.existingdata=existingdata
        # the data we are importing
        self.importdata=importdata
        # the resulting data
        self.resultdata={}
        # each row to display showing what happened, with ids pointing into above data
        self.rowdata={}

        vbs=wx.BoxSizer(wx.VERTICAL)
        
        bg=self.GetBackgroundColour()
        w=wx.html.HtmlWindow(self, -1, size=wx.Size(600,50), style=wx.html.HW_SCROLLBAR_NEVER)
        w.SetPage('<html><body BGCOLOR="#%02X%02X%02X">Your data is being imported and BitPim is showing what will happen below so you can confirm its actions.</body></html>' % (bg.Red(), bg.Green(), bg.Blue()))
        vbs.Add(w, 0, wx.EXPAND|wx.ALL, 5)

        hbs=wx.BoxSizer(wx.HORIZONTAL)
        hbs.Add(wx.StaticText(self, -1, "Show entries"), 0, wx.EXPAND|wx.ALL,3)

        self.cbunaltered=wx.CheckBox(self, wx.NewId(), "Unaltered")
        self.cbadded=wx.CheckBox(self, wx.NewId(), "Added")
        self.cbchanged=wx.CheckBox(self, wx.NewId(), "Changed")
        self.cbdeleted=wx.CheckBox(self, wx.NewId(), "Deleted")

        for i in self.cbunaltered, self.cbadded, self.cbchanged, self.cbdeleted:
            i.SetValue(True)
            hbs.Add(i, 0, wx.ALIGN_CENTRE|wx.LEFT|wx.RIGHT, 7)

        hbs.Add(wx.StaticText(self, -1, " "), 0, wx.EXPAND|wx.LEFT, 10)

        self.details=wx.CheckBox(self, wx.NewId(), "Original/Import Details")
        self.details.SetValue(False)
        hbs.Add(self.details, 0, wx.EXPAND|wx.LEFT, 25)

        vbs.Add(hbs, 0, wx.EXPAND|wx.ALL, 5)

        splitterstyle=wx.SP_3D|wx.SP_LIVE_UPDATE
        self.splitterstyle=splitterstyle

        hsplit=wx.SplitterWindow(self,-1, style=splitterstyle)
        hsplit.SetMinimumPaneSize(20)

        self.resultpreview=PhoneEntryDetailsView(hsplit, -1, "styles.xy", "pblayout.xy")

        vsplit=wx.SplitterWindow(hsplit, -1, style=splitterstyle)
        vsplit.SetMinimumPaneSize(20)

        self.grid=wx.grid.Grid(vsplit, -1)
        self.grid.EnableGridLines(False)
        self.table=ImportDataTable(self)
        self.grid.SetTable(self.table, False, wx.grid.Grid.wxGridSelectRows)
        self.grid.SetSelectionMode(wx.grid.Grid.wxGridSelectRows)
        self.grid.SetRowLabelSize(0)
        self.grid.EnableDragRowSize(False)
        self.grid.EnableEditing(False)
        self.grid.SetMargins(1,0)

        self.hhsplit=None
        self.origpreview=None
        self.importpreview=None

        hsplit.SplitVertically(vsplit, self.resultpreview, -250)
        vsplit.Initialize(self.grid)
        # save these for OnDetailChanged
        self.vsplit=vsplit
        self.vsplitpos=-200
        self.hhsplitpos=0

        vbs.Add(hsplit, 1, wx.EXPAND|wx.ALL,5)
        vbs.Add(wx.StaticLine(self, -1, style=wx.LI_HORIZONTAL), 0, wx.EXPAND|wx.ALL, 5)

        vbs.Add(self.CreateButtonSizer(wx.OK|wx.CANCEL|wx.HELP), 0, wx.ALIGN_CENTRE|wx.ALL, 5)

        self.SetSizer(vbs)
        self.SetAutoLayout(True)

        wx.EVT_CHECKBOX(self, self.details.GetId(), self.OnDetailChanged)
        wx.grid.EVT_GRID_SELECT_CELL(self, self.OnCellSelect)
        wx.CallAfter(self.DoMerge)

    def DoMerge(self):
        """Merges all the importdata with existing data

        This can take quite a while!
        """
        wx.BeginBusyCursor(wx.StockCursor(wx.CURSOR_ARROWWAIT))
        count=0
        row={}
        results={}

        em=EntryMatcher(self.importdata, self.existingdata)
        usedexistingkeys=[]
        for i in self.importdata:
            # does it match existing entry
            matches=em.bestmatches(i)
            if len(matches):
                confidence, existingid=matches[0]
                if confidence>90:
                    results[count]=self.MergeEntries(self.existingdata[existingid], self.importdata[i])
                    row[count]=(confidence, i, existingid, count)
                    count+=1
                    usedexistingkeys.append(existingid)
                    continue
            # nope, so just add it
            results[count]=self.importdata[i]
            row[count]=(100, i, None, count)
            count+=1
        for i in self.existingdata:
            if i in usedexistingkeys: continue
            results[count]=self.existingdata[i]
            row[count]=("", None, i, count)
            count+=1
        self.rowdata=row
        self.resultdata=results
        self.table.OnDataUpdated()
        wx.EndBusyCursor()

    def MergeEntries(self, originalentry, importentry):
        "Take an original and a merge entry and join them together return a dict of the result"
        o=originalentry
        i=importentry
        result={}
        # Get the intersection.  Anything not in this is not controversial
        intersect=dictintersection(o,i)
        for dict in i,o:
            for k in dict.keys():
                if k not in intersect:
                    result[k]=dict[k]
        # now only deal with keys in both
        for key in intersect:
            if key=="names":
                # we ignore anything except the first name.  fields in existing take precedence
                r=i["names"][0].copy()
                for k in o["names"][0]:
                    r[k]=o["names"][0][k]
                result["names"]=[r]
            elif key=="numbers":
                result['numbers']=mergenumberlists(o['numbers'], i['numbers'])
            else:
                result[key]=o[key]+i[key]

        return result
        

    def OnCellSelect(self, event):
        row=self.rowdata[event.GetRow()]
        confidence,importid,existingid,resultid=row
        if self.importpreview is not None:
            if importid is not None:
                self.importpreview.ShowEntry(self.importdata[importid])
            else:
                self.importpreview.ShowEntry({})
        if self.origpreview is not None:
            if existingid is not None:
                self.origpreview.ShowEntry(self.existingdata[existingid])
            else:
                self.origpreview.ShowEntry({})
        if resultid is not None:
            self.resultpreview.ShowEntry(self.resultdata[resultid])
        else:
            self.resultpreview.ShowEntry({})


    def OnDetailChanged(self, _):
        "Show or hide the exiting/imported data previews"
        # We destroy and recreate the bottom splitter with the two previews in
        # them.  If that isn't done then the window doesn't draw properly amongst
        # other issues
        if self.details.GetValue():
            hhsplit=wx.SplitterWindow(self.vsplit, -1, style=self.splitterstyle)
            hhsplit.SetMinimumPaneSize(20)
            self.origpreview=PhoneEntryDetailsView(hhsplit, -1, "styles.xy", "pblayout.xy")
            self.importpreview=PhoneEntryDetailsView(hhsplit, -1, "styles.xy", "pblayout.xy")
            hhsplit.SplitVertically(self.origpreview, self.importpreview, self.hhsplitpos)
            self.hhsplit=hhsplit
            self.vsplit.SplitHorizontally(self.grid, self.hhsplit, self.vsplitpos)
        else:
            self.vsplitpos=self.vsplit.GetSashPosition()
            self.hhsplitpos=self.hhsplit.GetSashPosition()
            self.vsplit.Unsplit()
            self.hhsplit.Destroy()
            self.origpreview=None
            self.importpreview=None
                        

def dictintersection(one,two):
    return filter(two.has_key, one.keys())

class EntryMatcher:
    "Implements matching phonebook entries"

    def __init__(self, sources, against):
        self.sources=sources
        self.against=against

    def bestmatches(self, sourceid, limit=5):
        """Gives best matches out of against list

        @return: list of tuples of (percent match, againstid)
        """

        res=[]

        source=self.sources[sourceid]
        for i in self.against:
            against=self.against[i]

            # now get keys source and against have in common
            intersect=dictintersection(source,against)

            # overall score for this match
            score=0
            count=0
            for key in intersect:
                s=source[key]
                a=against[key]
                count+=1
                if key=="names":
                    score+=comparenames(s,a)
                elif key=="numbers":
                    score+=comparenumbers(s,a)
                elif key=="urls":
                    score+=comparefields(s,a,"url")
                elif key=="emails":
                    score+=comparefields(s,a,"email")
                elif key=="urls":
                    score+=comparefields(s,a,"url")
                elif key=="addresses":
                    score+=compareallfields(s,a, ("company", "street", "street2", "city", "state", "postalcode", "country"))
                else:
                    # ignore it
                    count-=1
                
            res.append( ( int(score*100/count), i ) )

        res.sort()
        res.reverse()
        if len(res)>limit:
            return res[:limit]
        return res

def comparenames(s,a):
    "Give a score on two names"
    sm=difflib.SequenceMatcher()
    sm.set_seq1(formatsimplename(s[0]))
    sm.set_seq2(formatsimplename(a[0]))
                    
    r=(sm.ratio()-0.6)*10
    return r


nondigits=re.compile("[^0-9]")
def cleannumber(num):
    "Returns num (a phone number) with all non-digits removed"
    return re.sub(nondigits, "", num)

def comparenumbers(s,a):
    """Give a score on two numbers

    """

    sm=difflib.SequenceMatcher()
    ss=[cleannumber(x['number']) for x in s]
    aa=[cleannumber(x['number']) for x in a]

    candidates=[]
    for snum in ss:
        sm.set_seq2(snum)
        for anum in aa:
            sm.set_seq1(anum)
            candidates.append( (sm.ratio(), snum, anum) )

    candidates.sort()
    candidates.reverse()

    if len(candidates)>3:
        candidates=candidates[:3]

    score=0
    # we now have 3 best matches
    for ratio,snum,anum in candidates:
        if ratio>0.9:
            score+=(ratio-0.9)*10

    return score

def comparefields(s,a,valuekey,threshold=0.8,lookat=3):
    sm=difflib.SequenceMatcher()
    ss=[x[valuekey] for x in s if x.has_key(valuekey)]
    aa=[x[valuekey] for x in a if x.has_key(valuekey)]

    candidates=[]
    for sval in ss:
        sm.set_seq2(sval)
        for aval in aa:
            sm.set_seq1(aval)
            candidates.append( (sm.ratio(), sval, aval) )

    candidates.sort()
    candidates.reverse()

    if len(candidates)>lookat:
        candidates=candidates[:lookat]

    score=0
    # we now have 3 best matches
    for ratio,sval,aval in candidates:
        if ratio>threshold:
            score+=(ratio-threshold)*10/(1-threshold)

    return score
    
def compareallfields(s,a,fields,threshold=0.8,lookat=3):
    args=[]
    for d in s,a:
        str=""
        for f in fields:
            if d.has_key(f):
                str+=d[f]+"  "
        args.append({'value': str})
    args.extend( ['value', threshold, lookat] )
    return comparefields(*args)

def mergenumberlists(orig, imp):
    """Return the results of merging two lists of numbers

    We compare the sanitised numbers (ie after punctuation etc is stripped
    out).  If they are the same, then the original is kept (since the number
    is the same, and the original most likely has the correct punctuation).

    Otherwise the imported entries overwrite the originals
    """
    # results start with existing entries
    res=[]
    res.extend(orig[:])
    # look through each imported number
    for i in imp:
        print i
        num=cleannumber(i['number'])
        found=False
        for r in res:
            if num==cleannumber(r['number']):
                # an existing entry was matched so we stop
                found=True
                if i.has_key('speeddial'):
                    r['speeddial']=i['speeddial']
                break
        if found:
            continue

        # we will be replacing one of the same type
        found=False
        for r in res:
            if i['type']==r['type']:
                r['number']=i['number']
                if i.has_key('speeddial'):
                    r['speeddial']=i['speeddial']
                found=True
                break
        if found:
            continue
        # ok, just add it on the end then
        res.append(i)

    return res


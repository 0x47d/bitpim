### BITPIM
###
### Copyright (C) 2003-2004 Roger Binns <rogerb@rogerbinns.com>
### Copyright (C) 2004 Adit Panchal <apanchal@bastula.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
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
  - use         see ringtones.use

flags:

  - secret     Boolean if record is private/secret (if not present - value is false)

memos:

  - memo       Note

numbers:

  - number     Phone number as ascii string
  - type       'home', 'office', 'cell', 'fax', 'pager', 'data', 'none'  (if you have home2 etc, list
               them without the digits.  The second 'home' is implicitly home2 etc)
  - speeddial  (optional) Speed dial number

serials:

  - sourcetype        identifies source driver in bitpim (eg "lgvx4400", "windowsaddressbook")
  - sourceuniqueid    (optional) identifier for where the serial came from (eg ESN of phone, wab host/username)
                      (imagine having multiple phones of the same model to see why this is needed)
  - *                 other names of use to sourcetype
"""

# Standard imports
import os
import cStringIO
import difflib
import re
import time
import random
import sha
import copy

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
import nameparser
import bphtml
import guiwidgets

###
### Phonebook entry display (Derived from HTML)
###

class PhoneEntryDetailsView(bphtml.HTMLWindow):

    def __init__(self, parent, id, stylesfile, layoutfile):
        bphtml.HTMLWindow.__init__(self, parent, id)
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
        try:
            text=bphtml.applyhtmlstyles(text, self.xcpstyles['styles'])
        except:
            if __debug__:
                f=open("debug.html", "wt")
                f.write(text)
                f.close()
            raise
        self.SetPage(text)

###
### Functions used to get data from a record
###


def formatcategories(cats):
    return "; ".join([cat['category'] for cat in cats])

def formataddress(address):
    l=[]
    for i in 'company', 'street', 'street2', 'city', 'state', 'postalcode', 'country':
        if i in address:
            l.append(address[i])
    return "; ".join(l)

def formatnumber(number):
    t=number['type']
    t=t[0].upper()+t[1:]
    return "%s (%s)" % (number['number'], t)

# this is specified here as a list so that we can get the
# keys in the order below for the settings UI (alpha sorting
# or dictionary order would be user hostile).  The data
# is converted to a dict below
_getdatalist=[
    # column   (matchnum   match   func_or_field)
    'Name', ("names", 0, None, nameparser.formatfullname),
    'First', ("names", 0, None, nameparser.getfirst),
    'Middle', ("names", 0, None, nameparser.getmiddle),
    'Last', ("names", 0, None, nameparser.getlast),

    # phone numbers are inserted here

    'Category', ("categories", 0,  None, "category"),
    'Category2', ("categories", 1,  None, "category"),
    'Category3', ("categories", 2,  None, "category"),
    'Categories', ("categories", None, None, formatcategories),

    'Email', ("emails", 0, None, "email"),
    'Email2', ("emails", 1, None, "email"),
    'Email3', ("emails", 2, None, "email"),
    'Business Email', ("emails", 0, ("type", "business"), "email"),
    'Home Email', ("emails", 0, ("type", "home"), "email"),

    'URL', ("urls", 0, None, "url"),
    'URL2', ("urls", 1, None, "url"),
    'URL3', ("urls", 2, None, "url"),
    'Business URL', ("urls", 0, ("type", "business"), "url"),
    'Home URL', ("urls", 0, ("type", "home"), "url"),

    'Ringtone', ("ringtones", 0, ("use", "call"), "ringtone"),
    'Message Ringtone', ("ringtones", 0, ("use", "message"), "ringtone"),

    'Address', ("addresses", 0, None, formataddress),
    'Address2', ("addresses", 1, None, formataddress),
    'Home Address', ("addresses", 0, ("type", "home"), formataddress),
    'Business Address', ("addressess", 0, ("type", "business"), formataddress),

    "Wallpaper", ("wallpapers", 0, None, "wallpaper"),

    "Secret", ("flags", 0, ("secret", True), "secret"),

    "Memo", ("memos", 0, None, "memo"),
    "Memo2", ("memos", 1, None, "memo"),
    "Memo3", ("memos", 2, None, "memo"),

    "Phone", ("numbers", 0, None, formatnumber),
    "Phone2", ("numbers", 1, None, formatnumber),
    "Phone3", ("numbers", 2, None, formatnumber),
    "Phone4", ("numbers", 3, None, formatnumber),
    "Phone5", ("numbers", 4, None, formatnumber),
    
    ]

ll=[]
for pretty, actual in ("Home", "home"), ("Office", "office"), ("Cell", "cell"), ("Fax", "fax"), ("Pager", "pager"), ("Data", "data"):
    for suf,n in ("", 0), ("2", 1), ("3", 2):
        ll.append(pretty+suf)
        ll.append(("numbers", n, ("type", actual), 'number'))
_getdatalist[8:8]=ll

_getdatatable={}
AvailableColumns=[]
DefaultColumns=['Name', 'Phone', 'Phone2', 'Phone3', 'Email', 'Categories', 'Memo', 'Secret']

for n in range(len(_getdatalist)/2):
    AvailableColumns.append(_getdatalist[n*2])
    _getdatatable[_getdatalist[n*2]]=_getdatalist[n*2+1]

del _getdatalist  # so we don't accidentally use it

def getdata(column, entry, default=None):

    key, count, prereq, formatter=_getdatatable[column]

    # do we even have that key
    if key not in entry:
        return default

    # which value or values do we want
    if count is None:
        # all of them
        thevalue=entry[key]
    elif prereq is None:
        # no prereq
        if len(entry[key])<=count:
            return default
        thevalue=entry[key][count]
    else:
        # find the count instance of value matching k,v in prereq
        ptr=0
        togo=count+1
        l=entry[key]
        k,v=prereq
        while togo:
            if ptr==len(l):
                return default
            if k not in l[ptr]:
                ptr+=1
                continue
            if l[ptr][k]!=v:
                ptr+=1
                continue
            togo-=1
            if togo!=0:
                ptr+=1
                continue
            thevalue=entry[key][ptr]
            break

    # thevalue now contains the dict with value we care about
    if callable(formatter):
        return formatter(thevalue)

    return thevalue.get(formatter, default)

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

    def __init__(self, widget, columns):
        self.main=widget
        self.rowkeys=self.main._data.keys()
        wx.grid.PyGridTableBase.__init__(self)
        self.oddattr=wx.grid.GridCellAttr()
        self.oddattr.SetBackgroundColour("OLDLACE")
        self.evenattr=wx.grid.GridCellAttr()
        self.evenattr.SetBackgroundColour("ALICE BLUE")
        self.columns=columns
        assert len(self.rowkeys)==0  # we can't sort here, and it isn't necessary because list is zero length

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
        self.Sort()
        msg=wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_REQUEST_VIEW_GET_VALUES)
        self.GetView().ProcessTableMessage(msg)
        self.GetView().AutoSizeColumns()

    def SetColumns(self, columns):
        oldcols=self.columns
        self.columns=columns
        lo=len(oldcols)
        ln=len(self.columns)
        if ln>lo:
            msg=wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_NOTIFY_COLS_APPENDED, ln-lo)
        elif lo>ln:
            msg=wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_NOTIFY_COLS_DELETED, 0, lo-ln)
        else:
            msg=None
        if msg is not None:
            self.GetView().ProcessTableMessage(msg)
        msg=wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_REQUEST_VIEW_GET_VALUES)
        self.GetView().ProcessTableMessage(msg)
        self.GetView().AutoSizeColumns()

    def Sort(self):
        bycol=self.main.sortedColumn
        descending=self.main.sortedColumnDescending
        ### ::TODO:: this sorting is not stable - it should include the current pos rather than key
        l=[ (getdata(self.columns[bycol], self.main._data[key]), key) for key in self.rowkeys]
        l.sort()
        if descending:
            l.reverse()
        self.rowkeys=[key for val,key in l]
        msg=wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_REQUEST_VIEW_GET_VALUES)
        self.GetView().ProcessTableMessage(msg)

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

thephonewidget=None  # track the instance

class PhoneWidget(wx.Panel):
    """Main phone editing/displaying widget"""
    CURRENTFILEVERSION=2
    def __init__(self, mainwindow, parent, config):
        global thephonewidget
        thephonewidget=self
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
        # which columns?
        cur=config.Read("phonebookcolumns", "")
        if len(cur):
            cur=cur.split(",")
            # ensure they all exist
            cur=[c for c in cur if c in AvailableColumns]
        else:
            cur=DefaultColumns
        # column sorter info
        self.sortedColumn=0
        self.sortedColumnDescending=False

        self.dt=PhoneDataTable(self, cur)
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
        wx.EVT_LEFT_DCLICK(self.preview, self.OnPreviewDClick)
        pubsub.subscribe(pubsub.ALL_CATEGORIES, self, "OnCategoriesUpdate")
        # we draw the column headers
        # code based on original implementation by Paul Mcnett
        wx.EVT_PAINT(self.table.GetGridColLabelWindow(), self.OnColumnHeaderPaint)
        wx.grid.EVT_GRID_LABEL_LEFT_CLICK(self.table, self.OnGridLabelLeftClick)
        wx.grid.EVT_GRID_LABEL_LEFT_DCLICK(self.table, self.OnGridLabelLeftClick)

    def OnColumnHeaderPaint(self, evt):
        w = self.table.GetGridColLabelWindow()
        dc = wx.PaintDC(w)
        font = dc.GetFont()
        dc.SetTextForeground(wx.BLACK)
        
        # For each column, draw it's rectangle, it's column name,
        # and it's sort indicator, if appropriate:
        totColSize = -self.table.GetViewStart()[0]*self.table.GetScrollPixelsPerUnit()[0]
        for col in range(self.table.GetNumberCols()):
            dc.SetBrush(wx.Brush("WHEAT", wx.TRANSPARENT))
            colSize = self.table.GetColSize(col)
            rect = (totColSize,0,colSize,32)
            dc.DrawRectangle(rect[0] - (col!=0 and 1 or 0), rect[1], rect[2] + (col!=0 and 1 or 0), rect[3])
            totColSize += colSize
            
            if col == self.sortedColumn:
                font.SetWeight(wx.BOLD)
                # draw a triangle, pointed up or down, at the
                # top left of the column.
                left = rect[0] + 3
                top = rect[1] + 3
                
                dc.SetBrush(wx.Brush("WHEAT", wx.SOLID))
                if self.sortedColumnDescending:
                    dc.DrawPolygon([(left,top), (left+6,top), (left+3,top+4)])
                else:
                    dc.DrawPolygon([(left+3,top), (left+6, top+4), (left, top+4)])
            else:
                font.SetWeight(wx.NORMAL)

            dc.SetFont(font)
            dc.DrawLabel("%s" % self.table.GetTable().columns[col],
                     rect, wx.ALIGN_CENTER | wx.ALIGN_TOP)


    def OnGridLabelLeftClick(self, evt):
        col=evt.GetCol()
        if col==self.sortedColumn:
            self.sortedColumnDescending=not self.sortedColumnDescending
        else:
            self.sortedColumn=col
            self.sortedColumnDescending=False
        self.dt.Sort()
        self.table.Refresh()


    def SetColumns(self, columns):
        c=self.GetColumns()[self.sortedColumn]
        self.dt.SetColumns(columns)
        if c in columns:
            self.sortedColumn=columns.index(c)
        else:
            self.sortedColumn=0
            self.sortedColumnDescending=False
        self.dt.Sort()
        self.table.Refresh()

    def GetColumns(self):
        return self.dt.columns

    def OnCategoriesUpdate(self, msg):
        if self.categories!=msg.data:
            self.categories=msg.data[:]
            self.modified=True

    def OnIdle(self, _):
        "We save out changed data"
        if self.modified:
            self.modified=False
            self.populatefs(self.getdata({}))

    # we use two random numbers to generate the serials.  _persistrandom
    # is seeded at startup
    _persistrandom=random.Random()
    def EnsureBitPimSerials(self):
        "Make sure all entries have a BitPim serial"
        rand2=random.Random() # this random is seeded when this function is called
        d={}
        for k in self._data:
            entry=self._data[k]
            found=False
            for s in entry.get("serials", []):
                if s.get("sourcetype", "")=="bitpim":
                    assert s["id"] not in d
                    d[s["id"]]=0
                    found=True
                    break
            if not found:
                num=sha.new()
                num.update(`self._persistrandom.random()`)
                num.update(`rand2.random()`)
                if "serials" not in entry: entry["serials"]=[]
                entry["serials"].append({"sourcetype": "bitpim", "id": num.hexdigest()})
                assert num.hexdigest() not in d
                d[num.hexdigest()]=0

    def updateserials(self, results):
        "update the serial numbers after having written to the phone"
        if not results.has_key('serialupdates'):
            return

        # each item is a tuple.  bpserial is the bitpim serialid,
        # and updserial is what to update with.
        for bpserial,updserial in results['serialupdates']:
            # find the entry with bpserial
            for k in self._data:
                entry=self._data[k]
                if not entry.has_key('serials'):
                    continue
                found=False
                for serial in entry['serials']:
                    if bpserial==serial:
                        found=True
                        break
                if not found:
                    # not this entry
                    continue
                # we will be updating this entry
                # see if there is a matching serial for updserial that we will update
                st=updserial['sourcetype']
                remove=None
                for serial in entry['serials']:
                    if serial['sourcetype']!=st:
                        continue
                    if updserial.has_key("sourceuniqueid"):
                        if updserial["sourceuniqueid"]!=serial.get("sourceuniqueid", None):
                            continue
                    remove=serial
                    break
                # remove if needbe
                if remove is not None:
                    for count,serial in zip(range(len(entry['serials'])), entry['serials']):
                        if remove==serial:
                            break
                    del entry['serials'][count]
                # add update on end
                entry['serials'].append(updserial)
        self.modified=True
                    
                    

    def OnCellSelect(self, event):
        event.Skip()
        row=event.GetRow()
        self.SetPreview(self._data[self.dt.rowkeys[row]]) # bad breaking of abstraction referencing dt!

    def OnPreviewDClick(self, _):
        self.EditEntry(self.table.GetGridCursorRow())

    def OnCellDClick(self, event):
        row=event.GetRow()
        self.EditEntry(row)

    def EditEntry(self, row):
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

    def GetSelectedRows(self):
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

        return rows

    def OnDelete(self,_):
        rows=self.GetSelectedRows()
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

    def OnPrintDialog(self, mainwindow, config):
        dlg=PhonebookPrintDialog(self, mainwindow, config)
        dlg.ShowModal()
        dlg.Destroy()

    def getdata(self, dict):
        self.EnsureBitPimSerials()
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
            dict['result']['phonebook']={}
            dict['result']['categories']=[]
            
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

    def importdata(self, importdata, categoriesinfo=[], merge=True):
        if merge:
            d=self._data
        else:
            d={}
        dlg=ImportDialog(self, d, importdata)
        result=None
        if dlg.ShowModal()==wx.ID_OK:
            result=dlg.resultdata
        guiwidgets.save_size(dlg.config, "ImportDialog", dlg.GetRect())
        dlg.Destroy()
        if result is not None:
            d={}
            d['phonebook']=result
            d['categories']=categoriesinfo
            self.populatefs(d)
            self.populate(d)
    
    def converttophone(self, data):
        self.mainwindow.phoneprofile.convertphonebooktophone(self, data)

    ###
    ###  The methods from here on are passed as the 'helper' to
    ###  convertphonebooktophone in the phone profiles.  One
    ###  day they may move to a seperate class.
    ###

    class ConversionFailed(Exception):
        pass

    def _getentries(self, list, min, max, name):
        candidates=[]
        for i in list:
            # ::TODO:: possibly ensure that a key appears in each i
            candidates.append(i)
        if len(candidates)<min:
            # ::TODO:: log this
            raise self.ConversionFailed("Too few %s.  Need at least %d but there were only %d" % (name,min,len(candidates)))
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
        n=[nameparser.formatsimplename(nn) for nn in names]
        if len(n)<min:
            raise self.ConversionFailed("Too few names.  Need at least %d but there were only %d" % (min, len(n)))
        if len(n)>max:
            n=n[:max]
            # ::TODO:: mention this
        return self._truncatefields(n, truncateat)

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

    def getnumber(self, numbers, type, count=1, default=""):
        """Returns phone numbers of the type

        @param numbers: The list of numbers
        @param type: The type, such as cell, home, office
        @param count: Which number to return (eg with type=home, count=2 the second
                    home number is returned)
        @param fallback: What is returned if there is no such number"""
        for n in numbers:
            if n['type']==type:
                if count==1:
                    return n['number']
                count-=1
        return default

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

    def getmostpopularcategories(self, howmany, entries, reserved=[], truncateat=None, padnames=[]):
        """Returns the most popular categories

        @param howmany:  How many to return, including the reserved ones
        @ptype howmany:  int
        @param entries:  A dict of the entries
        @param reserved: A list of reserved entries (ie must be present, no matter
                         how popular)
        @param truncateat: How long to truncate the category names at
        @param padnames: if the list is less than howmany long, then add these on the end providing
                         they are not already in the list
        @return: A list of the group names.  The list starts with the members of
               reserved followed by the most popular groups
        """
        # build a histogram
        freq={}
        for entry in entries:
            e=entries[entry]
            for cat in e.get('categories', []):
               n=cat['category']
               if truncateat: n=n[:truncateat] # truncate
               freq[n]=1+freq.get(n,0)
        # sort
        freq=[(count,value) for value,count in freq.items()]
        freq.sort()
        freq.reverse() # most popular first
        # build a new list
        newl=reserved[:]
        for _, group in freq:
            if len(newl)==howmany:
                break
            if group not in newl:
                newl.append(group)
        # pad list out
        for p in padnames:
            if len(newl)==howmany:
                break
            if p not in newl:
                newl.append(p)
                
        return newl

class ImportCellRenderer(wx.grid.PyGridCellRenderer):
    SCALE=0.8
    def __init__(self):
        wx.grid.PyGridCellRenderer.__init__(self)

    def Draw(self, grid, attr, dc, rect, row, col, isSelected):

        dc.SetClippingRect(rect)

        # clear the background
        dc.SetBackgroundMode(wx.SOLID)
        if isSelected:
            dc.SetBrush(wx.Brush(wx.BLUE, wx.SOLID))
            dc.SetPen(wx.Pen(wx.BLUE, 1, wx.SOLID))
        else:
            dc.SetBrush(wx.Brush(attr.GetBackgroundColour(), wx.SOLID))
            dc.SetPen(wx.Pen(attr.GetBackgroundColour(), 1, wx.SOLID))
        dc.DrawRectangle(rect.x, rect.y, rect.width, rect.height)
        if isSelected:
            dc.SetPen(wx.Pen(wx.WHITE,1,wx.SOLID))
        else:
            dc.SetPen(wx.Pen(wx.BLACK,1,wx.SOLID))

        dc.SetBackgroundMode(wx.TRANSPARENT)

        text = grid.GetTable().GetHtmlCellValue(row, col)
        bphtml.drawhtml(dc,
                        wx.Rect(rect.x+2, rect.y+1, rect.width-4, rect.height-2),
                        text, scale=self.SCALE)
        dc.DestroyClippingRegion()

    def GetBestSize(self, grid, attr, dc, row, col):
        text = grid.GetTable().GetHtmlCellValue(row, col)
        return bphtml.getbestsize(dc, text, scale=self.SCALE)

    def Clone(self):
        return ImportCellRenderer()


class ImportDataTable(wx.grid.PyGridTableBase):
    ADDED=0
    UNALTERED=1
    CHANGED=2
    DELETED=3

    htmltemplate=["Not set - "+`i` for i in range(8)]
    
    def __init__(self, widget):
        self.main=widget
        self.rowkeys=[]
        wx.grid.PyGridTableBase.__init__(self)
        self.columns=['Confidence']+thephonewidget.GetColumns()
        self.addedattr=wx.grid.GridCellAttr()
        self.addedattr.SetBackgroundColour("HONEYDEW")
        self.unalteredattr=wx.grid.GridCellAttr()
        self.unalteredattr.SetBackgroundColour("WHITE")
        self.changedattr=wx.grid.GridCellAttr()
        self.changedattr.SetBackgroundColour("LEMON CHIFFON")
        self.changedattr.SetRenderer(ImportCellRenderer())
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

    def GetHtmlCellValue(self, row, col):
        try:
            row=self.main.rowdata[self.rowkeys[row]]
        except:
            print "bad row", row
            return "&gt;error&lt;"

        if self.columns[col]=='Confidence':
            return `row[0]`

        # as an exercise in madness, try to redo this as a list comprehension
        imported,existing,result=None,None,None
        if row[1] is not None:
            imported=getdata(self.columns[col], self.main.importdata[row[1]], None)
        if row[2] is not None:
            existing=getdata(self.columns[col], self.main.existingdata[row[2]], None)
        if row[3] is not None:
            result=getdata(self.columns[col], self.main.resultdata[row[3]], None)

        # this code is both hacky and elegant!
        idx=((imported is not None)<<2 ) + \
            ((existing is not None)<<1 ) + \
            (result is not None)

        # ::TODO:: don't give so much detail if the imported/existing/result
        # match each other after doing a "lossy" comparison (eg the phone
        # numbers 1234567890 and 1-234-6790 should be considered the same)

        return self.htmltemplate[idx] % { 'imported': _htmlfixup(imported),
                                          'existing': _htmlfixup(existing),
                                          'result': _htmlfixup(result) }

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
        self.GetView().ProcessTableMessage(msg)
        wx.CallAfter(self.GetView().AutoSizeColumns)
        wx.CallAfter(self.GetView().AutoSizeRows)

def _htmlfixup(txt):
    if txt is None: return ""
    return txt.replace("&", "&amp;").replace("<", "&gt;").replace(">", "&lt;") \
           .replace("\r\n", "<br/>").replace("\r", "<br/>").replace("\n", "<br/>")

ImportDataTable.htmltemplate[0]=""
ImportDataTable.htmltemplate[7]="%(result)s<br><b><font size=-1>Imported</font></b> %(imported)s<br><b><font size=-1>Existing</font></b> %(existing)s"

class ImportDialog(wx.Dialog):
    "The dialog for mixing new (imported) data with existing data"

    def __init__(self, parent, existingdata, importdata):
        wx.Dialog.__init__(self, parent, id=-1, title="Import Phonebook data", style=wx.CAPTION|
             wx.SYSTEM_MENU|wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER|wx.NO_FULL_REPAINT_ON_RESIZE)
        self.config = parent.mainwindow.config
        guiwidgets.set_size(self.config, "ImportDialog", self, screenpct=95,  aspect=1.10)
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
        self.cbchanged=wx.CheckBox(self, wx.NewId(), "Merged")
        self.cbdeleted=wx.CheckBox(self, wx.NewId(), "Deleted")

        for i in self.cbunaltered, self.cbadded, self.cbchanged, self.cbdeleted:
            i.SetValue(True)
            hbs.Add(i, 0, wx.ALIGN_CENTRE|wx.LEFT|wx.RIGHT, 7)

        hbs.Add(wx.StaticText(self, -1, " "), 0, wx.EXPAND|wx.LEFT, 10)

        vbs.Add(hbs, 0, wx.EXPAND|wx.ALL, 5)

        splitterstyle=wx.SP_3D|wx.SP_LIVE_UPDATE

        splitter=wx.SplitterWindow(self,-1, style=splitterstyle)
        splitter.SetMinimumPaneSize(20)

        self.resultpreview=PhoneEntryDetailsView(splitter, -1, "styles.xy", "pblayout.xy")

        self.grid=wx.grid.Grid(splitter, -1)
        self.grid.EnableGridLines(False)
        self.table=ImportDataTable(self)
        self.grid.SetTable(self.table, False, wx.grid.Grid.wxGridSelectRows)
        self.grid.SetSelectionMode(wx.grid.Grid.wxGridSelectRows)
        self.grid.SetRowLabelSize(0)
        self.grid.EnableDragRowSize(True)
        self.grid.EnableEditing(False)
        self.grid.SetMargins(1,0)

        splitter.SplitVertically(self.grid, self.resultpreview, -250)

        vbs.Add(splitter, 1, wx.EXPAND|wx.ALL,5)
        vbs.Add(wx.StaticLine(self, -1, style=wx.LI_HORIZONTAL), 0, wx.EXPAND|wx.ALL, 5)

        vbs.Add(self.CreateButtonSizer(wx.OK|wx.CANCEL|wx.HELP), 0, wx.ALIGN_CENTRE|wx.ALL, 5)

        self.SetSizer(vbs)
        self.SetAutoLayout(True)

        wx.grid.EVT_GRID_SELECT_CELL(self, self.OnCellSelect)
        wx.CallAfter(self.DoMerge)

    def DoMerge(self):
        """Merges all the importdata with existing data

        This can take quite a while!
        """

        # We go to great lengths to ensure that a copy of the import
        # and existing data is passed on to the routines we call and
        # data structures being built.  Originally the code expected
        # the called routines to make copies of the data they were
        # copying/modifying, but it proved too error prone and often
        # ended up modifying the original/import data passed in.  That
        # had the terrible side effect of meaning that your original
        # data got modified even if you pressed cancel!

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
                    results[count]=self.MergeEntries(copy.deepcopy(self.existingdata[existingid]),
                                                     copy.deepcopy(self.importdata[i]))
                    row[count]=(confidence, i, existingid, count)
                    count+=1
                    usedexistingkeys.append(existingid)
                    continue
            # nope, so just add it
            results[count]=copy.deepcopy(self.importdata[i])
            row[count]=(100, i, None, count)
            count+=1
        for i in self.existingdata:
            if i in usedexistingkeys: continue
            results[count]=copy.deepcopy(self.existingdata[i])
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
                    result[k]=dict[k][:]
        # now only deal with keys in both
        for key in intersect:
            if key=="names":
                # we ignore anything except the first name.  fields in existing take precedence
                r=i["names"][0]
                for k in o["names"][0]:
                    r[k]=o["names"][0][k]
                result["names"]=[r]
            elif key=="numbers":
                result['numbers']=mergenumberlists(o['numbers'], i['numbers'])
            elif key=="urls":
                result['urls']=mergefields(o['urls'], i['urls'], 'url', cleaner=cleanurl)
            else:
                result[key]=common.list_union(o[key], i[key])

        return result
        
    def OnCellSelect(self, event):
        event.Skip()
        row=self.rowdata[event.GetRow()]
        confidence,importid,existingid,resultid=row
        if resultid is not None:
            self.resultpreview.ShowEntry(self.resultdata[resultid])
        else:
            self.resultpreview.ShowEntry({})


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

            if count:
                res.append( ( int(score*100/count), i ) )

        res.sort()
        res.reverse()
        if len(res)>limit:
            return res[:limit]
        return res

def comparenames(s,a):
    "Give a score on two names"
    sm=difflib.SequenceMatcher()
    sm.set_seq1(nameparser.formatsimplename(s[0]))
    sm.set_seq2(nameparser.formatsimplename(a[0]))
                    
    r=(sm.ratio()-0.6)*10
    return r

def cleanurl(url, mode="compare"):
    """Returns lowercase url with the "http://" prefix removed
    
    @param mode: If the value is compare (default), it removes ""http://www.""
                 in preparation for comparing entries. Otherwise, if the value
                 is pb, the result is formatted for writing to the phonebook.
    """
    if mode == "compare":
        urlprefix=re.compile("^(http://)?(www.)?")
    else: urlprefix=re.compile("^(http://)?")
    
    return default_cleaner(re.sub(urlprefix, "", url).lower())


nondigits=re.compile("[^0-9]")
def cleannumber(num):
    "Returns num (a phone number) with all non-digits removed"
    return re.sub(nondigits, "", num)

def comparenumbers(s,a):
    """Give a score on two phone numbers

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
    """Compares the valuekey field in source and against lists returning a score for closeness of match"""
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
    """Like comparefields, but for source and against lists where multiple keys have values in each item

    @param fields: This should be a list of keys from the entries that are in the order the human
                   would write them down."""

    # we do it in "write them down order" as that means individual values that move don't hurt the matching
    # much  (eg if the town was wrongly in address2 and then moved into town, the concatenated string would
    # still be the same and it would still be an appropriate match)
    args=[]
    for d in s,a:
        str=""
        list=[]
        for entry in d:
            for f in fields:
                # we merge together the fields space separated in order to make one long string from the values
                if entry.has_key(f):
                    str+=entry.get(f)+"  "
            list.append( {'value': str} )
        args.append( list )
    # and then give the result to comparefields
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
    res.extend(orig)
    # look through each imported number
    for i in imp:
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

def default_cleaner(param):
    """Clean fields for merging.  In particular * characters have to be
    removed since winkler uses them internally"""
    # ::TODO:: reimplment winkler and use a different special character such as an unprintable one
    return param.replace("*", "")

def mergefields(orig, imp, field, threshold=0.88, cleaner=default_cleaner):
    """Return the results of merging two lists of fields

    We compare the fields. If they are the same, then the original is kept
    (since the name is the same, and the original most likely has the 
    correct punctuation).

    Otherwise the imported entries overwrite the originals
    """
    # results start with existing entries
    res=[]
    res.extend(orig)
    # look through each imported field
    for i in imp:

        impfield=cleaner(i[field])
        
        found=False
        for r in res:
            # if the imported entry is similar or the same as the
            # original entry, then we stop
            
            # add code for short or long lengths
            # since cell phones usually have less than 16-22 chars max per field

            resfield=cleaner(r[field])

            if (comparestrings(resfield, impfield) > threshold):
                # an existing entry was matched so we stop
                found=True
                
                # since new item matches, we don't need to replace the
                # original value, but we should update the type of item
                # to reflect the imported value
                # for example home --> business
                if i.has_key('type'):
                    r['type'] = i['type']
                
                # break out of original item loop
                break
        
        # if we have found the item to be imported, we can move to the next one
        if found:
            continue

        # since there is no matching item, we will replace the existing item
        # if a matching type exists
        found=False
        for r in res:
            if (i.has_key('type') and r.has_key('type')):
                if i['type']==r['type']:
                    # write the field entry in the way the phonebook expects it
                    r[field]=cleaner(i[field], "pb")
                    found=True
                    break
        if found:
            continue
        # add new item on the end if there no matching type
        # and write the field entry in the way the phonebook expects it
        i[field] = cleaner(i[field], "pb")
        res.append(i)

    return res

try:
    # Try to use febrl's winkler ...
    import stringcmp
    stringcmp.winkler

    def comparestrings(origfield, impfield):
        """ Compares two strings and returns the score using 
        winkler routine from Febrl (stringcmp.py)
        
        Return value is between 0.0 and 1.0, where 0.0 means no similarity
        whatsoever, and 1.0 means the strings match exactly."""
        return stringcmp.winkler(origfield, impfield)

except:
    # fallback on difflib
    import difflib
    def comparestrings(origfield, impfield):
        """ Compares two strings and returns the score using Python's
        built-in difflib (if stringcmp.py isn't available).
        
        Return value is between 0.0 and 1.0, where 0.0 means no similarity
        whatsoever, and 1.0 means the strings match exactly."""
        sm=difflib.SequenceMatcher()
        sm.set_seq1(origfield)
        sm.set_seq2(impfield)
        return sm.ratio()

class ColumnSelectorDialog(wx.Dialog):
    "The dialog for selecting what columns you want to view"

    ID_SHOW=wx.NewId()
    ID_AVAILABLE=wx.NewId()
    ID_UP=wx.NewId()
    ID_DOWN=wx.NewId()
    ID_ADD=wx.NewId()
    ID_REMOVE=wx.NewId()
    ID_DEFAULT=wx.NewId()

    def __init__(self, parent, config, phonewidget):
        wx.Dialog.__init__(self, parent, id=-1, title="Select Columns to view", style=wx.CAPTION|
                 wx.SYSTEM_MENU|wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)

        self.config=config
        self.phonewidget=phonewidget
        hbs=wx.BoxSizer(wx.HORIZONTAL)

        # the show bit
        bs=wx.BoxSizer(wx.VERTICAL)
        bs.Add(wx.StaticText(self, -1, "Showing"), 0, wx.ALIGN_CENTRE|wx.ALL, 5)
        self.show=wx.ListBox(self, self.ID_SHOW, style=wx.LB_SINGLE|wx.LB_NEEDED_SB, size=(250, 300))
        bs.Add(self.show, 1, wx.EXPAND|wx.ALL, 5)
        hbs.Add(bs, 1, wx.EXPAND|wx.ALL, 5)

        # the column of buttons
        bs=wx.BoxSizer(wx.VERTICAL)
        self.up=wx.Button(self, self.ID_UP, "Move Up")
        self.down=wx.Button(self, self.ID_DOWN, "Move Down")
        self.add=wx.Button(self, self.ID_ADD, "Show")
        self.remove=wx.Button(self, self.ID_REMOVE, "Don't Show")
        self.default=wx.Button(self, self.ID_DEFAULT, "Default")

        for b in self.up, self.down, self.add, self.remove, self.default:
            bs.Add(b, 0, wx.ALL|wx.ALIGN_CENTRE, 10)

        hbs.Add(bs, 0, wx.ALL|wx.ALIGN_CENTRE, 5)

        # the available bit
        bs=wx.BoxSizer(wx.VERTICAL)
        bs.Add(wx.StaticText(self, -1, "Available"), 0, wx.ALIGN_CENTRE|wx.ALL, 5)
        self.available=wx.ListBox(self, self.ID_AVAILABLE, style=wx.LB_EXTENDED|wx.LB_NEEDED_SB, choices=AvailableColumns)
        bs.Add(self.available, 1, wx.EXPAND|wx.ALL, 5)
        hbs.Add(bs, 1, wx.EXPAND|wx.ALL, 5)

        # main layout
        vbs=wx.BoxSizer(wx.VERTICAL)
        vbs.Add(hbs, 1, wx.EXPAND|wx.ALL, 5)
        vbs.Add(wx.StaticLine(self, -1, style=wx.LI_HORIZONTAL), 0, wx.EXPAND|wx.ALL, 5)
        vbs.Add(self.CreateButtonSizer(wx.OK|wx.CANCEL|wx.HELP), 0, wx.ALIGN_CENTRE|wx.ALL, 5)

        self.SetSizer(vbs)
        vbs.Fit(self)

        # fill in current selection
        cur=self.config.Read("phonebookcolumns", "")
        if len(cur):
            cur=cur.split(",")
            # ensure they all exist
            cur=[c for c in cur if c in AvailableColumns]
        else:
            cur=DefaultColumns
        self.show.Set(cur)

        # buttons, events etc
        self.up.Disable()
        self.down.Disable()
        self.add.Disable()
        self.remove.Disable()

        wx.EVT_LISTBOX(self, self.ID_SHOW, self.OnShowClicked)
        wx.EVT_LISTBOX_DCLICK(self, self.ID_SHOW, self.OnShowClicked)
        wx.EVT_LISTBOX(self, self.ID_AVAILABLE, self.OnAvailableClicked)
        wx.EVT_LISTBOX_DCLICK(self, self.ID_AVAILABLE, self.OnAvailableDClicked)

        wx.EVT_BUTTON(self, self.ID_ADD, self.OnAdd)
        wx.EVT_BUTTON(self, self.ID_REMOVE, self.OnRemove)
        wx.EVT_BUTTON(self, self.ID_UP, self.OnUp)
        wx.EVT_BUTTON(self, self.ID_DOWN, self.OnDown)
        wx.EVT_BUTTON(self, self.ID_DEFAULT, self.OnDefault)
        wx.EVT_BUTTON(self, wx.ID_OK, self.OnOk)

    def OnShowClicked(self, _=None):
        self.up.Enable(self.show.GetSelection()>0)
        self.down.Enable(self.show.GetSelection()<self.show.GetCount()-1)
        self.remove.Enable(self.show.GetCount()>0)
        self.FindWindowById(wx.ID_OK).Enable(self.show.GetCount()>0)

    def OnAvailableClicked(self, _):
        self.add.Enable(True)

    def OnAvailableDClicked(self, _):
        self.OnAdd()

    def OnAdd(self, _=None):
        items=[AvailableColumns[i] for i in self.available.GetSelections()]
        for i in self.available.GetSelections():
            self.available.Deselect(i)
        self.add.Disable()
        it=self.show.GetSelection()
        if it>=0:
            self.show.Deselect(it)
            it+=1
        else:
            it=self.show.GetCount()
        self.show.InsertItems(items, it)
        self.remove.Disable()
        self.up.Disable()
        self.down.Disable()
        self.show.SetSelection(it)
        self.OnShowClicked()

    def OnRemove(self, _):
        it=self.show.GetSelection()
        assert it>=0
        self.show.Delete(it)
        if self.show.GetCount():
            if it==self.show.GetCount():
                self.show.SetSelection(it-1)
            else:
                self.show.SetSelection(it)
        self.OnShowClicked()

    def OnDefault(self,_):
        self.show.Set(DefaultColumns)
        self.show.SetSelection(0)
        self.OnShowClicked()

    def OnUp(self, _):
        it=self.show.GetSelection()
        assert it>=1
        self.show.InsertItems([self.show.GetString(it)], it-1)
        self.show.Delete(it+1)
        self.show.SetSelection(it-1)
        self.OnShowClicked()

    def OnDown(self, _):
        it=self.show.GetSelection()
        assert it<self.show.GetCount()-1
        self.show.InsertItems([self.show.GetString(it)], it+2)
        self.show.Delete(it)
        self.show.SetSelection(it+1)
        self.OnShowClicked()

    def OnOk(self, event):
        cur=[self.show.GetString(i) for i in range(self.show.GetCount())]
        self.config.Write("phonebookcolumns", ",".join(cur))
        self.config.Flush()
        self.phonewidget.SetColumns(cur)
        event.Skip()

class PhonebookPrintDialog(wx.Dialog):

    ID_SELECTED=wx.NewId()
    ID_ALL=wx.NewId()
    ID_LAYOUT=wx.NewId()
    ID_STYLES=wx.NewId()
    ID_PRINT=wx.NewId()
    ID_PAGESETUP=wx.NewId()
    ID_PRINTPREVIEW=wx.NewId()
    ID_CLOSE=wx.ID_CANCEL
    ID_HELP=wx.NewId()
    ID_TEXTSCALE=wx.NewId()

    textscales=[ (0.4, "Teeny"), (0.6, "Tiny"), (0.8, "Small"), (1.0, "Normal"), (1.2, "Large"), (1.4, "Ginormous") ]
    # we reverse the order so the slider seems more natural
    textscales.reverse()

    def __init__(self, phonewidget, mainwindow, config):
        wx.Dialog.__init__(self, mainwindow, id=-1, title="Print PhoneBook", style=wx.CAPTION|
                 wx.SYSTEM_MENU|wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)

        self.config=config
        self.phonewidget=phonewidget

        # sort out available layouts and styles
        # first line is description
        self.layoutfiles={}
        for file in guihelper.getresourcefiles("pbpl-*.xy"):
            f=open(file, "rt")
            desc=f.readline().strip()
            self.layoutfiles[desc]=f.read()
            f.close()
        self.stylefiles={}
        for file in guihelper.getresourcefiles("pbps-*.xy"):
            f=open(file, "rt")
            desc=f.readline().strip()
            self.stylefiles[desc]=f.read()
            f.close()

        # Layouts
        vbs=wx.BoxSizer(wx.VERTICAL)  # main vertical sizer

        hbs=wx.BoxSizer(wx.HORIZONTAL) # first row

        numselected=len(phonewidget.GetSelectedRows())
        numtotal=len(phonewidget._data)

        # selection and scale
        vbs2=wx.BoxSizer(wx.VERTICAL)
        bs=wx.StaticBoxSizer(wx.StaticBox(self, -1, "Rows"), wx.VERTICAL)
        self.selected=wx.RadioButton(self, self.ID_SELECTED, "Selected (%d)" % (numselected,), style=wx.RB_GROUP)
        self.all=wx.RadioButton(self, self.ID_SELECTED, "All (%d)" % (numtotal,) )
        bs.Add(self.selected, 0, wx.EXPAND|wx.ALL, 2)
        bs.Add(self.all, 0, wx.EXPAND|wx.ALL, 2)
        self.selected.SetValue(numselected>1)
        self.all.SetValue(not (numselected>1))
        vbs2.Add(bs, 0, wx.EXPAND|wx.ALL, 2)

        bs=wx.StaticBoxSizer(wx.StaticBox(self, -1, "Text Scale"), wx.HORIZONTAL)
        for i in range(len(self.textscales)):
            if self.textscales[i][0]==1.0:
                sv=i
                break
        self.textscaleslider=wx.Slider(self, self.ID_TEXTSCALE, sv, 0, len(self.textscales)-1, style=wx.SL_VERTICAL|wx.SL_AUTOTICKS)
        self.scale=1
        bs.Add(self.textscaleslider, 0, wx.EXPAND|wx.ALL, 2)
        self.textscalelabel=wx.StaticText(self, -1, "Normal")
        bs.Add(self.textscalelabel, 0, wx.ALIGN_CENTRE)
        vbs2.Add(bs, 1, wx.EXPAND|wx.ALL, 2)
        hbs.Add(vbs2, 0, wx.EXPAND|wx.ALL, 2)
        
        # Sort
        self.sortkeyscb=[]
        bs=wx.StaticBoxSizer(wx.StaticBox(self, -1, "Sorting"), wx.VERTICAL)
        choices=["<None>"]+AvailableColumns
        for i in range(3):
            bs.Add(wx.StaticText(self, -1, ("Sort by", "Then")[i!=0]), 0, wx.EXPAND|wx.ALL, 2)
            self.sortkeyscb.append(wx.ComboBox(self, wx.NewId(), "<None>", choices=choices, style=wx.CB_READONLY))
            self.sortkeyscb[-1].SetSelection(0)
            bs.Add(self.sortkeyscb[-1], 0, wx.EXPAND|wx.ALL, 2)
        hbs.Add(bs, 0, wx.EXPAND|wx.ALL, 4)

        # Layout and style
        vbs2=wx.BoxSizer(wx.VERTICAL) # they are on top of each other
        bs=wx.StaticBoxSizer(wx.StaticBox(self, -1, "Layout"), wx.VERTICAL)
        k=self.layoutfiles.keys()
        k.sort()
        self.layout=wx.ListBox(self, self.ID_LAYOUT, style=wx.LB_SINGLE|wx.LB_NEEDED_SB|wx.LB_HSCROLL, choices=k, size=(150,-1))
        self.layout.SetSelection(0)
        bs.Add(self.layout, 1, wx.EXPAND|wx.ALL, 2)
        vbs2.Add(bs, 1, wx.EXPAND|wx.ALL, 2)
        bs=wx.StaticBoxSizer(wx.StaticBox(self, -1, "Styles"), wx.VERTICAL)
        k=self.stylefiles.keys()
        self.styles=wx.CheckListBox(self, self.ID_STYLES, choices=k)
        bs.Add(self.styles, 1, wx.EXPAND|wx.ALL, 2)
        vbs2.Add(bs, 1, wx.EXPAND|wx.ALL, 2)
        hbs.Add(vbs2, 1, wx.EXPAND|wx.ALL, 2)

        # Buttons
        vbs2=wx.BoxSizer(wx.VERTICAL)
        vbs2.Add(wx.Button(self, self.ID_PRINT, "Print"), 0, wx.EXPAND|wx.ALL, 2)
        vbs2.Add(wx.Button(self, self.ID_PAGESETUP, "Page Setup..."), 0, wx.EXPAND|wx.ALL, 2)
        vbs2.Add(wx.Button(self, self.ID_PRINTPREVIEW, "Print Preview"), 0, wx.EXPAND|wx.ALL, 2)
        vbs2.Add(wx.Button(self, self.ID_HELP, "Help"), 0, wx.EXPAND|wx.ALL, 2)
        vbs2.Add(wx.Button(self, self.ID_CLOSE, "Close"), 0, wx.EXPAND|wx.ALL, 2)
        hbs.Add(vbs2, 0, wx.EXPAND|wx.ALL, 2)

        # wrap up top row
        vbs.Add(hbs, 1, wx.EXPAND|wx.ALL, 2)

        # bottom half - preview
        bs=wx.StaticBoxSizer(wx.StaticBox(self, -1, "Content Preview"), wx.VERTICAL)
        self.preview=bphtml.HTMLWindow(self, -1)
        bs.Add(self.preview, 1, wx.EXPAND|wx.ALL, 2)

        # wrap up bottom row
        vbs.Add(bs, 2, wx.EXPAND|wx.ALL, 2)

        self.SetSizer(vbs)
        vbs.Fit(self)

        # event handlers
        wx.EVT_BUTTON(self, self.ID_PRINTPREVIEW, self.OnPrintPreview)
        wx.EVT_BUTTON(self, self.ID_PRINT, self.OnPrint)
        wx.EVT_BUTTON(self, self.ID_PAGESETUP, self.OnPageSetup)
        wx.EVT_RADIOBUTTON(self, self.selected.GetId(), self.UpdateHtml)
        wx.EVT_RADIOBUTTON(self, self.all.GetId(), self.UpdateHtml)
        for i in self.sortkeyscb:
            wx.EVT_COMBOBOX(self, i.GetId(), self.UpdateHtml)
        wx.EVT_LISTBOX(self, self.layout.GetId(), self.UpdateHtml)
        wx.EVT_CHECKLISTBOX(self, self.styles.GetId(), self.UpdateHtml)
        wx.EVT_COMMAND_SCROLL(self, self.textscaleslider.GetId(), self.UpdateSlider)
        self.UpdateHtml()

    def UpdateSlider(self, evt):
        pos=evt.GetPosition()
        if self.textscales[pos][0]!=self.scale:
            self.scale=self.textscales[pos][0]
            self.textscalelabel.SetLabel(self.textscales[pos][1])
            self.preview.SetFontScale(self.scale)

    def UpdateHtml(self,_=None):
        wx.CallAfter(self._UpdateHtml)

    def _UpdateHtml(self):
        self.html=self.GetCurrentHTML()
        self.preview.SetPage(self.html)

    def GetCurrentHTML(self):
        wx.BeginBusyCursor(wx.StockCursor(wx.CURSOR_ARROWWAIT))
        wx.Yield() # so the cursor can be displayed
        # Setup a nice environment pointing at this module
        vars={'phonebook': __import__(__name__) }
        # which data do we want?
        if self.all.GetValue():
            rowkeys=self.phonewidget._data.keys()
        else:
            rowkeys=self.phonewidget.GetSelectedRows()
        # sort the data
        # we actually sort in reverse order of what the UI shows in order to get correct results
        for keycb in (-1, -2, -3):
            sortkey=self.sortkeyscb[keycb].GetValue()
            if sortkey=="<None>": continue
            # decorate
            l=[(getdata(sortkey, self.phonewidget._data[key]), key) for key in rowkeys]
            l.sort()
            # undecorate
            rowkeys=[key for val,key in l]
        # finish up vars
        vars['rowkeys']=rowkeys
        vars['currentcolumns']=self.phonewidget.GetColumns()
        vars['data']=self.phonewidget._data
        # Use xyaptu
        xcp=xyaptu.xcopier(None)
        xcp.setupxcopy(self.layoutfiles[self.layout.GetStringSelection()])
        html=xcp.xcopywithdns(vars)
        # apply styles
        sd={'styles': {}, '__builtins__': __builtins__ }
        for i in range(self.styles.GetCount()):
            if self.styles.IsChecked(i):
                exec self.stylefiles[self.styles.GetString(i)] in sd,sd
        try:
            html=bphtml.applyhtmlstyles(html, sd['styles'])
        except:
            if __debug__:
                f=open("debug.html", "wt")
                f.write(html)
                f.close()
            wx.EndBusyCursor()
            raise
        wx.EndBusyCursor()
        return html

    def OnPrintPreview(self, _):
        wx.GetApp().htmlprinter.PreviewText(self.html, scale=self.scale)

    def OnPrint(self, _):
        wx.GetApp().htmlprinter.PrintText(self.html, scale=self.scale)

    def OnPrinterSetup(self, _):
        wx.GetApp().htmlprinter.PrinterSetup()

    def OnPageSetup(self, _):
        wx.GetApp().htmlprinter.PageSetup()


def htmlify(string):
    return string.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>")

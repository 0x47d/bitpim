### BITPIM
###
### Copyright (C) 2003 Roger Binns <rogerb@rogerbinns.com>
###
### This software is under the Artistic license.
### http://www.opensource.org/licenses/artistic-license.php
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

# GUI
import wx
import wx.grid
import wx.html
import wx.stc

# My imports
import common
import xyaptu
import guihelper

###
###  Enhanced HTML Widget
###

class HTMLWindow(wx.html.HtmlWindow):

    def __init__(self, parent, id):
        wx.html.HtmlWindow.__init__(self, parent, id)
        wx.EVT_KEY_UP(self, self.OnKeyUp)
        self.thetext=""

    def SetPage(self, text):
        self.thetext=text
        wx.html.HtmlWindow.SetPage(self,text)

    def OnKeyUp(self, evt):
        keycode=evt.GetKeyCode()        
        if keycode==ord('S') and evt.ControlDown() and evt.AltDown():
            print "got ctrl alt s"
            vs=ViewSourceFrame(self, self.thetext)
            vs.Show(True)
            evt.Skip()

###
###  View Source Window
###            

class ViewSourceFrame(wx.Frame):
    def __init__(self, parent, text, id=-1):
        wx.Frame.__init__(self, parent, id, "HTML Source")
        stc=wx.stc.StyledTextCtrl(self, -1)
        stc.SetLexer(wx.stc.STC_LEX_HTML)
        stc.SetText(text)
        stc.Colourise(0,-1)


###
### Phonebook entry display (Derived from HTML)
###

class PhoneEntryDetailsView(HTMLWindow):

    def __init__(self, parent, id, stylesfile, layoutfile):
        HTMLWindow.__init__(self, parent, id)
        self.stylesfile=guihelper.getresourcefile("styles.xy")
        self.stylesfilestat=None
        self.pblayoutfile=guihelper.getresourcefile("pblayout.xy")
        self.pblayoutfilestat=None
        self.xcp=None
        self.xcpstyles=None

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
        self.SetPage(self.xcp.xcopywithdns(self.xcpstyles))
        
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

    def OnDataUpdated(self):
        newkeys=self.main._data.keys()
        newkeys.sort()
        oldrows=self.rowkeys
        print oldrows
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
        return 2

    def formatname(self,name):
        # Returns a string of the name in name.
        # Since there can be many fields, we try to make sense of them
        res=""
        res+=name.get("full", "")
        f=name.get("first", "")
        m=name.get("middle", "")
        l=name.get("last", "")
        if len(f) or len(m) or len(l):
            if len(res):
                res+=" | "
            # severe abuse of booleans
            res+=f+(" "*bool(len(f)))
            res+=m+(" "*bool(len(m)))
            res+=l+(" "*bool(len(l)))
        if name.has_key("nickname"):
            res+=" ("+name["nickname"]+")"
        return res

    def GetValue(self, row, col):
        try:
            entry=self.main._data[self.rowkeys[row]]
        except:
            print "bad row", row
            return "<error>"
        if col==0:
            names=entry.get("names", [{'full': '<not set>'}])
            name=names[0]
            return self.formatname(name)
        if col==1:
            numbers=entry.get("numbers", [])
            if len(numbers)==0:
                return ""
            number=numbers[0]
            return number['type']+" : "+number['number']
        assert False, "Bad column "+`col`

    def GetAttr(self, row, col, another):
        print row,col,another
        return [self.evenattr, self.oddattr][row%2]

class PhoneWidget(wx.SplitterWindow):
    """Main phone editing/displaying widget"""
    CURRENTFILEVERSION=2
    def __init__(self, mainwindow, parent, id=-1):
        wx.SplitterWindow.__init__(self, parent, id, style=wx.SP_3D|wx.SP_LIVE_UPDATE)
        self.mainwindow=mainwindow
        self._data={}
        self.groupdict={}
        self.modified=False
        self.table=wx.grid.Grid(self, -1)
        self.dt=PhoneDataTable(self)
        # 1 is GridSelectRows.  The symbol pathologically refused to be defined
        self.table.SetTable(self.dt, False, 1)
        self.table.SetRowLabelSize(0)
        self.table.EnableEditing(False)
        self.table.SetMargins(1,0)
        self.preview=PhoneEntryDetailsView(self, -1, "styles.xy", "pblayout.xy")
        self.preview.ShowEntry({})
        self.SplitVertically(self.table, self.preview, -300)
        wx.EVT_IDLE(self, self.OnIdle)
        wx.grid.EVT_GRID_SELECT_CELL(self, self.OnCellSelect)


    def OnIdle(self, _):
        "We save out changed data"
        if self.modified:
            print "Saving phonebook"
            self.modified=False
            self.populatefs(self.getdata({}))

    def OnCellSelect(self, event):
        row=event.GetRow()
        self.SetPreview(self._data[self.dt.rowkeys[row]]) # bad breaking of abstraction referencing dt!

    def SetPreview(self, entry):
        self.preview.ShowEntry(entry)

    def getdata(self, dict):
        dict['phonebook']=self._data.copy()
        dict['groups']=self.groupdict.copy()
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
            
    def clear(self):
        self._data={}
        self.dt.OnDataUpdated()


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
        common.writeversionindexfile(os.path.join(self.thedir, "index.idx"), d, self.CURRENTFILEVERSION)
        return dict

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
        return dict

    def populate(self, dict):
        self.clear()
        pb=dict['phonebook']
        k=pb.keys()
        k.sort()
        self.clear()
        self._data=pb.copy()
        self.dt.OnDataUpdated()

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


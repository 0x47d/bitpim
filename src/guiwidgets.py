# Part of bitpim

# $Id$

# standard modules
import os
import re
import calendar
import time

# wx modules
from wxPython.grid import *
from wxPython.wx import *
from wxPython.lib.timectrl import *
from wxPython.lib.mixins.listctrl import wxColumnSorterMixin, wxListCtrlAutoWidthMixin
from wxPython.lib.intctrl import *

# my modules
import common
import gui
import calendarcontrol

####
#### A widget for displaying the phone information
####            

# we use a custom table class
class PhoneDataTable(wxPyGridTableBase):

    numbertypetab=( 'Home', 'Home2', 'Office', 'Office2', 'Mobile', 'Mobile2',
                    'Pager', 'Fax', 'Fax2', 'None' )

    typesnames=( 'type1', 'type2', 'type3', 'type4', 'type5' )

    typestypename=wxGRID_VALUE_CHOICE+":"+",".join(numbertypetab)

    groupnames=( 'group', )

    grouptypenamebase=wxGRID_VALUE_CHOICE+":"

    intnames=( 'msgringtone', 'ringtone', 'serial1', 'serial2' )
    
    boolnames=( 'secret', )

    blankentry={ 'name': "", 'group': 0, 'type1': 0, 'type2': 0, 'type3': 0, 'type4': 0, 'type5': 0,
                 'number1': "", 'number2': "", 'number3': "", 'number4': "", 'number5': "",
                 'email1': "", 'email2': "", 'email3': "", 'memo': "", 'msgringtone': 0,
                 'ringtone': 0, 'secret': False, 'serial1': 0, 'serial2': 0, 'url': "",
                 '?offset00f': 0, '?offset028': 0, '?offset111': 0, '?offset20c': 0 }
    
    def __init__(self, mainwindow):
        wxPyGridTableBase.__init__(self)
        self.mainwindow=mainwindow
        self.numrows=0
        self.numcols=0
        self.labels=[] # columns
        self.roworder=[] # rows
        self._data={}
        self.needswrite=False
        self.sequence=0xffff # for new entries we add
        # default groups
        self.groupdict={0: {'name': 'No Group', 'icon': 0}, 1: {'name': 'Family', 'icon': 1},
                        2: {'name': 'Friends', 'icon': 2}, 3: {'name': 'Colleagues', 'icon': 3},
                        4: {'name': 'Business', 'icon': 4}, 5: {'name': 'School', 'icon': 5}, }
        self.buildgrouptypename(self.groupdict)
 
    def OnIdle(self, _):
        if self.needswrite:
            print "updating filesystem for phonebook"
            self.populatefs(self.getdata({}))
            self.needswrite=False

    def getdata(self, dict):
        dict['phonebook']=self._data.copy()
        dict['groups']=self.groupdict.copy()
        return dict

    def setstandardlabels(self):
        # get some nice columns setup first
        self.addcolumn('name')
        self.addcolumn('group')
        for i in range(1,6):
            self.addcolumn('type'+`i`)
            self.addcolumn('number'+`i`)

    def addcolumn(self, name):
        self.labels.append(name)
        msg=wxGridTableMessage(self, wxGRIDTABLE_NOTIFY_COLS_APPENDED, 1)
        self.GetView().ProcessTableMessage(msg)

    def clear(self):
        # we never clear out columns
        oldr=self.numrows
        self.numrows=0
        msg=wxGridTableMessage(self, wxGRIDTABLE_NOTIFY_ROWS_DELETED, 0, oldr)
        if oldr:
            self.GetView().ProcessTableMessage(msg)

    def OnDelete(self, rows):
        # we do them in reverse order so that we don't have to worry about row numbers
        # changing under us
        print "delete - rows chosen=",rows
        print "keys b4", self._data.keys()
        rows.sort()
        rows.reverse()
        for row in rows:
            del self._data[self.roworder[row]]
            del self.roworder[row]
            self.numrows-=1
            msg=wxGridTableMessage(self, wxGRIDTABLE_NOTIFY_ROWS_DELETED, row, 1)
            self.GetView().ProcessTableMessage(msg)
        if len(rows):
            self.needswrite=True
        print "keys after", self._data.keys()

    def OnAdd(self, currow):
        print "add - keys b4", self._data.keys()
        self.sequence+=1
        while self.sequence in self._data:
            self.sequence+=1
        self._data[self.sequence]=self.blankentry.copy()
        if currow+1==self.numrows:
            msg=wxGridTableMessage(self, wxGRIDTABLE_NOTIFY_ROWS_APPENDED, 1)
            self.roworder.append(self.sequence)
        else:
            msg=wxGridTableMessage(self, wxGRIDTABLE_NOTIFY_ROWS_INSERTED, currow+1, 1)
            self.roworder[currow+1:currow+1]=[self.sequence]
        self.numrows+=1
        self.GetView().ProcessTableMessage(msg)
        self.needswrite=True
        print "keys after", self._data.keys()

    def getcolumn(self,name):
        if len(self.labels)==0:
            self.setstandardlabels()
        if name not in self.labels:
            self.addcolumn(name)
        return self.labels.index(name)

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
        f=open(os.path.join(self.thedir, "index.idx"), "wb")
        f.write("result['phonebook']="+`dict['phonebook']`+"\n")
        if dict.has_key('groups'):
            f.write("result['groups']="+`dict['groups']`+"\n")
        f.close()
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
            execfile(os.path.join(self.thedir, "index.idx"), d, d)
            dict.update(d['result'])
        else:
            dict['phonebook']={}
            dict['groups']=self.groupdict
        return dict

    def populate(self, dict):
        self.clear()
        pb=dict['phonebook']
        k=pb.keys()
        k.sort()
        self._data=pb.copy()
        self.roworder=k
        oldrows=self.numrows
        self.numrows=len(k)
        msg=None
        if self.numrows>oldrows:
            msg=wxGridTableMessage(self, wxGRIDTABLE_NOTIFY_ROWS_APPENDED, self.numrows-oldrows)
        elif self.numrows<oldrows:
            msg=wxGridTableMessage(self, wxGRIDTABLE_NOTIFY_ROWS_DELETED, self.numrows, oldrows-self.numrows)
        if msg is not None:
            self.GetView().ProcessTableMessage(msg)

        # get list of all columns
        cols=[]
        for e in pb:
            keys=pb[e].keys()
            for k in keys:
                if k not in cols:
                    cols.append(k)
        # now order the columns
        cols.sort()
        k2=[]
        for c in cols:
            if c[0]=='?':
                k2.append(c)
            else:
                self.getcolumn(c)
        k2.sort()
        for c in k2:
            self.getcolumn(c)

        self.GetView().FitInside()

        if dict.has_key('groups'):
            self.buildgrouptypename(dict['groups'])

    def buildgrouptypename(self, dict):
        self.grouptypename=self.grouptypenamebase
        keys=dict.keys()
        keys.sort()
        self.grouptypename+=(",".join([dict[k]['name'] for k in keys]))
        self.groupdict=dict.copy()
                    
    def GetNumberRows(self):
        return len(self.roworder)

    def GetNumberCols(self):
        return len(self.labels)

    def IsEmptyCell(self, row, col):
        return False

    def GetValue(self, row, col):
        celldata=self._data[self.roworder[row]][self.labels[col]]
        try:
            if self.labels[col] in self.typesnames:
                return self.numbertypetab[ celldata ]
            elif self.labels[col] in self.groupnames:
                if self.groupdict.has_key( celldata ):
                    return self.groupdict[celldata]['name']
                return "Group #"+`celldata`
            return celldata
        except:
            print "bad request", row, self.labels[col]
            return ""

    def GetTypeName(self, row, col):
        # print "GetTypeName",row,col
        if self.labels[col] in self.typesnames:
            return self.typestypename
        elif self.labels[col] in self.intnames or self.labels[col][0]=='?':
            return wxGRID_VALUE_NUMBER
        elif self.labels[col] in self.boolnames:
            return wxGRID_VALUE_BOOL
        elif self.labels[col] in self.groupnames:
            return self.grouptypename
        return wxGRID_VALUE_STRING

    def SetValue(self, row, col, value):
        if self.labels[col] in self.typesnames:
            for i in range(0,len(self.numbertypetab)):
                if value==self.numbertypetab[i]:
                    value=i
                    break
        elif self.labels[col] in self.groupnames:
            for i in self.groupdict:
                if value==self.groupdict[i]['name']:
                    value=i
                    break
        print "SetValue",row,col,`value`
        self._data[self.roworder[row]][self.labels[col]]=value
        if self.labels[col]=='name':
            self.GetView().GetGridRowLabelWindow().Refresh()
        self.needswrite=1

    def GetColLabelValue(self, col):
        return self.labels[col]

    def GetRowLabelValue(self, row):
        return self._data[self.roworder[row]]['name']

    def CanGetValueAs(self, row, col, typename):
        # print "CanGetValueAs", row, col, typename
        return True

    def CanSetValueAs(self, row, col, typename):
        return self.CanGetValueAs(row, col, typename)

class PhoneGrid(wxGrid):
    # The various FitInside calls are because wxGrid doesn't update its scrollbars without
    # them.  See the wxPython FAQ
    def __init__(self, mainwindow, parent, id=-1, *args, **kwargs):
        apply(wxGrid.__init__, (self,parent,id)+args, kwargs)
        self.mainwindow=mainwindow
        self.table=PhoneDataTable(mainwindow)
        self.SetTable( self.table, True)
        self.table.setstandardlabels()
        # self.AutoSizeColumns(True)
        # self.AutoSize()
        EVT_IDLE(self, self.table.OnIdle)
        EVT_GRID_CELL_LEFT_DCLICK(self, self.OnLeftDClick) # see the demo
        EVT_KEY_DOWN(self, self.OnKeyDown)

    # we move to cell right on enter - pretty much copied from the demo
    def OnKeyDown(self, event):
        if event.KeyCode()!=WXK_RETURN:
            event.Skip()
            return
        if event.ControlDown():
            event.Skip()
            return

        self.DisableCellEditControl()
        success=self.MoveCursorRight(event.ShiftDown())
        # move to next row maybe?

    def OnLeftDClick(self, _):
        if self.CanEnableCellControl():
            self.EnableCellEditControl()

    def OnDelete(self, _=None):
        print "delete - selected cells=", self.GetSelectedCells()
        rows=self.GetSelectedRows()
        self.table.OnDelete(rows)

    def OnAdd(self, _=None):
        print "add, cursor at row", self.GetGridCursorRow()
        self.table.OnAdd(self.GetGridCursorRow())

    def clear(self):
        self.table.clear()

    def getdata(self, dict):
        self.table.getdata(dict)

    def populatefs(self, dict):
        return self.table.populatefs(dict)
    
    def populate(self, dict):
        return self.table.populate(dict)

    def getfromfs(self, dict):
        return self.table.getfromfs(dict)

####
#### A simple text widget that does nice pretty logging.
####        

    
class LogWindow(wxPanel):
    def __init__(self, parent):
        wxPanel.__init__(self,parent, -1, style=wxNO_FULL_REPAINT_ON_RESIZE)
        # have to use rich2 otherwise fixed width font isn't used on windows
        self.tb=wxTextCtrl(self, 1, style=wxTE_MULTILINE| wxTE_RICH2|wxTE_READONLY|wxNO_FULL_REPAINT_ON_RESIZE|wxTE_DONTWRAP  )
        f=wxFont(10, wxMODERN, wxNORMAL, wxNORMAL )
        ta=wxTextAttr(font=f)
        self.tb.SetDefaultStyle(ta)
        self.sizer=wxBoxSizer(wxVERTICAL)
        self.sizer.Add(self.tb, 1, wxEXPAND)
        self.SetSizer(self.sizer)
        self.SetAutoLayout(True)
        self.sizer.Fit(self)
        EVT_IDLE(self, self.OnIdle)
        self.outstandingtext=""


    def OnIdle(self,_):
        if len(self.outstandingtext):
            self.tb.AppendText(self.outstandingtext)
            self.outstandingtext=""

    def log(self, str):
        self.outstandingtext+=str+"\r\n"

    def logdata(self, str, data):
        self.log("%s - Data %d bytes" % (str, len(data),))
        self.log(common.datatohexstring(data))


###
### Dialog asking what you want to sync
###

class GetPhoneDialog(wxDialog):
    strings= ('Version Information', 'PhoneBook', 'Calendar', 'Wallpaper', 'Ringtone')
    NOTREQUESTED=0
    MERGE=1
    OVERWRITE=2
    
    def __init__(self, frame, title, id=-1):
        wxDialog.__init__(self, frame, id, title,
                          style=wxCAPTION|wxSYSTEM_MENU|wxDEFAULT_DIALOG_STYLE)
        gs=wxFlexGridSizer(6, 4,5 ,10)
        gs.AddGrowableCol(1)
        gs.AddMany( [
            (wxStaticText(self, -1, "Get"), 0, wxEXPAND),
            (wxStaticText(self, -1, "Type"), 0, wxEXPAND),
            (wxStaticText(self, -1, "Merge"), 0, wxEXPAND),
            (wxStaticText(self, -1, "Overwrite"), 0, wxEXPAND)
            ])
        self.cb=[]
        self.rb=[]
        for i in self.strings:
            self.cb.append(wxCheckBox(self,-1, ""))
            if len(self.cb)>1: self.cb[-1].SetValue(True) # info not requested by default
            gs.Add(self.cb[-1], 0, wxEXPAND)
            gs.Add(wxStaticText(self,-1,i), 0, wxEXPAND|wxALIGN_CENTER_VERTICAL) # align needed for gtk
            self.rb.append( [wxRadioButton(self, -1, "", style=wxRB_GROUP),
                             wxRadioButton(self, -1, "")])
            gs.Add(self.rb[-1][0], 0, wxEXPAND|wxALIGN_CENTRE)
            gs.Add(self.rb[-1][1], 0, wxEXPAND|wxALIGN_CENTRE)
            # merge not supported
            self.rb[-1][0].Enable(False)
            self.rb[-1][0].SetValue(False)
            self.rb[-1][1].SetValue(True)

        bs=wxBoxSizer(wxVERTICAL)
        bs.Add(gs, 0, wxEXPAND|wxALL, 10)
        bs.Add(wxStaticLine(self, -1), 0, wxEXPAND|wxTOP|wxBOTTOM, 7)
        
        but=self.CreateButtonSizer(wxOK|wxCANCEL|wxHELP)
        bs.Add(but, 0, wxEXPAND|wxALL, 10)
        
        self.SetSizer(bs)
        self.SetAutoLayout(True)
        bs.Fit(self)

    def _setting(self, index):
        if not self.cb[index].GetValue(): return self.NOTREQUESTED
        if self.rb[index][0].GetValue(): return self. MERGE
        return self.OVERWRITE

    def GetInformationSetting(self):
        return self._setting(0)

    def GetPhoneBookSetting(self):
        return self._setting(1)

    def GetCalendarSetting(self):
        return self._setting(2)

    def GetWallpaperSetting(self):
        return self._setting(3)

    def GetRingtoneSetting(self):
        return self._setting(4)

class SendPhoneDialog(GetPhoneDialog):
    def __init__(self, frame, title, id=-1):
        GetPhoneDialog.__init__(self, frame, title, id)
        # disable the information line
        self.cb[0].SetValue(False)
        self.cb[0].Enable(False)
        self.rb[0][0].Enable(False)
        self.rb[0][1].Enable(False)
        # turn all checkboxes off by default for writing
        # we want user to explicitly write stuff they changed
        for i in self.cb:
            i.SetValue(False)
        # We do support merge for wallpaper and ringtone
        self.rb[3][0].Enable(True)
        self.rb[4][0].Enable(True)
        

###
###  The master config dialog
###

class ConfigDialog(wxDialog):
    setme="<setme>"
    def __init__(self, mainwindow, frame, title="BitPim Settings", id=-1):
        wxDialog.__init__(self, frame, id, title,
                          style=wxCAPTION|wxSYSTEM_MENU|wxDEFAULT_DIALOG_STYLE)
        self.mw=mainwindow
        gs=wxFlexGridSizer(2, 2,  5 ,10)
        gs.AddGrowableCol(1)

        gs.Add( wxStaticText(self, -1, "Disk storage"), 0, wxEXPAND)
        self.diskbox=wxTextCtrl(self, -1, self.setme)
        gs.Add( self.diskbox, 0, wxEXPAND)

        gs.Add( wxStaticText(self, -1, "Com Port"), 0, wxEXPAND)
        self.commbox=wxTextCtrl(self, -1, self.setme)
        gs.Add( self.commbox, 0, wxEXPAND)

        bs=wxBoxSizer(wxVERTICAL)
        bs.Add(gs, 0, wxEXPAND|wxALL, 10)
        bs.Add(wxStaticLine(self, -1), 0, wxEXPAND|wxTOP|wxBOTTOM, 7)
        
        but=self.CreateButtonSizer(wxOK|wxCANCEL|wxHELP)
        bs.Add(but, 0, wxEXPAND|wxALL, 10)
        
        self.SetSizer(bs)
        self.SetAutoLayout(True)
        bs.Fit(self)

    def setfromconfig(self):
        if len(self.mw.config.Read("path", "")):
            self.diskbox.SetValue(self.mw.config.Read("path", ""))
        if len(self.mw.config.Read("lgvx4400port")):
            self.commbox.SetValue(self.mw.config.Read("lgvx4400port", ""))

    def setdefaults(self):
        if self.diskbox.GetValue()==self.setme:
            if gui.IsMSWindows(): # we want subdir of my documents on windows
                    # nice and painful
                    import _winreg
                    x=_winreg.ConnectRegistry(None, _winreg.HKEY_CURRENT_USER)
                    y=_winreg.OpenKey(x, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
                    str=_winreg.QueryValueEx(y, "Personal")[0]
                    _winreg.CloseKey(y)
                    _winreg.CloseKey(x)
                    path=os.path.join(str, "bitpim")
            else:
                path=os.path.expanduser("~/.bitpim-files")
            self.diskbox.SetValue(path)
        if self.commbox.GetValue()==self.setme:
            if gui.IsMSWindows(): # we want subdir of my documents on windows
                comm="com4"
            else:
                comm="/dev/usb/ttyUSB0"
            self.commbox.SetValue(comm)

    def updatevariables(self):
        path=self.diskbox.GetValue()
        self.mw.configpath=path
        self.mw.ringerpath=self._fixup(os.path.join(path, "ringer"))
        self.mw.wallpaperpath=self._fixup(os.path.join(path, "wallpaper"))
        self.mw.phonebookpath=self._fixup(os.path.join(path, "phonebook"))
        self.mw.calendarpath=self._fixup(os.path.join(path, "calendar"))
        self.mw.config.Write("path", path)
        self.mw.commportsetting=self.commbox.GetValue()
        self.mw.config.Write("lgvx4400port", self.mw.commportsetting)
        if self.mw.wt is not None:
            self.mw.wt.commphone=None # cause it to be recreated

    def _fixup(self, path):
        # os.path.join screws up adding root directory of a drive to
        # a directory.  eg join("c:\", "foo") gives "c:\\foo" whch
        # is invalid.  This function fixes that
        if len(path)>=3:
            if path[1]==':' and path[2]=='\\' and path[3]=='\\':
                return path[0:2]+path[3:]
        return path
        
    def needconfig(self):
        self.setfromconfig()
        if self.diskbox.GetValue()==self.setme or \
           self.commbox.GetValue()==self.setme:
            return True
        return False

    def ShowModal(self):
        self.setfromconfig()
        self.setdefaults()
        ec=wxDialog.ShowModal(self)
        if ec==wxID_OK:
            self.updatevariables()
        return ec




###
### File viewer
###

class MyFileDropTarget(wxFileDropTarget):
    def __init__(self, target):
        wxFileDropTarget.__init__(self)
        self.target=target
        
    def OnDropFiles(self, x, y, filenames):
        return self.target.OnDropFiles(x,y,filenames)

class FileView(wxListCtrl, wxListCtrlAutoWidthMixin):

    # File we should ignore
    skiplist= ( 'desktop.ini', 'thumbs.db', 'zbthumbnail.info' )
    
    def __init__(self, mainwindow, parent, id=-1, style=wxLC_REPORT|wxLC_SINGLE_SEL):
        wxListCtrl.__init__(self, parent, id, style=style)
        wxListCtrlAutoWidthMixin.__init__(self)
        self.droptarget=MyFileDropTarget(self)
        self.SetDropTarget(self.droptarget)
        self.mainwindow=mainwindow
        self.thedir=None
        self.wildcard="I forgot to set wildcard in derived class|*"
        self.maxlen=255
        if (style&wxLC_REPORT)==wxLC_REPORT or gui.HasFullyFunctionalListView():
            # some can't do report and icon style
            self.InsertColumn(0, "Name")
            self.InsertColumn(1, "Bytes", wxLIST_FORMAT_RIGHT)
            
            self.SetColumnWidth(0, 200)
            
        self.menu=wxMenu()
        self.menu.Append(gui.ID_FV_OPEN, "Open")
        self.menu.AppendSeparator()
        self.menu.Append(gui.ID_FV_DELETE, "Delete")
        self.menu.AppendSeparator()
        self.menu.Append(gui.ID_FV_RENAME, "Rename")
        self.menu.Append(gui.ID_FV_REFRESH, "Refresh")
        self.menu.Append(gui.ID_FV_PROPERTIES, "Properties")

        self.addfilemenu=wxMenu()
        self.addfilemenu.Append(gui.ID_FV_ADD, "Add ...")
        self.addfilemenu.Append(gui.ID_FV_REFRESH, "Refresh")

        EVT_MENU(self.menu, gui.ID_FV_REFRESH, self.OnRefresh)
        EVT_MENU(self.addfilemenu, gui.ID_FV_REFRESH, self.OnRefresh)
        EVT_MENU(self.addfilemenu, gui.ID_FV_ADD, self.OnAdd)
        EVT_MENU(self.menu, gui.ID_FV_OPEN, self.OnLaunch)
        EVT_MENU(self.menu, gui.ID_FV_DELETE, self.OnDelete)
        EVT_MENU(self.menu, gui.ID_FV_PROPERTIES, self.OnProperties)

        EVT_LEFT_DCLICK(self, self.OnLaunch)
        # copied from the demo - much voodoo
        EVT_LIST_ITEM_SELECTED(self, -1, self.OnItemActivated)
        EVT_RIGHT_DOWN(self, self.OnRightDown)
        EVT_COMMAND_RIGHT_CLICK(self, id, self.OnRightClick)
        EVT_RIGHT_UP(self, self.OnRightClick)

        EVT_KEY_DOWN(self, self.OnKeyDown)
        

    def OnRightDown(self,event):
        item,flags=self.HitTest(wxPoint(event.GetX(), event.GetY()))
        if flags&wxLIST_HITTEST_ONITEM:
            self.selecteditem=item
            self.SetItemState(item, wxLIST_STATE_SELECTED, wxLIST_STATE_SELECTED)
        else:
            self.selecteditem=-1
        
    def OnRightClick(self,event):
        if self.selecteditem>=0:
            self.PopupMenu(self.menu, event.GetPosition())
        else:
            self.PopupMenu(self.addfilemenu, event.GetPosition())

    def OnKeyDown(self,event):
        if event.GetKeyCode()==WXK_DELETE:
            self.OnDelete(event)
            return
        event.Skip()

    def OnItemActivated(self,event):
        self.selecteditem=event.m_itemIndex
        
    def OnLaunch(self,_=None):
        name=self.GetItemText(self.selecteditem)
        ext=name[name.rfind('.')+1:]
        type=wxTheMimeTypesManager.GetFileTypeFromExtension(ext)
        cmd=type.GetOpenCommand(os.path.join(self.thedir, name))
        if cmd is None or len(cmd)==0:
            dlg=wxMessageDialog(self, "You don't have any programs defined to open ."+ext+" files",
                                "Unable to open", style=wxOK|wxICON_INFORMATION)
            dlg.ShowModal()
            dlg.Destroy()
        else:
            try:
                wxExecute(cmd)
            except:
                dlg=wxMessageDialog(self, "Unable to execute '"+cmd+"'",
                                    "Open failed", style=wxOK|wxICON_ERROR)
                dlg.ShowModal()
                dlg.Destroy()
                

    def OnDropFiles(self, _, dummy, filenames):
        # There is a bug in that the most recently created tab
        # in the notebook that accepts filedrop receives these
        # files, not the most visible one.  We find the currently
        # viewed tab in the notebook and send the files there
        target=self # fallback
        t=self.mainwindow.nb.GetPage(self.mainwindow.nb.GetSelection())
        if isinstance(t, FileView):
            print "changing target in dragndrop"
            target=t
        for f in filenames:
            target.OnAddFile(f)

    def OnAdd(self, _=None):
        dlg=wxFileDialog(self, "Choose files", style=wxOPEN|wxMULTIPLE, wildcard=self.wildcard)
        if dlg.ShowModal()==wxID_OK:
            for file in dlg.GetPaths():
                self.OnAddFile(file)
        dlg.Destroy()

    def OnAddFile(self,_):
        raise Exception("not implemented")

    def OnRefresh(self, _=None):
        result={}
        self.getfromfs(result)
        self.populate(result)

    def OnDelete(self,_):
        name=self.GetItemText(self.selecteditem)
        os.remove(os.path.join(self.thedir, name))
        self.OnRefresh()

    def OnProperties(self,_):
        raise Exception("not implemented")
    
    def getfromfs(self,_):
        raise Exception("not implemented")
    
    def populate(self,_):
        raise Exception("not implemented")

    def seticonview(self):
        self.SetSingleStyle(wxLC_REPORT, False)
        self.SetSingleStyle(wxLC_ICON, True)

    def setlistview(self):
        self.SetSingleStyle(wxLC_ICON, False)
        self.SetSingleStyle(wxLC_REPORT, True)

    def genericpopulatefs(self, dict, key, indexkey):
        try:
            os.makedirs(self.thedir)
        except:
            pass
        if not os.path.isdir(self.thedir):
            raise Exception("Bad directory for "+key+" '"+self.thedir+"'")
        for f in os.listdir(self.thedir):
            # delete them all except windows magic ones which we ignore
            if f.lower() in self.skiplist:
                os.remove(os.path.join(self.thedir, f))
        d=dict[key]
        for i in d:
            f=open(os.path.join(self.thedir, i), "wb")
            f.write(d[i])
            f.close()
        d=dict[indexkey]
        f=open(os.path.join(self.thedir, "index.idx"), "wb")
        f.write("result['"+indexkey+"']="+`d`)
        f.close()
        return dict

    def genericgetfromfs(self, result, key, indexkey):
        try:
            os.makedirs(self.thedir)
        except:
            pass
        if not os.path.isdir(self.thedir):
            raise Exception("Bad directory for "+key+" '"+self.thedir+"'")
        dict={}
        for file in os.listdir(self.thedir):
            if file=='index.idx':
                d={}
                d['result']={}
                execfile(os.path.join(self.thedir, file), d, d)
                result.update(d['result'])
            elif file.lower() in self.skiplist:
                # ignore windows detritus
                continue
            else:
                f=open(os.path.join(self.thedir, file), "rb")
                data=f.read()
                f.close()
                dict[file]=data
        result[key]=dict
        if indexkey not in result:
            result[indexkey]={}
        return result

    def getshortenedbasename(self, filename, newext=''):
        filename=basename(filename).lower()
        if len(newext):
            filename=stripext(filename)+'.'+newext
        if len(filename)>self.maxlen:
            chop=len(filename)-self.maxlen
            filename=stripext(filename)[:-chop]+'.'+getext(filename)
        return os.path.join(self.thedir, filename)
        

###
###  Midi
###

class RingerView(FileView):
    def __init__(self, mainwindow, parent, id=-1):
        FileView.__init__(self, mainwindow, parent, id)
        self.InsertColumn(2, "Length")
        self.InsertColumn(3, "Index")
        self.InsertColumn(4, "Description")
        il=wxImageList(32,32)
        il.Add(self.mainwindow.getbitmap("ringer"))
        self.AssignImageList(il, wxIMAGE_LIST_NORMAL)
        self._data={}
        self._data['ringtone']={}
        self._data['ringtone-index']={}

        self.wildcard="MIDI files (*.mid)|*.mid"
        self.maxlen=19

    def getdata(self, dict):
        dict.update(self._data)
        return dict

    def OnAddFile(self, file):
        self.thedir=self.mainwindow.ringerpath
        target=self.getshortenedbasename(file, 'mid')
        if target==None: return # user didn't want to
        f=open(file, "rb")
        contents=f.read()
        f.close()
        if len(contents)>=65534:
            raise Exception(file+" is too big at "+`len(contents)`+ " bytes.  Max size is 64k")
        f=open(target, "wb")
        f.write(contents)
        f.close()
        self.OnRefresh()

    def populatefs(self, dict):
        self.thedir=self.mainwindow.ringerpath
        return self.genericpopulatefs(dict, 'ringtone', 'ringtone-index')
            
    def populate(self, dict):
        self.DeleteAllItems()
        self._data={}
        self._data['ringtone']=dict['ringtone'].copy()
        self._data['ringtone-index']=dict['ringtone-index'].copy()
        count=0
        keys=dict['ringtone'].keys()
        keys.sort()
        for i in keys:
            item={}
            item['name']=i
            item['data']=dict['ringtone'][i]
            item['index']=-1
            for ii in dict['ringtone-index']:
                if dict['ringtone-index'][ii]==i:
                    item['index']=ii
                    break
            self.InsertImageStringItem(count, item['name'], 0)
            self.SetStringItem(count, 0, item['name'])
            self.SetStringItem(count, 1, `len(item['data'])`)
            self.SetStringItem(count, 2, "1 second :-)")
            self.SetStringItem(count, 3, `item['index']`)
            self.SetStringItem(count, 4, "Midi file")
            count+=1

    def getfromfs(self, result):
        self.thedir=self.mainwindow.ringerpath
        return self.genericgetfromfs(result, "ringtone", 'ringtone-index')
        
###
###  Bitmaps
###

class WallpaperView(FileView):
    def __init__(self, mainwindow, parent, id=-1):
        FileView.__init__(self, mainwindow, parent, id, style=wxLC_ICON|wxLC_SINGLE_SEL)
        if gui.HasFullyFunctionalListView():
            self.InsertColumn(2, "Size")
            self.InsertColumn(3, "Index")
        self._data={}
        self._data['wallpaper']={}
        self._data['wallpaper-index']={}
        self.maxlen=19
        self.wildcard="Image files|*.bmp;*.jpg;*.jpeg;*.png;*.gif;*.pnm;*.tiff;*.ico"
        self.usewidth=120
        self.useheight=98

    def getdata(self,dict):
        dict.update(self._data)
        return dict

    def populate(self, dict):
        self.DeleteAllItems()
        self._data={}
        self._data['wallpaper']=dict['wallpaper'].copy()
        self._data['wallpaper-index']=dict['wallpaper-index'].copy()
        il=wxImageList(self.usewidth,self.useheight)
        self.AssignImageList(il, wxIMAGE_LIST_NORMAL)
        count=0
        keys=dict['wallpaper'].keys()
        keys.sort()
        for i in keys:
            item={}
            item['name']=i
            item['data']=dict['wallpaper'][i]
            item['index']=-1
            for ii in dict['wallpaper-index']:
                if dict['wallpaper-index'][ii]==i:
                    item['index']=ii
                    break
            # ImageList barfs big time when adding bmps that came from
            # gifs
            file=os.path.join(self.mainwindow.wallpaperpath, i)
            image=wxImage(file)
            width=min(image.GetWidth(), self.usewidth)
            height=min(image.GetHeight(), self.useheight)
            img=image.GetSubImage(wxRect(0,0,width,height))
            if width!=self.usewidth or height!=self.useheight:
                b=wxEmptyBitmap(self.usewidth, self.useheight)
                mdc=wxMemoryDC()
                mdc.SelectObject(b)
                mdc.Clear()
                mdc.DrawBitmap(img.ConvertToBitmap(), 0, 0, True)
                mdc.SelectObject(wxNullBitmap)
                bitmap=b
            else:
                # bitmap=wxBitmapFromImage(img)
                bitmap=img.ConvertToBitmap()
            pos=-1
            try: pos=il.Add(bitmap)
            except: pass
            if pos<0:  # sadly they throw up a dialog as well
                dlg=wxMessageDialog(self, "Failed to add to imagelist image in '"+file+"'",
                                "Imagelist got upset", style=wxOK|wxICON_ERROR)
                dlg.ShowModal()
                il.Add(wxNullBitmap)
            self.InsertImageStringItem(count, item['name'], count)
            if gui.HasFullyFunctionalListView():
                self.SetStringItem(count, 0, item['name'])
                self.SetStringItem(count, 1, `len(item['data'])`)
                self.SetStringItem(count, 2, "%d x %d" % (image.GetWidth(), image.GetHeight()))
                self.SetStringItem(count, 3, `item['index']`)
            image.Destroy()
            count+=1

    def OnAddFile(self, file):
        self.thedir=self.mainwindow.wallpaperpath
        target=self.getshortenedbasename(file, 'bmp')
        if target==None: return # user didn't want to
        img=wxImage(file)
        if not img.Ok():
            dlg=wxMessageDialog(self, "Failed to understand the image in '"+file+"'",
                                "Image not understood", style=wxOK|wxICON_ERROR)
            dlg.ShowModal()
            return
        obj=img
        # if image is more than 20% bigger or 60% smaller than screen, resize
        if img.GetWidth()>self.usewidth*120/100 or \
           img.GetHeight()>self.useheight*120/100 or \
           img.GetWidth()<self.usewidth*60/100 or \
           img.GetHeight()<self.useheight*60/100:
            bitmap=wxEmptyBitmap(self.usewidth, self.useheight)
            mdc=wxMemoryDC()
            mdc.SelectObject(bitmap)
            # scale the source.  we use int arithmetic with 10000 being 1.000
            sfactorw=self.usewidth*10000/img.GetWidth()
            sfactorh=self.useheight*10000/img.GetHeight()
            sfactor=min(sfactorw,sfactorh) # preserve aspect ratio
            newwidth=img.GetWidth()*sfactor/10000
            newheight=img.GetHeight()*sfactor/10000
            self.mainwindow.OnLog("Resizing %s from %dx%d to %dx%d" % (target, img.GetWidth(),
                                                            img.GetHeight(), newwidth,
                                                            newheight))
            img.Rescale(newwidth, newheight)
            # figure where to place image to centre it
            posx=self.usewidth-(self.usewidth+newwidth)/2
            posy=self.useheight-(self.useheight+newheight)/2
            # background fill in white
            mdc.Clear()
            mdc.DrawBitmap(img.ConvertToBitmap(), posx, posy, True)
            obj=bitmap
        if not obj.SaveFile(target, wxBITMAP_TYPE_BMP):
            os.remove(target)
            dlg=wxMessageDialog(self, "Failed to convert the image in '"+file+"'",
                                "Image not converted", style=wxOK|wxICON_ERROR)
            dlg.ShowModal()
            return
            
        self.OnRefresh()

    def populatefs(self, dict):
        self.thedir=self.mainwindow.wallpaperpath
        return self.genericpopulatefs(dict, 'wallpaper', 'wallpaper-index')

    def getfromfs(self, result):
        self.thedir=self.mainwindow.wallpaperpath
        return self.genericgetfromfs(result, 'wallpaper', 'wallpaper-index')

def basename(name):
    if name.rfind('\\')>=0 or name.rfind('/')>=0:
        pos=max(name.rfind('\\'), name.rfind('/'))
        name=name[pos+1:]
    return name

def stripext(name):
    if name.rfind('.')>=0:
        name=name[:name.rfind('.')]
    return name

def getext(name):
    if name.rfind('.')>=0:
        return name[name.rfind('.')+1:]
    return ''

###
###  Calendar
###

class Calendar(calendarcontrol.Calendar):
    def __init__(self, mainwindow, parent, id=-1):
        self.mainwindow=mainwindow
        self.entrycache={}
        self.entries={}
        self.repeating=[]  # nb this is stored unsorted
        self._data={}
        calendarcontrol.Calendar.__init__(self, parent, rows=5, id=id)
        self.dialog=DayViewDialog(self, self)

    def getdata(self, dict):
        # Return underlying calendar data in bitpim format
        dict['calendar']=self._data
        return dict

    def getentrydata(self, year, month, day):
        # return the entry objects for corresponding date
        res=self.entrycache.get( (year,month,day), None)
        if res is not None:
            return res
        dayofweek=calendar.weekday(year, month, day)
        dayofweek=(dayofweek+1)%7 # normalize to sunday == 0
        res=[]
        # find non-repeating entries
        fixed=self.entries.get((year,month,day), [])
        res.extend(fixed)
        # now find repeating entries
        repeats=[]
        for i in self.repeating:
            y,m,d=i['start'][0:3]
            if year<y or (year<=y and month<m) or (year<=y and month<=m and day<d):
                continue # we are before this entry
            # look in exception list            
            if (year,month,day) in i.get('exceptions', ()):
                continue # yup, so ignore
            repeating=i['repeat']
            if repeating=='daily':
                repeats.append(i)
                continue
            if repeating=='monfri':
                if dayofweek>0 and dayofweek<6:
                    repeats.append(i)
                continue
            if repeating=='weekly':
                if i['dayofweek']==dayofweek:
                    repeats.append(i)
                continue
            if repeating=='monthly':
                if day==i['start'][2]:
                    repeats.append(i)
                continue
            if repeating=='yearly':
                if day==i['start'][2] and month==i['start'][1]:
                    repeats.append(i)
                continue
            assert False, "Unknown repeat type \""+repeating+"\""

        res.extend(repeats)
        self.entrycache[(year,month,day)] = res
        return res
        
        
    def OnGetEntries(self, year, month, day):
        # return pretty printed sorted entries for date
        res=[(i['start'][3], i['start'][4], i['description']) for i in self.getentrydata(year, month,day)]
        res.sort()
        return res

    def OnEdit(self, year, month, day):
        self.dialog.setdate(year, month, day)
        self.dialog.Show(True)
            
    def populate(self, dict):
        self._data=dict['calendar']
        self.entrycache={}
        self.entries={}
        self.repeating=[]

        for entry in self._data:
            entry=self._data[entry]
            y,m,d,h,min=entry['start']
            if entry['repeat'] is None:
                if not self.entries.has_key( (y,m,d) ): self.entries[(y,m,d)]=[]
                self.entries[(y,m,d)].append(entry)
                continue
            if entry['repeat']=='weekly':
                entry['dayofweek']=(calendar.weekday(y,m,d)+1)%7
            self.repeating.append(entry)

        self.RefreshAllEntries()

    def populatefs(self, dict):
        self.thedir=self.mainwindow.calendarpath
        try:
            os.makedirs(self.thedir)
        except:
            pass
        if not os.path.isdir(self.thedir):
            raise Exception("Bad directory for calendar '"+self.thedir+"'")
        for f in os.listdir(self.thedir):
            # delete them all!
            os.remove(os.path.join(self.thedir, f))
        f=open(os.path.join(self.thedir, "index.idx"), "wb")
        f.write("result['calendar']="+`dict['calendar']`+"\n")
        f.close()
        return dict

    def getfromfs(self, dict):
        self.thedir=self.mainwindow.calendarpath
        try:
            os.makedirs(self.thedir)
        except:
            pass
        if not os.path.isdir(self.thedir):
            raise Exception("Bad directory for calendar '"+self.thedir+"'")
        if os.path.exists(os.path.join(self.thedir, "index.idx")):
            d={'result': {}}
            execfile(os.path.join(self.thedir, "index.idx"), d, d)
            dict.update(d['result'])
        else:
            dict['calendar']={}
        return dict


class DayViewDialog(wxDialog):
    ID_PREV=1
    ID_NEXT=2
    ID_ADD=3
    ID_DELETE=4
    ID_CLOSE=5
    ID_LISTBOX=6
    ID_START=7
    ID_END=8
    ID_REPEAT=9
    # 10 is used by something else
    ID_SAVE=11
    ID_HELP=12
    ID_REVERT=13
    
    def __init__(self, parent, calendarwidget, id=-1, title="Edit Calendar"):
        self.cw=calendarwidget
        wxDialog.__init__(self, parent, id, title, style=wxDEFAULT_DIALOG_STYLE)

        # overall container
        vbs=wxBoxSizer(wxVERTICAL)
        
        prev=wxButton(self, self.ID_PREV, "<", style=wxBU_EXACTFIT)
        next=wxButton(self, self.ID_NEXT, ">", style=wxBU_EXACTFIT)
        self.title=wxStaticText(self, -1, "Date here", style=wxALIGN_CENTRE|wxST_NO_AUTORESIZE)

        # top row container 
        hbs1=wxBoxSizer(wxHORIZONTAL)
        hbs1.Add(prev, 0, wxEXPAND)
        hbs1.Add(self.title, 1, wxEXPAND)
        hbs1.Add(next, 0, wxEXPAND)
        vbs.Add(hbs1, 0, wxEXPAND)

        # list box and two buttons below
        self.listbox=wxListBox(self, self.ID_LISTBOX, style=wxLB_SINGLE|wxLB_HSCROLL|wxLB_NEEDED_SB)
        add=wxButton(self, self.ID_ADD, "New")
        hbs2=wxBoxSizer(wxHORIZONTAL)
        hbs2.Add(add, 1, wxALIGN_CENTER|wxLEFT|wxRIGHT, border=5)
        
        # sizer for listbox
        lbs=wxBoxSizer(wxVERTICAL)
        lbs.Add(self.listbox, 1, wxEXPAND|wxBOTTOM, border=5)
        lbs.Add(hbs2, 0, wxEXPAND)


        self.fieldnames=('description', 'start', 'end', 'repeat',
        'alarm', 'ringtone', '?d')
        
        self.fielddesc=( 'Description', 'Start', 'End', 'Repeat',
        'Alarm', 'Ringtone', '?Internal' )

        # right hand bit with all fields
        gs=wxFlexGridSizer(-1,2,5,5)
        gs.AddGrowableCol(1)
        self.fields={}
        for desc,field in zip(self.fielddesc, self.fieldnames):
            t=wxStaticText(self, -1, desc, style=wxALIGN_LEFT)
            gs.Add(t)
            if field=='start':
                c=DVTimeControl(self,self.ID_START)
            elif field=='end':
                c=DVTimeControl(self,self.ID_END)
            elif field=='repeat':
                c=DVRepeatControl(self, self.ID_REPEAT)
            elif field=='description':
                c=wxTextCtrl(self, len(self.fields)+10, "dummy")
            else:
                c=DVIntControl(self, -1)
            gs.Add(c,0,wxEXPAND)
            self.fields[field]=c

        # buttons below fields
        delete=wxButton(self, self.ID_DELETE, "Delete")
        revert=wxButton(self, self.ID_REVERT, "Revert")
        save=wxButton(self, self.ID_SAVE, "Save")

        hbs4=wxBoxSizer(wxHORIZONTAL)
        hbs4.Add(delete, 1, wxALIGN_CENTRE|wxLEFT, border=10)
        hbs4.Add(revert, 1, wxALIGN_CENTRE|wxLEFT|wxRIGHT, border=10)
        hbs4.Add(save, 1, wxALIGN_CENTRE|wxRIGHT, border=10)

        # fields and buttons together
        vbs2=wxBoxSizer(wxVERTICAL)
        vbs2.Add(gs, 1, wxEXPAND|wxBOTTOM, border=5)
        vbs2.Add(hbs4, 0, wxEXPAND|wxALIGN_CENTRE)

        # container for everything below title row
        hbs3=wxBoxSizer(wxHORIZONTAL)
        hbs3.Add(lbs, 1, wxEXPAND|wxALL, 5)
        hbs3.Add(vbs2, 2, wxEXPAND|wxALL, 5)

        vbs.Add(hbs3, 1, wxEXPAND)

        # horizontal rules plus help and cancel buttons
        vbs.Add(wxStaticLine(self, -1, style=wxLI_HORIZONTAL), 0, wxEXPAND)
        help=wxButton(self, self.ID_HELP, "Help")
        close=wxButton(self, self.ID_CLOSE, "Close")
        hbs4=wxBoxSizer(wxHORIZONTAL)
        hbs4.Add(help, 0, wxALL, 5)
        hbs4.Add(close, 0, wxALL, 5)
        vbs.Add(hbs4, 0, wxALIGN_RIGHT|wxALL, 5)

        self.SetSizer(vbs)
        self.SetAutoLayout(True)
        vbs.Fit(self)
        self.entries={}
        self.entrymap=[]

        EVT_LISTBOX(self, self.ID_LISTBOX, self.OnListBoxItem)
        EVT_LISTBOX_DCLICK(self, self.ID_LISTBOX, self.OnListBoxItem)

        self.seteditmode(False)

    def OnListBoxItem(self, _):
        self.updatefields(self.entrymap[self.listbox.GetSelection()])
        self.seteditmode(True)

    def setdate(self, year, month, day):
        d=time.strftime("%A %d %B %Y", (year,month,day,0,0,0, calendar.weekday(year,month,day),1, 0))
        self.title.SetLabel(d)
        self.entries=self.cw.getentrydata(year,month,day)
        self.updatelistbox()
        self.updatefields(None)

    def updatelistbox(self):
        self.listbox.Clear()
        self.entrymap=[]
        for i in self.entries:
            entry=i
            e=( entry['start'][3:5], entry['end'][3:5], entry['description'], entry)
            self.entrymap.append(e)
        # time ordered
        self.entrymap.sort()
        # add listbox entries
        for e in self.entrymap:
            if 0: # ampm/miltime config here ::TODO::
                str="%2d:%02d" % (e[0][0], e[0][1])
            else:
                hr=e[0][0]
                ap="am"
                if hr>=12:
                    ap="pm"
                    hr-=12
                if hr==0: hr=12
                str="%2d:%02d %s" % (hr, e[0][1], ap)
            str+=" "+e[2]
            print "adding",str
            self.listbox.Append(str)

        # make entrymap only be entries
        self.entrymap=[x[3] for x in self.entrymap] 

    def updatefields(self, entry):
        print entry
        if entry is None:
            for i in self.fields:
                self.fields[i].SetValue("")
            return
        for i in self.fieldnames:
            print i, entry[i]
            self.fields[i].SetValue(entry[i])

    def seteditmode(self, val):
        # if val is true then we are editing an entry

        # previous and next buttons
        self.FindWindowById(self.ID_PREV).Enable(not val)
        self.FindWindowById(self.ID_NEXT).Enable(not val)

        # listbox
        self.FindWindowById(self.ID_LISTBOX).Enable(not val)

        # main buttons
        self.FindWindowById(self.ID_ADD).Enable(not val)
        self.FindWindowById(self.ID_DELETE).Enable(val)
        self.FindWindowById(self.ID_REVERT).Enable(val)
        self.FindWindowById(self.ID_SAVE).Enable(val)

        # fields
        for i in self.fields:
            self.fields[i].Enable(val)

        # bottom buttons
        self.FindWindowById(self.ID_CLOSE).Enable(not val)

class DVTimeControl(wxPanel):
    # A time control customised to work in the dayview editor
    def __init__(self,parent,id):
        wxPanel.__init__(self, parent, -1)
        self.tc=wxTimeCtrl(self, id)
        self.spin=wxSpinButton(self, -1, style=wxSP_VERTICAL, size=wxSize(-1,20))
        self.tc.BindSpinButton(self.spin)
        bs=wxBoxSizer(wxHORIZONTAL)
        bs.Add(self.tc,0,wxEXPAND)
        bs.Add(self.spin,0, wxEXPAND)
        self.SetSizer(bs)
        self.SetAutoLayout(True)
        bs.Fit(self)

    def SetValue(self, v):
        if isinstance(v, str):
            assert len(v)==0  # blank string
            self.tc.SetWxDateTime(wxDateTimeFromHMS(0, 0))
            return
        self.tc.SetWxDateTime(wxDateTimeFromHMS(v[3], v[4]))
    
class DVRepeatControl(wxChoice):
    # shows the repeat values
    vals=[None, "daily", "monfri", "weekly", "monthly", "yearly"]
    desc=["None", "Daily", "Mon - Fri", "Weekly", "Monthly", "Yearly" ]

    def __init__(self, parent, id):
        wxChoice.__init__(self, parent, id, choices=self.desc)

    def SetValue(self, v):
        if isinstance(v,str) and len(v)==0:  # blank string
            v=None
        assert v in self.vals
        self.SetSelection(self.vals.index(v))

class DVIntControl(wxIntCtrl):
    # shows integer values
    def __init__(self, parent, id):
        wxIntCtrl.__init__(self, parent, id, limited=True)

    def SetValue(self, v):
        if isinstance(v, str):
            assert len(v)==0  # blank string
            v=0
        if v is None:
            v=-1
        assert isinstance(v, int)
        wxIntCtrl.SetValue(self,v)
        

        

        
###
### Copied from wxPython.lib.dialogs.  This one is different in that it
### uses a larger text control (standard one on windows is limited to
### 32KB of text)
###

from wxPython.lib.layoutf import Layoutf

class FixedScrolledMessageDialog(wx.wxDialog):
    def __init__(self, parent, msg, caption, pos = wxDefaultPosition, size = (800,600)):
        wxDialog.__init__(self, parent, -1, caption, pos, size,
                          style=wxDEFAULT_DIALOG_STYLE|wxRESIZE_BORDER|wxNO_FULL_REPAINT_ON_RESIZE)
        text = wxTextCtrl(self, 1,
                          style=wxTE_MULTILINE | wxTE_READONLY | wxTE_RICH2 |
                          wxNO_FULL_REPAINT_ON_RESIZE|wxTE_DONTWRAP  )
        f=wxFont(10, wxMODERN, wxNORMAL, wxNORMAL )
        ta=wxTextAttr(font=f)
        text.SetDefaultStyle(ta)
        ok = wxButton(self, wxID_OK, "OK")
        text.SetConstraints(Layoutf('t=t5#1;b=t5#2;l=l5#1;r=r5#1', (self,ok)))
        ok.SetConstraints(Layoutf('b=b5#1;x%w50#1;w!80;h!25', (self,)))
        self.SetAutoLayout(1)
        self.Layout()
        text.AppendText(msg) # if i supply this in constructor then the font doesn't take
        text.ShowPosition(text.XYToPosition(0,0))

###
###  Too much freaking effort for a simple statusbar.  Mostly copied from the demo.
###

class MyStatusBar(wxStatusBar):
    def __init__(self, parent, id=-1):
        wxStatusBar.__init__(self, parent, id)
        self.sizechanged=False
        EVT_SIZE(self, self.OnSize)
        EVT_IDLE(self, self.OnIdle)
        self.gauge=wxGauge(self, 1000, 1)
        self.SetFieldsCount(4)
        self.SetStatusWidths( [200, -5, 180, -20] )
        self.Reposition()

    def OnSize(self,_):
        self.Reposition()
        self.sizechanged=True

    def OnIdle(self,_):
        if self.sizechanged:
            self.Reposition()

    def Reposition(self):
        rect=self.GetFieldRect(2)
        self.gauge.SetPosition(wxPoint(rect.x+2, rect.y+2))
        self.gauge.SetSize(wxSize(rect.width-4, rect.height-4))
        self.sizeChanged = False

    def progressminor(self, pos, max, desc=""):
        self.gauge.SetRange(max)
        self.gauge.SetValue(pos)
        self.SetStatusText(desc,3)

    def progressmajor(self, pos, max, desc=""):
        self.progressminor(0,1)
        if len(desc):
            str="%d/%d %s" % (pos+1, max, desc)
        else:
            str=desc
        self.SetStatusText(str,1)

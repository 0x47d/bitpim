# Part of bitpim

# $Id$

# standard modules
import os
import re

# wx modules
from wxPython.grid import *
from wxPython.wx import *
from wxPython.lib.mixins.listctrl import wxColumnSorterMixin, wxListCtrlAutoWidthMixin

# my modules
import common
import gui

####
#### A widget for displaying the phone information
####            

# we use a custom table class
class PhoneDataTable(wxPyGridTableBase):

    numbertypetab=( 'Home', 'Home2', 'Office', 'Office2', 'Mobile', 'Mobile2',
                    'Pager', 'Fax', 'Fax2', 'None' )

    typesnames=( 'type1', 'type2', 'type3', 'type4', 'type5' )

    typestypename=wxGRID_VALUE_CHOICE+":"+",".join(numbertypetab)

    intnames=( 'group', 'msgringtone', 'ringtone', 'serial1', 'serial2' )
    
    boolnames=( 'secret', )
    
    def __init__(self, mainwindow):
        wxPyGridTableBase.__init__(self)
        self.mainwindow=mainwindow
        self.numrows=0
        self.numcols=0
        self.labels=[] # columns
        self.roworder=[] # rows
        self._data={}
        self.needswrite=False


    def OnIdle(self, _):
        if self.needswrite:
            print "updating filesystem"
            self.populatefs(self.getdata({}))
            self.needswrite=False


    def getdata(self, dict):
        dict['phonebook']=self._data.copy()
        # need to add group
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
        print "deleting", rows
        rows.sort()
        rows.reverse()
        for row in rows:
            del self._data[self.roworder[row]]
            del self.roworder[row]
            msg=wxGridTableMessage(self, wxGRIDTABLE_NOTIFY_ROWS_DELETED, row, 1)
            self.GetView().ProcessTableMessage(msg)
        if len(rows):
            self.needswrite=True

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
        f.write("result['phonebook']="+`dict['phonebook']`)
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
        return dict

    def populate(self, dict):
        self.clear()
        pb=dict['phonebook']
        k=pb.keys()
        k.sort()
        self._data.update(pb)
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
                    
    def GetNumberRows(self):
        return len(self.roworder)

    def GetNumberCols(self):
        return len(self.labels)

    def IsEmptyCell(self, row, col):
        return False

    def GetValue(self, row, col):
        try:
            if self.labels[col] in self.typesnames:
                return self.numbertypetab[ self._data[self.roworder[row]][self.labels[col]] ]
            return self._data[self.roworder[row]][self.labels[col]]
        except:
            print "bad request", row, col
            return ""

    def GetTypeName(self, row, col):
        # print "GetTypeName",row,col
        if self.labels[col] in self.typesnames:
            return self.typestypename
        if self.labels[col] in self.intnames or self.labels[col][0]=='?':
            return wxGRID_VALUE_NUMBER
        if self.labels[col] in self.boolnames:
            return wxGRID_VALUE_BOOL
        return wxGRID_VALUE_STRING

    def SetValue(self, row, col, value):
        if self.labels[col] in self.typesnames:
            for i in range(0,len(self.numbertypetab)):
                if value==self.numbertypetab[i]:
                    value=i
                    break
        print "SetValue",row,col,value
        self._data[self.roworder[row]][self.labels[col]]=value
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

    def OnLeftDClick(self, _):
        if self.CanEnableCellControl():
            self.EnableCellEditControl()

    def OnDelete(self, evt):
        rows=self.GetSelectedRows()
        self.table.OnDelete(rows)

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
        
    def log(self, str):
        self.tb.AppendText(str+"\r\n")

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
        self.mw.ringerpath=os.path.join(path, "ringer")
        self.mw.wallpaperpath=os.path.join(path, "wallpaper")
        self.mw.phonebookpath=os.path.join(path, "phonebook")
        self.mw.config.Write("path", path)
        self.mw.commportsetting=self.commbox.GetValue()
        self.mw.config.Write("lgvx4400port", self.mw.commportsetting)
        self.mw.commphone=None # cause it to be recreated
        
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
    def __init__(self, mainwindow, parent, id=-1, style=wxLC_REPORT|wxLC_SINGLE_SEL):
        wxListCtrl.__init__(self, parent, id, style=style)
        wxListCtrlAutoWidthMixin.__init__(self)
        self.droptarget=MyFileDropTarget(self)
        self.SetDropTarget(self.droptarget)
        self.mainwindow=mainwindow
        self.thedir=None
        self.wildcard="I forgot to set wildcard in derived class|*"
        self.maxlen=255
        if style!=wxLC_REPORT and not gui.IsGtk():
            # gtk can't do report and icon style
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
            # delete them all!
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
        for i in dict['ringtone']:
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
        if not gui.IsGtk():
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
        for i in dict['wallpaper']:
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
            if not gui.IsGtk():
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
            # scale the source.  we use int arithmetic with 1000 being 1.000
            sfactorw=self.usewidth*1000/img.GetWidth()
            sfactorh=self.useheight*1000/img.GetHeight()
            sfactor=min(sfactorw,sfactorh) # preserve aspect ratio
            newwidth=img.GetWidth()*sfactor/1000
            newheight=img.GetHeight()*sfactor/1000
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
        self.SetStatusWidths( [300, -5, 260, -20] )
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

#!/usr/bin/env python

### BITPIM
###
### Copyright (C) 2003 Roger Binns <rogerb@rogerbinns.com>
###
### This software is under the Artistic license.
### Please see the accompanying LICENSE file
###
### $Id$

"""Most of the graphical user interface elements making up BitPim"""

# standard modules
import os
import calendar
import time
import copy

# wx modules
from wxPython.wx import *
from wxPython.grid import *
from wxPython.lib.mixins.listctrl import wxColumnSorterMixin, wxListCtrlAutoWidthMixin
from wxPython.lib.intctrl import *
from wxPython.lib.maskededit import wxMaskedTextCtrl
from wxPython.html import *

# my modules
import common
import calendarcontrol
import helpids
import comscan
import comdiagnose
import brewcompressedimage
import bpaudio
import analyser
import guihelper

####
#### A simple text widget that does nice pretty logging.
####        

    
class LogWindow(wxPanel):

    theanalyser=None
    
    def __init__(self, parent):
        wxPanel.__init__(self,parent, -1, style=wxNO_FULL_REPAINT_ON_RESIZE)
        # have to use rich2 otherwise fixed width font isn't used on windows
        self.tb=wxTextCtrl(self, 1, style=wxTE_MULTILINE| wxTE_RICH2|wxNO_FULL_REPAINT_ON_RESIZE|wxTE_DONTWRAP|wxTE_READONLY)
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

        EVT_KEY_UP(self.tb, self.OnKeyUp)

    def OnIdle(self,_):
        if len(self.outstandingtext):
            self.tb.AppendText(self.outstandingtext)
            self.outstandingtext=""
            self.tb.ScrollLines(-1)

    def log(self, str):
        now=time.time()
        t=time.localtime(now)
        self.outstandingtext+="%d:%02d:%02d.%03d %s\r\n"  % ( t[3], t[4], t[5],  int((now-int(now))*1000), str)

    def logdata(self, str, data, klass=None):
        hd=""
        if data is not None:
            hd="Data - "+`len(data)`+" bytes\n"
            if klass is not None:
                try:
                    hd+="<#! %s.%s !#>\n" % (klass.__module__, klass.__name__)
                except:
                    klass=klass.__class__
                    hd+="<#! %s.%s !#>\n" % (klass.__module__, klass.__name__)
            hd+=common.datatohexstring(data)
        self.log("%s %s" % (str, hd))

    def OnKeyUp(self, evt):
        keycode=evt.GetKeyCode()
        if keycode==ord('P') and evt.ControlDown() and evt.AltDown():
            # analysze what was selected
            data=self.tb.GetStringSelection()
            # or the whole buffer if it was nothing
            if data is None or len(data)==0:
                data=self.tb.GetValue()
            try:
                self.theanalyser.Show()
            except:
                self.theanalyser=None
                
            if self.theanalyser is None:
                self.theanalyser=analyser.Analyser(data=data)

            self.theanalyser.Show()
            self.theanalyser.newdata(data)
            evt.Skip()
            


###
### Dialog asking what you want to sync
###

class GetPhoneDialog(wxDialog):
    strings= ('PhoneBook', 'Calendar', 'Wallpaper', 'Ringtone')
    NOTREQUESTED=0
    MERGE=1
    OVERWRITE=2

    HELPID=helpids.ID_GET_PHONE_DATA

    # ::TODO:: ok button should be grayed out unless at least one category is
    # picked
    def __init__(self, frame, title, id=-1):
        wxDialog.__init__(self, frame, id, title,
                          style=wxCAPTION|wxSYSTEM_MENU|wxDEFAULT_DIALOG_STYLE)
        gs=wxFlexGridSizer(6, 4,5 ,10)
        gs.AddGrowableCol(1)
        gs.AddMany( [
            (wxStaticText(self, -1, "Get"), 0, wxEXPAND),
            (wxStaticText(self, -1, "Type"), 0, wxEXPAND),
            (wxStaticText(self, -1, "Merge"), 0, wxEXPAND),
            (wxStaticText(self, -1, "Replace"), 0, wxEXPAND)
            ])
        self.cb=[]
        self.rb=[]
        for i in self.strings:
            self.cb.append(wxCheckBox(self,-1, ""))
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

        # merge is supported for phonebook
        self.rb[0][0].Enable(True)
        self.rb[0][0].SetValue(True) # and set to true by default

        EVT_BUTTON(self, wxID_HELP, self.OnHelp)

    def _setting(self, index):
        if not self.cb[index].GetValue(): return self.NOTREQUESTED
        if self.rb[index][0].GetValue(): return self. MERGE
        return self.OVERWRITE

    def GetPhoneBookSetting(self):
        return self._setting(0)

    def GetCalendarSetting(self):
        return self._setting(1)

    def GetWallpaperSetting(self):
        return self._setting(2)

    def GetRingtoneSetting(self):
        return self._setting(3)

    def OnHelp(self,_):
        wxGetApp().displayhelpid(self.HELPID)

class SendPhoneDialog(GetPhoneDialog):
    HELPID=helpids.ID_SEND_PHONE_DATA
    
    def __init__(self, frame, title, id=-1):
        GetPhoneDialog.__init__(self, frame, title, id)
        # turn all checkboxes off by default for writing
        # we want user to explicitly write stuff they changed
        for i in self.cb:
            i.SetValue(False)
        # We do support merge for wallpaper and ringtone
        # but not phonebook
        self.rb[0][0].Enable(False)
        self.rb[2][0].Enable(True)
        self.rb[3][0].Enable(True)
        

###
###  The master config dialog
###

class ConfigDialog(wxDialog):
    phonemodels={ 'LG-VX4400': 'com_lgvx4400',
                  'LG-VX6000': 'com_lgvx6000',
                  'LG-TM520': 'com_lgtm520',
                  'LG-VX10': 'com_lgtm520',
                  'SCP-4900': 'com_sanyo4900',
                  'SCP-8100': 'com_sanyo4900'}

    setme="<setme>"
    ID_DIRBROWSE=1
    ID_COMBROWSE=2
    ID_RETRY=3
    def __init__(self, mainwindow, frame, title="BitPim Settings", id=-1):
        wxDialog.__init__(self, frame, id, title,
                          style=wxCAPTION|wxSYSTEM_MENU|wxDEFAULT_DIALOG_STYLE|wxRESIZE_BORDER)
        self.mw=mainwindow
        gs=wxFlexGridSizer(2, 3,  5 ,10)
        gs.AddGrowableCol(1)

        gs.Add( wxStaticText(self, -1, "Disk storage"), 0, wxCENTER)
        self.diskbox=wxTextCtrl(self, -1, self.setme, size=wxSize( 400, 10))
        gs.Add( self.diskbox, 0, wxEXPAND)
        gs.Add( wxButton(self, self.ID_DIRBROWSE, "Browse ..."), 0, wxEXPAND)

        gs.Add( wxStaticText(self, -1, "Com Port"), 0, wxCENTER)
        self.commbox=wxTextCtrl(self, -1, self.setme)
        gs.Add( self.commbox, 0, wxEXPAND)
        gs.Add( wxButton(self, self.ID_COMBROWSE, "Browse ..."), 0, wxEXPAND)

        gs.Add( wxStaticText(self, -1, "Phone Type"), 0, wxCENTER)
        self.phonebox=wxComboBox(self, -1, style=wxCB_DROPDOWN|wxCB_READONLY|wxCB_SORT,choices=self.phonemodels.keys())
        gs.Add( self.phonebox, 0, wxEXPAND)

        bs=wxBoxSizer(wxVERTICAL)
        bs.Add(gs, 0, wxEXPAND|wxALL, 10)
        bs.Add(wxStaticLine(self, -1), 0, wxEXPAND|wxTOP|wxBOTTOM, 7)
        
        but=self.CreateButtonSizer(wxOK|wxCANCEL|wxHELP)
        bs.Add(but, 0, wxCENTER, 10)

        EVT_BUTTON(self, wxID_HELP, self.OnHelp)
        EVT_BUTTON(self, self.ID_DIRBROWSE, self.OnDirBrowse)
        EVT_BUTTON(self, self.ID_COMBROWSE, self.OnComBrowse)
        EVT_BUTTON(self, wxID_OK, self.OnOK)

        self.setdefaults()

        self.SetSizer(bs)
        self.SetAutoLayout(True)
        bs.Fit(self)

    def OnOK(self, _):
        # validate directory
        dir=self.diskbox.GetValue()
        try:
            os.makedirs(dir)
        except:
            pass
        if os.path.isdir(dir):
            self.EndModal(wxID_OK)
            return
        wxTipWindow(self.diskbox, "No such directory - please correct")
            

    def OnHelp(self, _):
        wxGetApp().displayhelpid(helpids.ID_SETTINGS_DIALOG)

    def OnDirBrowse(self, _):
        dlg=wxDirDialog(self, defaultPath=self.diskbox.GetValue(), style=wxDD_NEW_DIR_BUTTON)
        res=dlg.ShowModal()
        v=dlg.GetPath()
        dlg.Destroy()
        if res==wxID_OK:
            self.diskbox.SetValue(v)

    def OnComBrowse(self, _):
        self.mw.wt.clearcomm()
        # remember its size
        w=self.mw.config.ReadInt("combrowsewidth", 640)
        h=self.mw.config.ReadInt("combrowseheight", 480)
        p=self.mw.config.ReadInt("combrowsesash", 200)
        dlg=CommPortDialog(self, defaultport=self.commbox.GetValue(), sashposition=p)
        dlg.SetSize(wxSize(w,h))
        dlg.Centre()
        res=dlg.ShowModal()
        v=dlg.GetPort()
        sz=dlg.GetSize()
        self.mw.config.WriteInt("combrowsewidth", sz.GetWidth())
        self.mw.config.WriteInt("combrowseheight", sz.GetHeight())
        self.mw.config.WriteInt("combrowsesash", dlg.sashposition)
        dlg.Destroy()
        if res==wxID_OK:
            self.commbox.SetValue(v)
        

    def setfromconfig(self):
        if len(self.mw.config.Read("path", "")):
            self.diskbox.SetValue(self.mw.config.Read("path", ""))
        if len(self.mw.config.Read("lgvx4400port")):
            self.commbox.SetValue(self.mw.config.Read("lgvx4400port", ""))
        if len(self.mw.config.Read("phonetype")):
            self.phonebox.SetValue(self.mw.config.Read("phonetype"))


    def setdefaults(self):
        if self.diskbox.GetValue()==self.setme:
            if guihelper.IsMSWindows(): # we want subdir of my documents on windows
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
            comm="auto"
            self.commbox.SetValue(comm)
        print "pb=",self.phonebox.GetValue()
        if self.phonebox.GetValue()=="":
            self.phonebox.SetValue("LG-VX4400")

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
            self.mw.wt.clearcomm()
        # comm parameters (retry, timeouts, flow control etc)
        commparm={}
        commparm['retryontimeout']=self.mw.config.ReadInt("commretryontimeout", False)
        commparm['timeout']=self.mw.config.ReadInt('commtimeout', 3)
        commparm['hardwareflow']=self.mw.config.ReadInt('commhardwareflow', False)
        commparm['softwareflow']=self.mw.config.ReadInt('commsoftwareflow', False)
        commparm['baud']=self.mw.config.ReadInt('commbaud', 115200)
        self.mw.commparams=commparm
        # phone model
        self.mw.config.Write("phonetype", self.phonebox.GetValue())
        self.mw.phonemodule=__import__(self.phonemodels[self.phonebox.GetValue()])
        # ::TODO:: add/remove tabs depending on what phone supports
                                       
        

    def _fixup(self, path):
        # os.path.join screws up adding root directory of a drive to
        # a directory.  eg join("c:\", "foo") gives "c:\\foo" whch
        # is invalid.  This function fixes that
        if len(path)>=3:
            if path[1]==':' and path[2]=='\\' and path[3]=='\\':
                return path[0:2]+path[3:]
        return path
        
    def needconfig(self):
        # Set base config
        self.setfromconfig()
        # are any at unknown settings
        if self.diskbox.GetValue()==self.setme or \
           self.commbox.GetValue()==self.setme:
            # fill in and set defaults
            self.setdefaults()
            self.updatevariables()
            # any still unset?
            if self.diskbox.GetValue()==self.setme or \
                   self.commbox.GetValue()==self.setme:
                return True
        # does data directory exist?
        try:
            os.makedirs(self.diskbox.GetValue())
        except:
            pass
        if not os.path.isdir(self.diskbox.GetValue()):
            return True

        return False

    def ShowModal(self):
        self.setfromconfig()
        ec=wxDialog.ShowModal(self)
        if ec==wxID_OK:
            self.updatevariables()
        return ec

###
### The select a comm port dialog box
###

class CommPortDialog(wxDialog):
    ID_LISTBOX=1
    ID_TEXTBOX=2
    ID_REFRESH=3
    ID_SASH=4
    
    def __init__(self, parent, id=-1, title="Choose a comm port", defaultport="auto", sashposition=0):
        wxDialog.__init__(self, parent, id, title, style=wxCAPTION|wxSYSTEM_MENU|wxDEFAULT_DIALOG_STYLE|wxRESIZE_BORDER)
        self.parent=parent
        self.port=defaultport
        self.sashposition=sashposition
        
        p=self # parent widget

        # the listbox and textbox in a splitter
        splitter=wxSplitterWindow(p, self.ID_SASH, style=wxSP_3D|wxSP_LIVE_UPDATE)
        self.lb=wxListBox(splitter, self.ID_LISTBOX, style=wxLB_SINGLE|wxLB_HSCROLL|wxLB_NEEDED_SB)
        self.tb=wxHtmlWindow(splitter, self.ID_TEXTBOX, size=wxSize(400,400)) # default style is auto scrollbar
        splitter.SplitHorizontally(self.lb, self.tb, sashposition)

        # the buttons
        buttsizer=wxGridSizer(1, 4)
        buttsizer.Add(wxButton(p, wxID_OK, "OK"), 0, wxALL, 10)
        buttsizer.Add(wxButton(p, self.ID_REFRESH, "Refresh"), 0, wxALL, 10)
        buttsizer.Add(wxButton(p, wxID_HELP, "Help"), 0, wxALL, 10)
        buttsizer.Add(wxButton(p, wxID_CANCEL, "Cancel"), 0, wxALL, 10)

        # vertical join of the two
        vbs=wxBoxSizer(wxVERTICAL)
        vbs.Add(splitter, 1, wxEXPAND)
        vbs.Add(buttsizer, 0, wxCENTER)

        # hook into self
        p.SetSizer(vbs)
        p.SetAutoLayout(True)
        vbs.Fit(p)

        # update dialog
        self.OnRefresh()

        # hook in all the widgets
        EVT_BUTTON(self, wxID_CANCEL, self.OnCancel)
        EVT_BUTTON(self, wxID_HELP, self.OnHelp)
        EVT_BUTTON(self, self.ID_REFRESH, self.OnRefresh)
        EVT_BUTTON(self, wxID_OK, self.OnOk)
        EVT_LISTBOX(self, self.ID_LISTBOX, self.OnListBox)
        EVT_LISTBOX_DCLICK(self, self.ID_LISTBOX, self.OnListBox)
        EVT_SPLITTER_SASH_POS_CHANGED(self, self.ID_SASH, self.OnSashChange)

    def OnSashChange(self, _=None):
        self.sashposition=self.FindWindowById(self.ID_SASH).GetSashPosition()

    def OnRefresh(self, _=None):
        self.tb.SetPage("<p><b>Refreshing</b> ...")
        self.lb.Clear()
        self.Update()
        ports=comscan.comscan()
        self.portinfo=comdiagnose.diagnose(ports)
        if len(self.portinfo):
            self.portinfo=[ ("Automatic", "auto",
                             "<p>BitPim will try to detect the correct port automatically when accessing your phone"
                             ) ]+\
                           self.portinfo
        self.lb.Clear()
        sel=-1
        for name, actual, description in self.portinfo:
            if sel<0 and self.GetPort()==actual:
                sel=self.lb.GetCount()
            self.lb.Append(name)
        if sel<0:
            sel=0
        if self.lb.GetCount():
            self.lb.SetSelection(sel)
            self.OnListBox()
        else:
            self.FindWindowById(wxID_OK).Enable(False)
            self.tb.SetPage("<html><body>You do not have any com/serial ports on your system</body></html>")

    def OnListBox(self, _=None):
        # enable/disable ok button
        p=self.portinfo[self.lb.GetSelection()]
        if p[1] is None:
            self.FindWindowById(wxID_OK).Enable(False)
        else:
            self.port=p[1]
            self.FindWindowById(wxID_OK).Enable(True)
        self.tb.SetPage(p[2])
        

    def OnCancel(self, _):
        self.EndModal(wxID_CANCEL)

    def OnOk(self, _):
        self.EndModal(wxID_OK)

    def OnHelp(self, _):
        wxGetApp().displayhelpid(helpids.ID_COMMSETTINGS_DIALOG)        

    def GetPort(self):
        return self.port

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


    # ::TODO:: stop storing file data in 'data' and get from
    # disk instead.
    # be resilient to conversion failures in ringer
    # ringer onluanch should convert qcp to wav
    
    # File we should ignore
    skiplist= ( 'desktop.ini', 'thumbs.db', 'zbthumbnail.info' )
    
    def __init__(self, mainwindow, parent, id=-1, style=wxLC_REPORT|wxLC_SINGLE_SEL|wxLC_AUTOARRANGE ):
        wxListCtrl.__init__(self, parent, id, style=style)
        wxListCtrlAutoWidthMixin.__init__(self)
        self.droptarget=MyFileDropTarget(self)
        self.SetDropTarget(self.droptarget)
        self.mainwindow=mainwindow
        self.thedir=None
        self.wildcard="I forgot to set wildcard in derived class|*"
        self.maxlen=255
        if (style&wxLC_REPORT)==wxLC_REPORT or guihelper.HasFullyFunctionalListView():
            # some can't do report and icon style
            self.InsertColumn(0, "Name")
            self.InsertColumn(1, "Bytes", wxLIST_FORMAT_RIGHT)
            
            self.SetColumnWidth(0, 200)
            
        self.menu=wxMenu()
        self.menu.Append(guihelper.ID_FV_OPEN, "Open")
        self.menu.AppendSeparator()
        self.menu.Append(guihelper.ID_FV_DELETE, "Delete")
        self.menu.AppendSeparator()
        self.menu.Append(guihelper.ID_FV_RENAME, "Rename")
        self.menu.Append(guihelper.ID_FV_REFRESH, "Refresh")
        self.menu.Append(guihelper.ID_FV_PROPERTIES, "Properties")

        self.addfilemenu=wxMenu()
        self.addfilemenu.Append(guihelper.ID_FV_ADD, "Add ...")
        self.addfilemenu.Append(guihelper.ID_FV_REFRESH, "Refresh")

        EVT_MENU(self.menu, guihelper.ID_FV_REFRESH, self.OnRefresh)
        EVT_MENU(self.addfilemenu, guihelper.ID_FV_REFRESH, self.OnRefresh)
        EVT_MENU(self.addfilemenu, guihelper.ID_FV_ADD, self.OnAdd)
        EVT_MENU(self.menu, guihelper.ID_FV_OPEN, self.OnLaunch)
        EVT_MENU(self.menu, guihelper.ID_FV_DELETE, self.OnDelete)
        EVT_MENU(self.menu, guihelper.ID_FV_PROPERTIES, self.OnProperties)

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
            dlg=AlertDialogWithHelp(self, "You don't have any programs defined to open ."+ext+" files",
                                "Unable to open", lambda _: wxGetApp().displayhelpid(helpids.ID_NO_MIME_OPEN),
                                    style=wxOK|wxICON_INFORMATION)
            dlg.ShowModal()
            dlg.Destroy()
        else:
            try:
                wxExecute(cmd)
            except:
                dlg=AlertDialogWithHelp(self, "Unable to execute '"+cmd+"'",
                                    "Open failed", lambda _: wxGetApp().displayhelpid(helpids.ID_MIME_EXEC_FAILED),
                                        style=wxOK|wxICON_ERROR)
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
            # changing target in dragndrop
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

    def versionupgrade(self, dict, version):
        raise Exception("not implemented")

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

    def genericpopulatefs(self, dict, key, indexkey, version):
        try:
            os.makedirs(self.thedir)
        except:
            pass
        if not os.path.isdir(self.thedir):
            raise Exception("Bad directory for "+key+" '"+self.thedir+"'")
        for f in os.listdir(self.thedir):
            # delete them all except windows magic ones which we ignore
            if f.lower() not in self.skiplist:
                os.remove(os.path.join(self.thedir, f))

        d=dict[key]
        for i in d:
            f=open(os.path.join(self.thedir, i), "wb")
            f.write(d[i])
            f.close()
        d={}
        d[indexkey]=dict[indexkey]
        common.writeversionindexfile(os.path.join(self.thedir, "index.idx"), d, version)
        return dict

    def genericgetfromfs(self, result, key, indexkey, currentversion):
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
                common.readversionedindexfile(os.path.join(self.thedir, file), d, self.versionupgrade, currentversion)
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
    CURRENTFILEVERSION=1
    
    def __init__(self, mainwindow, parent, id=-1):
        FileView.__init__(self, mainwindow, parent, id)
        self.InsertColumn(2, "Length")
        self.InsertColumn(3, "Index")
        self.InsertColumn(4, "Description")
        il=wxImageList(32,32)
        il.Add(guihelper.getbitmap("ringer"))
        self.AssignImageList(il, wxIMAGE_LIST_NORMAL)
        self._data={}
        self._data['ringtone']={}
        self._data['ringtone-index']={}

        self.wildcard="MIDI files (*.mid)|*.mid|PureVoice Files (*.qcp)|*.qcp"
        self.maxlen=19

    def getdata(self, dict):
        dict.update(self._data)
        return dict

    def OnAddFile(self, file):
        self.thedir=self.mainwindow.ringerpath
        if os.path.splitext(file)[1]=='.mid':
            target=self.getshortenedbasename(file, 'mid')
            if target==None: return # user didn't want to
            f=open(file, "rb")
            contents=f.read()
            f.close()
            f=open(target, "wb")
            f.write(contents)
            f.close()
        else:
            # ::TODO:: warn if not on Windows
            target=self.getshortenedbasename(file, 'qcp')
            if target==None: return # user didn't want to
            qcpdata=bpaudio.converttoqcp(file)
            f=open(target, "wb")
            f.write(qcpdata)
            f.close()
            
        self.OnRefresh()

    def populatefs(self, dict):
        self.thedir=self.mainwindow.ringerpath
        return self.genericpopulatefs(dict, 'ringtone', 'ringtone-index', self.CURRENTFILEVERSION)
            
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
            if os.path.splitext(item['name'])[1]=='.qcp':
                self.SetStringItem(count, 2, "2 seconds :-)")
                self.SetStringItem(count, 3, `item['index']`)
                self.SetStringItem(count, 4, "PureVoice file")
            else:
                self.SetStringItem(count, 2, "1 second :-)")
                self.SetStringItem(count, 3, `item['index']`)
                self.SetStringItem(count, 4, "Midi file")
            count+=1

    def getfromfs(self, result):
        self.thedir=self.mainwindow.ringerpath
        return self.genericgetfromfs(result, "ringtone", 'ringtone-index', self.CURRENTFILEVERSION)

    def versionupgrade(self, dict, version):
        """Upgrade old data format read from disk

        @param dict:  The dict that was read in
        @param version: version number of the data on disk
        """

        # version 0 to 1 upgrade
        if version==0:
            version=1  # the are the same

        # 1 to 2 etc



###
### Various platform independent filename functions
###

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
    """A class encapsulating the GUI and data of the calendar (all days).  A seperate L{DayViewDialog} is
    used to edit the content of one particular day."""

    CURRENTFILEVERSION=2
    
    def __init__(self, mainwindow, parent, id=-1):
        """constructor

        @type  mainwindow: gui.MainWindow
        @param mainwindow: Used to get configuration data (such as directory to save/load data.
        @param parent:     Widget acting as parent for this one
        @param id:         id
        """
        self.mainwindow=mainwindow
        self.entrycache={}
        self.entries={}
        self.repeating=[]  # nb this is stored unsorted
        self._data={} # the underlying data
        calendarcontrol.Calendar.__init__(self, parent, rows=5, id=id)
        self.dialog=DayViewDialog(self, self)
        self._nextpos=-1  # pos ids for events we make

    def getdata(self, dict):
        """Return underlying calendar data in bitpim format

        @return:   The modified dict updated with at least C{dict['calendar']}"""
        dict['calendar']=self._data
        return dict

    def updateonchange(self):
        """Called when our data has changed

        The disk, widget and display are all updated with the new data"""
        d={}
        d=self.getdata(d)
        self.populatefs(d)
        self.populate(d)
        # Brute force - assume all entries have changed
        self.RefreshAllEntries()

    def AddEntry(self, entry):
        """Adds and entry into the calendar data.

        The entries on disk are updated by this function.

        @type  entry: a dict containing all the fields.
        @param entry: an entry.  It must contain a C{pos} field. You
                     should call L{newentryfactory} to make
                     an entry that you then modify
        """
        self._data[entry['pos']]=entry
        self.updateonchange()

    def DeleteEntry(self, entry):
        """Deletes an entry from the calendar data.

        The entries on disk are updated by this function.

        @type  entry: a dict containing all the fields.
        @param entry: an entry.  It must contain a C{pos} field
                      corresponding to an existing entry
        """
        del self._data[entry['pos']]
        self.updateonchange()

    def DeleteEntryRepeat(self, entry, year, month, day):
        """Deletes a specific repeat of an entry

        See L{DeleteEntry}"""
        e=self._data[entry['pos']]
        if not e.has_key('exceptions'):
            e['exceptions']=[]
        e['exceptions'].append( (year, month, day) )
        self.updateonchange()
        
    def ChangeEntry(self, oldentry, newentry):
        """Changes an entry in the calendar data.

        The entries on disk are updated by this function.
        """
        assert oldentry['pos']==newentry['pos']
        self._data[newentry['pos']]=newentry
        self.updateonchange()

    def getentrydata(self, year, month, day):
        """return the entry objects for corresponding date

        @rtype: list"""
        # return data from cache if we have it
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
            y,m,d=i['end'][0:3]
            if year>y or (year==y and month>m) or (year==y and month==m and day>d):
                continue # we are after this entry
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
        
    def newentryfactory(self, year, month, day):
        """Returns a new 'blank' entry with default fields

        @rtype: dict"""
        res={}
        now=time.localtime()
        res['start']=(year, month, day, now.tm_hour, now.tm_min)
        res['end']=[year, month, day, now.tm_hour, now.tm_min]
        # we make end be the next hour, unless it has gone 11pm
        # in which case it is 11:59pm
        if res['end'][3]<23:
            res['end'][3]+=1
            res['end'][4]=0
        else:
            res['end'][3]=23
            res['end'][4]=59
        res['repeat']=None
        res['description']='New event'
        res['changeserial']=1
        res['snoozedelay']=0
        res['alarm']=None
        res['daybitmap']=0
        res['ringtone']=0
        res['pos']=self.allocnextpos()
        return res

    def getdaybitmap(self, start, repeat):
        if repeat!="weekly":
            return 0
        dayofweek=calendar.weekday(*(start[:3]))
        dayofweek=(dayofweek+1)%7 # normalize to sunday == 0
        return [2048,1024,512,256,128,64,32][dayofweek]

    def allocnextpos(self):
        """Allocates a unique id for a new entry

        Negative integers are used to avoid any clashes with existing
        entries from the phone.  The existing data is checked to
        ensure there is no clash.

        @rtype: int"""
        while True:
            self._nextpos,res=self._nextpos-1, self._nextpos
            if res not in self._data:
                return res
        # can't get here but pychecker cant figure that out
        assert False
        return -1
        
    def OnGetEntries(self, year, month, day):
        """return pretty printed sorted entries for date
        as required by the parent L{calendarcontrol.Calendar} for
        display in a cell"""
        res=[(i['start'][3], i['start'][4], i['description']) for i in self.getentrydata(year, month,day)]
        res.sort()
        return res

    def OnEdit(self, year, month, day):
        """Called when the user wants to edit entries for a particular day"""
        if self.dialog.dirty:
            # user is editing a field so we don't allow edit
            wxBell()
        else:
            self.dialog.setdate(year, month, day)
            self.dialog.Show(True)
            
    def populate(self, dict):
        """Updates the internal data with the contents of C{dict['calendar']}"""
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
                # we could pay attention to daybitmap here ...
                entry['dayofweek']=(calendar.weekday(y,m,d)+1)%7
            self.repeating.append(entry)

        self.RefreshAllEntries()

    def populatefs(self, dict):
        """Saves the dict to disk"""
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

        d={}
        d['calendar']=dict['calendar']
        common.writeversionindexfile(os.path.join(self.thedir, "index.idx"), d, self.CURRENTFILEVERSION)
        return dict

    def getfromfs(self, dict):
        """Updates dict with info from disk

        @Note: The dictionary passed in is modified, as well
        as returned
        @rtype: dict
        @param dict: the dictionary to update
        @return: the updated dictionary"""
        self.thedir=self.mainwindow.calendarpath
        try:
            os.makedirs(self.thedir)
        except:
            pass
        if not os.path.isdir(self.thedir):
            raise Exception("Bad directory for calendar '"+self.thedir+"'")
        if os.path.exists(os.path.join(self.thedir, "index.idx")):
            d={'result': {}}
            common.readversionedindexfile(os.path.join(self.thedir, "index.idx"), d, self.versionupgrade, self.CURRENTFILEVERSION)
            dict.update(d['result'])
        else:
            dict['calendar']={}
        return dict

    def versionupgrade(self, dict, version):
        """Upgrade old data format read from disk

        @param dict:  The dict that was read in
        @param version: version number of the data on disk
        """

        # version 0 to 1 upgrade
        if version==0:
            version=1  # they are the same

        # 1 to 2 
        if version==1:
            # ?d field renamed daybitmap
            version=2
            for k in dict['result']['calendar']:
                entry=dict['result']['calendar'][k]
                entry['daybitmap']=self.getdaybitmap(entry['start'], entry['repeat'])
                del entry['?d']

        # 2 to 3 etc


class DayViewDialog(wxDialog):
    """Used to edit the entries on one particular day"""

    # ids for the various controls
    ID_PREV=1
    ID_NEXT=2
    ID_ADD=3
    ID_DELETE=4
    ID_CLOSE=5
    ID_LISTBOX=6
    ID_START=7
    ID_END=8
    ID_REPEAT=9
    ID_DESCRIPTION=10
    ID_SAVE=11
    ID_HELP=12
    ID_REVERT=13

    # results on asking if the user wants to change the original (repeating) entry, just
    # this instance, or cancel
    ANSWER_ORIGINAL=1
    ANSWER_THIS=2
    ANSWER_CANCEL=3

    def __init__(self, parent, calendarwidget, id=-1, title="Edit Calendar"):
        # This method is a good illustration of why people use gui designers :-)
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
        'alarm', 'ringtone', 'changeserial', 'snoozedelay')
        
        self.fielddesc=( 'Description', 'Start', 'End', 'Repeat',
        'Alarm', 'Ringtone', 'changeserial', 'Snooze Delay' )

        # right hand bit with all fields
        gs=wxFlexGridSizer(-1,2,5,5)
        gs.AddGrowableCol(1)
        self.fields={}
        for desc,field in zip(self.fielddesc, self.fieldnames):
            t=wxStaticText(self, -1, desc, style=wxALIGN_LEFT)
            gs.Add(t)
            if field=='start':
                c=DVDateTimeControl(self,self.ID_START)
            elif field=='end':
                c=DVDateTimeControl(self,self.ID_END)
            elif field=='repeat':
                c=DVRepeatControl(self, self.ID_REPEAT)
            elif field=='description':
                c=DVTextControl(self, self.ID_DESCRIPTION, "dummy")
            else:
                print "field",field,"needs an id"
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

        # delete is disabled until an item is selected
        self.FindWindowById(self.ID_DELETE).Enable(False)

        EVT_LISTBOX(self, self.ID_LISTBOX, self.OnListBoxItem)
        EVT_LISTBOX_DCLICK(self, self.ID_LISTBOX, self.OnListBoxItem)
        EVT_BUTTON(self, self.ID_SAVE, self.OnSaveButton)
        EVT_BUTTON(self, self.ID_REVERT, self.OnRevertButton)
        EVT_BUTTON(self, self.ID_CLOSE, self.OnCloseButton)
        EVT_BUTTON(self, self.ID_ADD, self.OnNewButton)
        EVT_BUTTON(self, self.ID_DELETE, self.OnDeleteButton)
        EVT_BUTTON(self, self.ID_HELP, lambda _: wxGetApp().displayhelpid(helpids.ID_EDITING_CALENDAR_EVENTS))
        EVT_BUTTON(self, self.ID_PREV, self.OnPrevDayButton)
        EVT_BUTTON(self, self.ID_NEXT, self.OnNextDayButton)

        # this is allegedly called automatically but didn't work for me
        EVT_CLOSE(self, self.OnCloseWindow)

        # Tracking of the entries in the listbox.  Each entry is a dict. Entries are just the
        # entries in a random order.  entrymap maps from the order in the listbox to a
        # specific entry
        self.entries=[]
        self.entrymap=[]

        # Dirty tracking.  We restrict what the user can do while editting an
        # entry to only be able to edit that entry.  'dirty' gets fired when
        # they make any updates.  Annoyingly, controls generate change events
        # when they are updated programmatically as well as by user interaction.
        # ignoredirty is set when we are programmatically updating controls
        self.dirty=None
        self.ignoredirty=False 
        self.setdirty(False)

    def AskAboutRepeatDelete(self):
        """Asks the user if they wish to delete the original (repeating) entry, or this instance

        @return: An C{ANSWER_} constant
        """
        return self._AskAboutRecurringEvent("Delete recurring event?", "Do you want to delete all the recurring events, or just this one?", "Delete")

    def AskAboutRepeatChange(self):
        """Asks the user if they wish to change the original (repeating) entry, or this instance

        @return: An C{ANSWER_} constant
        """
        return self._AskAboutRecurringEvent("Change recurring event?", "Do you want to change all the recurring events, or just this one?", "Change")

    def _AskAboutRecurringEvent(self, caption, text, prefix):
        dlg=RecurringDialog(self, caption, text, prefix)
        res=dlg.ShowModal()
        dlg.Destroy()
        if res==dlg.ID_THIS:
            return self.ANSWER_THIS
        if res==dlg.ID_ALL:
            return self.ANSWER_ORIGINAL
        if res==dlg.ID_CANCEL:
            return self.ANSWER_CANCEL
        assert False

    def OnListBoxItem(self, _=None):
        """Callback for when user clicks on an event in the listbox"""
        self.updatefields(self.getcurrententry())
        self.setdirty(False)
        self.FindWindowById(self.ID_DELETE).Enable(True)

    def getcurrententry(self):
        """Returns the entry currently being viewed

        @Note: this returns the unedited form of the entry"""
        return self.getentry(self.listbox.GetSelection())

    def getentry(self, num):
        """maps from entry number in listbox to an entry in entries

        @type num: int
        @rtype: entry(dict)"""
        return self.entries[self.entrymap[num]]

    def OnSaveButton(self, _=None):
        """Callback for when user presses save"""

        # check if the dates are ok
        for x in 'start', 'end':
            if not self.fields[x].IsValid():
                self.fields[x].SetFocus()
                wxBell()
                return

        # whine if end is before start
        start=self.fields['start'].GetValue()
        end=self.fields['end'].GetValue()

        # I want metric time!
        if ( end[0]<start[0] ) or \
           ( end[0]==start[0] and end[1]<start[1] ) or \
           ( end[0]==start[0] and end[1]==start[1] and end[2]<start[2] ) or \
           ( end[0]==start[0] and end[1]==start[1] and end[2]==start[2] and end[3]<start[3] ) or \
           ( end[0]==start[0] and end[1]==start[1] and end[2]==start[2] and end[3]==start[3] and end[4]<start[4] ):
            # scold the user
            dlg=wxMessageDialog(self, "End date and time is before start!", "Time Travel Attempt Detected",
                                wxOK|wxICON_EXCLAMATION)
            dlg.ShowModal()
            dlg.Destroy()
            # move focus
            self.fields['end'].SetFocus()
            return

        # lets roll ..
        entry=self.getcurrententry()

        # is it a repeat?
        res=self.ANSWER_ORIGINAL
        if entry['repeat'] is not None:
            # ask the user
            res=self.AskAboutRepeatChange()
            if res==self.ANSWER_CANCEL:
                return
        # where do we get newentry template from?
        if res==self.ANSWER_ORIGINAL:
            newentry=copy.copy(entry)
            # this will have no effect until we don't display the changeserial field
            newentry['changeserial']=entry['changeserial']+1
        else:
            newentry=self.cw.newentryfactory(*self.date)

        # update the fields
        for f in self.fields:
            control=self.fields[f]
            if isinstance(control, DVDateTimeControl):
                # which date do we use?
                if res==self.ANSWER_ORIGINAL:
                    d=control.GetValue()[0:3]
                else:
                    d=self.date
                v=list(d)+list(control.GetValue())[3:]
            else:
                v=control.GetValue()

            # if we are changing a repeat, reset the new entry's repeat is off
            if f=='repeat' and res==self.ANSWER_THIS:
                v=None
 
            newentry[f]=v

        # update the daybitmap field
        newentry['daybitmap']=self.cw.getdaybitmap(newentry['start'], newentry['repeat'])

        # update calendar widget
        if res==self.ANSWER_ORIGINAL:
            self.cw.ChangeEntry(entry, newentry)
        else:
            # delete the repeat and add this new entry
            self.cw.DeleteEntryRepeat(entry, *self.date)
            self.cw.AddEntry(newentry)

        # tidy up
        self.setdirty(False)
        # did the user change the date on us?
        date=tuple(newentry['start'][:3])
        if tuple(self.date)!=date:
            self.cw.showday(*date)
            self.cw.setselection(*date)
            self.setdate(*date)
        else:
            self.refreshentries()
        self.updatelistbox(newentry['pos'])

    def OnPrevDayButton(self, _):
        y,m,d=self.date
        y,m,d=calendarcontrol.normalizedate(y,m,d-1)
        self.setdate(y,m,d)
        self.cw.setday(y,m,d)

    def OnNextDayButton(self, _):
        y,m,d=self.date
        y,m,d=calendarcontrol.normalizedate(y,m,d+1)
        self.setdate(y,m,d)
        self.cw.setday(y,m,d)

    def OnNewButton(self, _=None):
        entry=self.cw.newentryfactory(*self.date)
        self.cw.AddEntry(entry)
        self.refreshentries()
        self.updatelistbox(entry['pos'])

    def OnRevertButton(self, _=None):
        # We basically pretend the user has selected the item in the listbox again (which they
        # can't actually do as it is disabled)
        self.OnListBoxItem()

    def OnDeleteButton(self, _=None):
        entry=self.getcurrententry()
        # is it a repeat?
        res=self.ANSWER_ORIGINAL
        if entry['repeat'] is not None:
            # ask the user
            res=self.AskAboutRepeatDelete()
            if res==self.ANSWER_CANCEL:
                return
        enum=self.listbox.GetSelection()
        if enum+1<len(self.entrymap):
            # try and find entry after current one
            newpos=self.getentry(enum+1)['pos']
        elif enum-1>=0:
            # entry before as we are deleting last entry
            newpos=self.getentry(enum-1)['pos']
        else:
            newpos=None
        if res==self.ANSWER_ORIGINAL:
            self.cw.DeleteEntry(entry)
        else:
            self.cw.DeleteEntryRepeat(entry, *self.date)
        self.refreshentries()
        self.updatelistbox(newpos)
        
    def OnCloseWindow(self, event):
        # only allow closing to happen if the close button is
        # enabled
        if self.FindWindowById(self.ID_CLOSE).IsEnabled():
            self.Show(False)
        else:
            # veto it if allowed
            if event.CanVeto():
                event.Veto()
                wxBell()

    def OnCloseButton(self, _=None):
        self.Show(False)

    def setdate(self, year, month, day):
        """Sets the date we are editing entries for

        @Note: The list of entries is updated"""
        d=time.strftime("%A %d %B %Y", (year,month,day,0,0,0, calendar.weekday(year,month,day),1, 0))
        self.date=year,month,day
        self.title.SetLabel(d)
        self.refreshentries()
        self.updatelistbox()
        self.updatefields(None)

    def refreshentries(self):
        """re-requests the list of entries for the currently visible date from the main calendar"""
        self.entries=self.cw.getentrydata(*self.date)

    def updatelistbox(self, entrytoselect=None):
        """
        Updates the contents of the listbox.  It will re-sort the contents.

        @param entrytoselect: The integer id of an entry to select.  Note that
                              this is an event id, not an index
        """
        self.listbox.Clear()
        selectitem=-1
        self.entrymap=[]
        # decorate
        for index, entry in zip(range(len(self.entries)), self.entries):
            e=( entry['start'][3:5], entry['end'][3:5], entry['description'], entry['pos'],  index)
            self.entrymap.append(e)
        # time ordered
        self.entrymap.sort()
        # now undecorate
        self.entrymap=[index for ign0, ign1, ign2, ign3, index in self.entrymap]
        # add listbox entries
        for curpos, index in zip(range(len(self.entrymap)), self.entrymap):
            e=self.entries[index]
            if e['pos']==entrytoselect:
                selectitem=curpos
            if 0: # ampm/miltime config here ::TODO::
                str="%2d:%02d" % (e['start'][3], e['start'][4])
            else:
                hr=e['start'][3]
                ap="am"
                if hr>=12:
                    ap="pm"
                    hr-=12
                if hr==0: hr=12
                str="%2d:%02d %s" % (hr, e['start'][4], ap)
            str+=" "+e['description']
            self.listbox.Append(str)

        # Select an item if requested
        if selectitem>=0:
            self.listbox.SetSelection(selectitem)
            self.OnListBoxItem() # update fields
        else:
            # disable fields since nothing is selected
            self.updatefields(None)
            
        # disable delete if there are no entries!
        if len(self.entries)==0:
            self.FindWindowById(self.ID_DELETE).Enable(False)
            
    def updatefields(self, entry):
        self.ignoredirty=True
        active=True
        if entry is None:
            for i in self.fields:
                self.fields[i].SetValue(None)
            active=False
        else:
            for i in self.fieldnames:
                self.fields[i].SetValue(entry[i])

        # manipulate field widgets
        for i in self.fields:
            self.fields[i].Enable(active)

        self.ignoredirty=False

    # called from various widget update callbacks
    def OnMakeDirty(self, _=None):
        """A public function you can call that will set the dirty flag"""
        self.setdirty(True)

    def setdirty(self, val):
        """Set the dirty flag

        The various buttons in the dialog are enabled/disabled as appropriate
        for the new state.
        
        @type  val: Bool
        @param val: True to mark edit fields as different from entry (ie
                    editing has taken place)
                    False to make them as the same as the entry (ie no
                    editing or the edits have been discarded)
        """
        if self.ignoredirty:
            return
        self.dirty=val
        if self.dirty:
            # The data has been modified, so we only allow working
            # with this data
            
            # enable save, revert, delete
            self.FindWindowById(self.ID_SAVE).Enable(True)
            self.FindWindowById(self.ID_REVERT).Enable(True)
            self.FindWindowById(self.ID_DELETE).Enable(True)
            # disable close, left, right, new
            self.FindWindowById(self.ID_CLOSE).Enable(False)
            self.FindWindowById(self.ID_PREV).Enable(False)
            self.FindWindowById(self.ID_NEXT).Enable(False)
            self.FindWindowById(self.ID_ADD).Enable(False)
            # can't play with listbox now
            self.FindWindowById(self.ID_LISTBOX).Enable(False)
        else:
            # The data is now clean and saved/reverted or deleted
            
            # disable save, revert,
            self.FindWindowById(self.ID_SAVE).Enable(False)
            self.FindWindowById(self.ID_REVERT).Enable(False)

            # enable delete, close, left, right, new
            self.FindWindowById(self.ID_CLOSE).Enable(True)
            self.FindWindowById(self.ID_DELETE).Enable(len(self.entries)>0) # only enable if there are entries
            self.FindWindowById(self.ID_PREV).Enable(True)
            self.FindWindowById(self.ID_NEXT).Enable(True)
            self.FindWindowById(self.ID_ADD).Enable(True)

            # can choose another item in listbox
            self.FindWindowById(self.ID_LISTBOX).Enable(True)



# We derive from wxPanel not the control directly.  If we derive from
# wxMaskedTextCtrl then all hell breaks loose as our {Get|Set}Value
# methods make the control malfunction big time
class DVDateTimeControl(wxPanel):
    """A datetime control customised to work in the dayview editor"""
    def __init__(self,parent,id):
        f="EUDATETIMEYYYYMMDD.HHMM"
        wxPanel.__init__(self, parent, -1)
        self.c=wxMaskedTextCtrl(self, id, "",
                                autoformat=f)
        bs=wxBoxSizer(wxHORIZONTAL)
        bs.Add(self.c,0,wxEXPAND)
        self.SetSizer(bs)
        self.SetAutoLayout(True)
        bs.Fit(self)
        EVT_TEXT(self.c, id, parent.OnMakeDirty)

    def SetValue(self, v):
        if v is None:
            self.c.SetValue("")
            return
        ap="A"
        v=list(v)
        if v[3]>12:
            v[3]-=12
            ap="P"
        elif v[3]==0:
            v[3]=12
        elif v[3]==12:
            ap="P"
        v=v+[ap]

        # we have to supply what the user would type without the punctuation
        # (try figuring that out from the "doc")
        str="%04d%02d%02d%02d%02d%s" % tuple(v)
        self.c.SetValue( str )
        self.c.Refresh()

    def GetValue(self):
        # The actual value including all punctuation is returned
        # GetPlainValue can get it with all digits run together
        str=self.c.GetValue()
        digits="0123456789"

        # turn it back into a list
        res=[]
        val=None
        for i in str:
            if i in digits:
                if val is None: val=0
                val*=10
                val+=int(i)
            else:
                if val is not None:
                    res.append(val)
                    val=None
        # fixup am/pm
        if str[-2]=='P' or str[-2]=='p':
            if res[3]!=12: # 12pm is midday and left alone
                res[3]+=12
        elif res[3]==12: # 12 am
            res[3]=0

        return res

    def IsValid(self):
        return self.c.IsValid()
    
class DVRepeatControl(wxChoice):
    """Shows the calendar repeat values"""
    vals=[None, "daily", "monfri", "weekly", "monthly", "yearly"]
    desc=["None", "Daily", "Mon - Fri", "Weekly", "Monthly", "Yearly" ]

    def __init__(self, parent, id):
        wxChoice.__init__(self, parent, id, choices=self.desc)
        EVT_CHOICE(self, id, parent.OnMakeDirty)

    def SetValue(self, v):
        assert v in self.vals
        self.SetSelection(self.vals.index(v))

    def GetValue(self):
        s=self.GetSelection()
        if s<0: s=0
        return self.vals[s]

class DVIntControl(wxIntCtrl):
    # shows integer values
    def __init__(self, parent, id):
        wxIntCtrl.__init__(self, parent, id, limited=True)
        EVT_INT(self, id, parent.OnMakeDirty)

    def SetValue(self, v):
        if v is None:
            v=-1
        wxIntCtrl.SetValue(self,v)
        
class DVTextControl(wxTextCtrl):
    def __init__(self, parent, id, value=""):
        if value is None:
            value=""
        wxTextCtrl.__init__(self, parent, id, value)
        EVT_TEXT(self, id, parent.OnMakeDirty)

    def SetValue(self, v):
        if v is None: v=""
        wxTextCtrl.SetValue(self,v)


###
### Dialog box for asking the user what they want to for a recurring event.
### Used when saving changes or deleting entries in the DayViewDialog
###

class RecurringDialog(wxDialog):
    """Ask the user what they want to do about a recurring event

    You should only use this as a modal dialog.  ShowModal() will
    return one of:

      - ID_THIS:   change just this event
      - ID_ALL:    change all events
      - ID_CANCEL: user cancelled dialog"""
    ID_THIS=1
    ID_ALL=2
    ID_CANCEL=3
    ID_HELP=4 # hide from epydoc

    def __init__(self, parent, caption, text, prefix):
        """Constructor

        @param parent: frame to parent this to
        @param caption: caption of the dialog (eg C{"Change recurring event?"})
        @param text: text displayed in the dialog (eg C{"This is a recurring event.  What would you like to change?"})
        @param prefix: text prepended to the buttons (eg the button says " this" so the prefix would be "Change" or "Delete")
        """
        wxDialog.__init__(self, parent, -1, caption,
                          style=wxCAPTION)

        # eveything sits inside a vertical box sizer
        vbs=wxBoxSizer(wxVERTICAL)

        # the explanatory text
        t=wxStaticText(self, -1, text)
        vbs.Add(t, 1, wxEXPAND|wxALL,10)

        # horizontal line
        vbs.Add(wxStaticLine(self, -1), 0, wxEXPAND|wxTOP|wxBOTTOM, 3)

        # buttons at bottom
        buttonsizer=wxBoxSizer(wxHORIZONTAL)
        for id, label in (self.ID_THIS,   "%s %s" % (prefix, "this")), \
                         (self.ID_ALL,    "%s %s" % (prefix, "all")), \
                         (self.ID_CANCEL, "Cancel"), \
                         (self.ID_HELP,   "Help"):
            b=wxButton(self, id, label)
            EVT_BUTTON(self, id, self._onbutton)
            buttonsizer.Add(b, 5, wxALIGN_CENTER|wxALL, 5)

        # plumb in sizers
        vbs.Add(buttonsizer, 0, wxEXPAND|wxALL,2)
        self.SetSizer(vbs)
        self.SetAutoLayout(True)
        vbs.Fit(self)


    def _onbutton(self, evt):
        if evt.GetId()==self.ID_HELP:
            pass # :::TODO::: some sort of help ..
        else:
            self.EndModal(evt.GetId())

###
### A dialog showing a message in a fixed font, with a help button
###

class MyFixedScrolledMessageDialog(wxDialog):
    """A dialog displaying a readonly text control with a fixed width font"""
    def __init__(self, parent, msg, caption, helpid, pos = wxDefaultPosition, size = (850,600)):
        wxDialog.__init__(self, parent, -1, caption, pos, size)

        text=wxTextCtrl(self, 1,
                        style=wxTE_MULTILINE | wxTE_READONLY | wxTE_RICH2 |
                        wxNO_FULL_REPAINT_ON_RESIZE|wxTE_DONTWRAP  )
        # Fixed width font
        f=wxFont(10, wxMODERN, wxNORMAL, wxNORMAL )
        ta=wxTextAttr(font=f)
        text.SetDefaultStyle(ta)

        text.AppendText(msg) # if i supply this in constructor then the font doesn't take
        text.SetInsertionPoint(0)
        text.ShowPosition(text.XYToPosition(0,0))

        # vertical sizer
        vbs=wxBoxSizer(wxVERTICAL)
        vbs.Add(text, 1, wxEXPAND|wxALL, 10)

        # buttons
        vbs.Add(self.CreateButtonSizer(wxOK|wxHELP), 0, wxALIGN_RIGHT|wxALL, 10)

        # plumb
        self.SetSizer(vbs)
        self.SetAutoLayout(True)
        EVT_BUTTON(self, wxID_HELP, lambda _,helpid=helpid: wxGetApp().displayhelpid(helpid))

###
###  Dialog that deals with exceptions
###
import StringIO

class ExceptionDialog(MyFixedScrolledMessageDialog):
    def __init__(self, frame, exception, title="Exception"):
        s=StringIO.StringIO()
        s.write("An unexpected exception has occurred.\nPlease see the help for details on what to do.\n\n")
        if hasattr(exception, 'gui_exc_info'):
            s.write(common.formatexception(exception.gui_exc_info))
        else:
            s.write("Exception with no extra info.\n%s\n" % (exception.str(),))
        self._text=s.getvalue()
        MyFixedScrolledMessageDialog.__init__(self, frame, s.getvalue(), title, helpids.ID_EXCEPTION_DIALOG)

    def getexceptiontext(self):
        return self._text

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
        if len(desc) and max:
            str="%d/%d %s" % (pos+1, max, desc)
        else:
            str=desc
        self.SetStatusText(str,1)

###
###  A MessageBox with a help button
###

class AlertDialogWithHelp(wxDialog):
    """A dialog box with Ok button and a help button"""
    def __init__(self, parent, message, caption, helpfn, style=wxDEFAULT_DIALOG_STYLE, icon=wxICON_EXCLAMATION):
        wxDialog.__init__(self, parent, -1, caption, style=style|wxDEFAULT_DIALOG_STYLE)

        p=self # parent widget

        # horiz sizer for bitmap and text
        hbs=wxBoxSizer(wxHORIZONTAL)
        hbs.Add(wxStaticBitmap(p, -1, wxArtProvider_GetBitmap(self.icontoart(icon), wxART_MESSAGE_BOX)), 0, wxCENTER|wxALL, 10)
        hbs.Add(wxStaticText(p, -1, message), 1, wxCENTER|wxALL, 10)

        # the buttons
        buttsizer=self.CreateButtonSizer(wxHELP|style)

        # Both vertical
        vbs=wxBoxSizer(wxVERTICAL)
        vbs.Add(hbs, 1, wxEXPAND|wxALL, 10)
        vbs.Add(buttsizer, 0, wxCENTER|wxALL, 10)

        # wire it in
        self.SetSizer(vbs)
        self.SetAutoLayout(True)
        vbs.Fit(self)

        EVT_BUTTON(self, wxID_HELP, helpfn)

    def icontoart(self, id):
        if id&wxICON_EXCLAMATION:
            return wxART_WARNING
        if id&wxICON_INFORMATION:
            return wxART_INFORMATION
        # ::TODO:: rest of these
        # fallthru
        return wxART_INFORMATION

###
### Yet another dialog with user selectable buttons
###

class AnotherDialog(wxDialog):
    """A dialog box with user supplied buttons"""
    def __init__(self, parent, message, caption, buttons, helpfn=None,
                 style=wxDEFAULT_DIALOG_STYLE, icon=wxICON_EXCLAMATION):
        """Constructor

        @param message:  Text displayed in body of dialog
        @param caption:  Title of dialog
        @param buttons:  A list of tuples.  Each tuple is a string and an integer id.
                         The result of calling ShowModal() is the id
        @param helpfn:  The function called if the user presses the help button (wxID_HELP)
        """
        wxDialog.__init__(self, parent, -1, caption, style=style)

        p=self # parent widget

        # horiz sizer for bitmap and text
        hbs=wxBoxSizer(wxHORIZONTAL)
        hbs.Add(wxStaticBitmap(p, -1, wxArtProvider_GetBitmap(self.icontoart(icon), wxART_MESSAGE_BOX)), 0, wxCENTER|wxALL, 10)
        hbs.Add(wxStaticText(p, -1, message), 1, wxCENTER|wxALL, 10)

        # the buttons
        buttsizer=wxBoxSizer(wxHORIZONTAL)
        for label,id in buttons:
            buttsizer.Add( wxButton(self, id, label), 0, wxALL|wxALIGN_CENTER, 5)
            if id!=wxID_HELP:
                EVT_BUTTON(self, id, self.OnButton)
            else:
                EVT_BUTTON(self, wxID_HELP, helpfn)
                
        # Both vertical
        vbs=wxBoxSizer(wxVERTICAL)
        vbs.Add(hbs, 1, wxEXPAND|wxALL, 10)
        vbs.Add(buttsizer, 0, wxCENTER|wxALL, 10)

        # wire it in
        self.SetSizer(vbs)
        self.SetAutoLayout(True)
        vbs.Fit(self)

    def OnButton(self, event):
        self.EndModal(event.GetId())

    def icontoart(self, id):
        if id&wxICON_EXCLAMATION:
            return wxART_WARNING
        if id&wxICON_INFORMATION:
            return wxART_INFORMATION
        # ::TODO:: rest of these
        # fallthru
        return wxART_INFORMATION

### BITPIM
###
### Copyright (C) 2003 Roger Binns <rogerb@rogerbinns.com>
###
### This software is under the Artistic license.
### http://www.opensource.org/licenses/artistic-license.php
###
### $Id$


# System modules
import thread, threading
import Queue
import time
import os

# wxPython modules
from wxPython.wx import *
from wxPython.lib.dialogs import wxScrolledMessageDialog
from wxPython.lib import colourdb

# my modules
import guiwidgets
import common
import version

###
### Used to check our threading
###
mainthreadid=thread.get_ident()
helperthreadid=-1 # set later

###
### The various IDs we use.  Code below munges the integers into sequence
###

# Main menu items

ID_FILENEW=1
ID_FILEOPEN=1
ID_FILESAVE=1
ID_FILEPRINT=1
ID_FILEPRINTPREVIEW=1
ID_FILEEXIT=1
ID_EDITADDENTRY=1
ID_EDITDELETEENTRY=1
ID_EDITSETTINGS=1
ID_DATAGETPHONE=1
ID_DATASENDPHONE=1
ID_VIEWLOGDATA=1
ID_VIEWFILESYSTEM=1
ID_HELPHELP=1
ID_HELPABOUT=1

# alter files viewer modes
ID_FV_ICONS=1
ID_FV_LIST=1

# file/filesystem viewer context menus
ID_FV_SAVE=1
ID_FV_HEXVIEW=1
ID_FV_OVERWRITE=1
ID_FV_NEWSUBDIR=1
ID_FV_NEWFILE=1
ID_FV_DELETE=1
ID_FV_OPEN=1
ID_FV_RENAME=1
ID_FV_REFRESH=1
ID_FV_PROPERTIES=1
ID_FV_ADD=1


# keep map around
idmap={}
# Start at 2 (if anything ends up being one then this code didn't spot it
idnum=2
for idmapname in locals().keys():
    if len(idmapname)>3 and idmapname[0:3]=='ID_':
        locals()[idmapname]=idnum
        idmap[idnum]=idmapname
        idnum+=1


###
### Implements a nice flexible callback object
###

class Callback:
    "Callback class.  Extra arguments can be supplied at call time"
    def __init__(self, method, *args, **kwargs):
        if __debug__:
            global mainthreadid
            assert mainthreadid==thread.get_ident()
        self.method=method
        self.args=args
        self.kwargs=kwargs

    def __call__(self, *args, **kwargs):
        if __debug__:
            global mainthreadid
            assert mainthreadid==thread.get_ident()
        d=self.kwargs.copy()
        d.update(kwargs)
        apply(self.method, self.args+args, d)

class Request:
    def __init__(self, method, *args, **kwargs):
        # created in main thread
        if __debug__:
            global mainthreadid
            assert mainthreadid==thread.get_ident()
        self.method=method
        self.args=args
        self.kwargs=kwargs

    def __call__(self, *args, **kwargs):
        # called in helper thread
        if __debug__:
            global helperthreadid
            assert helperthreadid==thread.get_ident()
        d=self.kwargs.copy()
        d.update(kwargs)
        return apply(self.method, self.args+args, d)
        

###
### Event used for passing results back from helper thread
###

class HelperReturnEvent(wxPyEvent):
    def __init__(self, callback, *args, **kwargs):
        if __debug__:
            global helperthreadid
            assert helperthreadid==thread.get_ident()
        global wxEVT_CALLBACK
        wxPyEvent.__init__(self)
        self.SetEventType(wxEVT_CALLBACK)
        self.cb=callback
        self.args=args
        self.kwargs=kwargs

    def __call__(self):
        if __debug__:
            global mainthreadid
            assert mainthreadid==thread.get_ident()
        return apply(self.cb, self.args, self.kwargs)

###
### Our helper thread where all the work gets done
###

class WorkerThreadFramework(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self, name="BitPim helper")
        self.q=Queue.Queue()

    def setdispatch(self, dispatchto):
        self.dispatchto=dispatchto

    def checkthread(self):
        # Function to verify we are running in the correct
        # thread.  All functions in derived class should call this
        global helperthreadid
        assert helperthreadid==thread.get_ident()
        
    def run(self):
        global helperthreadid
        helperthreadid=thread.get_ident()
        first=1
        while 1:
            if not first:
                wxPostEvent(self.dispatchto, HelperReturnEvent(self.dispatchto.endbusycb))
            else:
                first=0
            item=self.q.get()
            wxPostEvent(self.dispatchto, HelperReturnEvent(self.dispatchto.startbusycb))
            call=item[0]
            resultcb=item[1]
            ex=None
            res=None
            try:
                res=call()
            except Exception,e:
                ex=e
                ex.gui_exc_info=sys.exc_info()
            wxPostEvent(self.dispatchto, HelperReturnEvent(resultcb, ex, res))
            if isinstance(ex, SystemExit):
                print "worker thread is exiting"
                raise ex

    def progressminor(self, pos, max, desc=""):
        wxPostEvent(self.dispatchto, HelperReturnEvent(self.dispatchto.progressminorcb, pos, max, desc))

    def progressmajor(self, pos, max, desc=""):
        wxPostEvent(self.dispatchto, HelperReturnEvent(self.dispatchto.progressmajorcb, pos, max, desc))

    def progress(self, pos, max, desc=""):
        self.progressminor(pos, max, desc)

    def log(self, str):
        if self.dispatchto.wantlog:
            wxPostEvent(self.dispatchto, HelperReturnEvent(self.dispatchto.logcb, str))

    def logdata(self, str, data):
        if self.dispatchto.wantlog:
            wxPostEvent(self.dispatchto, HelperReturnEvent(self.dispatchto.logdatacb, str, data))


###
###  Splash screen
###

thesplashscreen=None  # set to non-none if there is one

class MySplashScreen(wxSplashScreen):
    def __init__(self, app, config):
        self.app=app
        # how long are we going to be up for?
        time=config.ReadInt("splashscreentime", 4000)
        if time>0:
            bmp=getbitmap("splashscreen")
            self.drawnameandnumber(bmp)
            wxSplashScreen.__init__(self, bmp, wxSPLASH_CENTRE_ON_SCREEN|wxSPLASH_TIMEOUT,
                                    time,
                                    None, -1)
            wx.EVT_CLOSE(self, self.OnClose)
            self.Show()
            app.Yield(True)
            global thesplashscreen
            thesplashscreen=self
            return
        # timeout is <=0 so don't show splash screen
        self.goforit()

    def drawnameandnumber(self, bmp):
        dc=wxMemoryDC()
        dc.SelectObject(bmp)
        # where we start writing
        x=10
        y=20
        # Product name
        str=version.name
        dc.SetTextForeground( wxNamedColour("DARKORCHID4") )
        dc.SetFont( wxFont(30, wxSWISS, wxNORMAL, wxNORMAL) )
        w,h=dc.GetTextExtent(str)
        dc.DrawText(str, x, y)
        y+=h+5 
        # Version number
        str=version.versionstring
        dc.SetTextForeground( wxNamedColour("GREY20") )
        dc.SetFont( wxFont(20, wxSWISS, wxNORMAL, wxNORMAL) )
        w,h=dc.GetTextExtent(str)
        dc.DrawText(str, x+10, y)
        y+=h+5
        # all done
        dc.SelectObject(wxNullBitmap)

    def goforit(self):
        self.app.makemainwindow()
        
    def OnClose(self, evt):
        self.goforit()
        evt.Skip()

####
#### Main application class.  Runs the event loop etc
####            
wxEVT_CALLBACK=None
class MainApp(wxApp):
    def __init__(self, *args):
        wxApp.__init__(self, redirect=False, useBestVisual=True)
        sys.setcheckinterval(100)
        
    def OnInit(self):
        # Routine maintenance
        wxInitAllImageHandlers()
        colourdb.updateColourDB()
        
        # Thread stuff
        global mainthreadid
        mainthreadid=thread.get_ident()

        # Establish config stuff
        cfgstr='bitpim'
        if IsMSWindows():
            cfgstr="BitPim"  # nicely capitalized on Windows
        self.config=wxConfig(cfgstr, style=wxCONFIG_USE_LOCAL_FILE)

        global wxEVT_CALLBACK
        wxEVT_CALLBACK=wxNewEventType()

        # get the splash screen up
        splash=MySplashScreen(self, self.config)

        return True

    def makemainwindow(self):
        # make the main frame
        frame=MainWindow(None, -1, "BitPim", self.config)
        frame.Connect(-1, -1, wxEVT_CALLBACK, frame.OnCallback)

        # make the worker thread
        wt=WorkerThread()
        wt.setdispatch(frame)
        wt.setDaemon(1)
        wt.start()
        frame.wt=wt
        self.frame=frame
        self.SetTopWindow(frame)

    def OnExit(self):
        print "onexit"
        sys.excepthook=sys.__excepthook__
        self.config.Flush()

# Entry point
def run(*args):
    m=MainApp(*args)
    res=m.MainLoop()
    return res

###
### Main Window (frame) class
###

class MainWindow(wxFrame):
    def __init__(self, parent, id, title, config):
        wxFrame.__init__(self, parent, id, title,
                         style=wxDEFAULT_FRAME_STYLE|wxNO_FULL_REPAINT_ON_RESIZE)

        sys.excepthook=Callback(self.excepthook)
        ### plumbing, callbacks        
        self.wt=None # worker thread
        self.progressminorcb=Callback(self.OnProgressMinor)
        self.progressmajorcb=Callback(self.OnProgressMajor)
        self.logcb=Callback(self.OnLog)
        self.logdatacb=Callback(self.OnLogData)
        self.startbusycb=Callback(self.OnBusyStart)
        self.endbusycb=Callback(self.OnBusyEnd)

        ### random variables
        self.wantlog=1  # do we want to receive log information
        self.config=config
        self.progmajortext=""
        self.lw=None
        self.lwdata=None
        self.filesystemwidget=None
        
        ### Status bar

        sb=guiwidgets.MyStatusBar(self)
        self.SetStatusBar(sb)

        ### Menubar

        menuBar = wxMenuBar()
        self.SetMenuBar(menuBar)
        menu = wxMenu()
        menu.Append(ID_FILENEW,  "&New", "Start from new")
        menu.Append(ID_FILEOPEN, "&Open", "Open a file")
        menu.Append(ID_FILESAVE, "&Save", "Save your work")
        menu.AppendSeparator()
        menu.Append(ID_FILEPRINTPREVIEW, "Print P&review", "Print Preview")
        menu.Append(ID_FILEPRINT, "&Print", "Print")        
        menu.AppendSeparator()
        menu.Append(ID_FILEEXIT, "E&xit", "Close down this program")
        menuBar.Append(menu, "&File");
        menu=wxMenu()
        menu.Append(ID_EDITADDENTRY, "Add...", "Add an item")
        menu.Append(ID_EDITDELETEENTRY, "Delete", "Delete currently selected entry")
        menu.AppendSeparator()
        menu.Append(ID_FV_ICONS, "View as Images", "Show items as images")
        menu.Append(ID_FV_LIST, "View As List", "Show items as a report")
        menu.AppendSeparator()
        menu.Append(ID_EDITSETTINGS, "&Settings", "Edit settings")
        menuBar.Append(menu, "&Edit");

        menu=wxMenu()
        menu.Append(ID_DATAGETPHONE, "Get Phone &Data ...", "Loads data from the phone")
        menu.Append(ID_DATASENDPHONE, "&Send Phone Data ...", "Sends data to the phone")
        menuBar.Append(menu, "&Data")

        menu=wxMenu()
        menu.AppendCheckItem(ID_VIEWLOGDATA, "View protocol logging", "View protocol logging information")
        menu.AppendCheckItem(ID_VIEWFILESYSTEM, "View filesystem", "View filesystem on the phone")
        menuBar.Append(menu, "&View")
        

        menu=wxMenu()
        menu.Append(ID_HELPHELP, "&Help", "Start online help")
        menu.AppendSeparator()
        menu.Append(ID_HELPABOUT, "&About", "Display program information")
        menuBar.Append(menu, "&Help");

        ### notebook
        self.nb=wxNotebook(self,-1)

        ### notebook tabs
        self.phonewidget=guiwidgets.PhoneGrid(self, self.nb)
        self.nb.AddPage(self.phonewidget, "PhoneBook")
        self.wallpaperwidget=guiwidgets.WallpaperView(self, self.nb)
        self.nb.AddPage(self.wallpaperwidget, "Wallpaper")
        self.ringerwidget=guiwidgets.RingerView(self, self.nb)
        self.nb.AddPage(self.ringerwidget, "Ringers")
        self.calendarwidget=guiwidgets.Calendar(self, self.nb)
        self.nb.AddPage(self.calendarwidget, "Calendar")

        ### toolbar
        # self.tb=self.CreateToolBar(wxTB_HORIZONTAL|wxNO_BORDER|wxTB_FLAT)
        self.tb=self.CreateToolBar(wxTB_HORIZONTAL)
        sz=self.tb.GetToolBitmapSize()
        # The art names are the opposite way round than people would normally describe ...
        self.tb.AddSimpleTool(ID_FV_LIST, wxArtProvider_GetBitmap(wxART_REPORT_VIEW, wxART_TOOLBAR, sz),
                              "List View", "View items as a list")
        self.tb.AddSimpleTool(ID_FV_ICONS, wxArtProvider_GetBitmap(wxART_LIST_VIEW, wxART_TOOLBAR, sz),
                              "Icon View", "View items as icons")
        # You have to make this call for the toolbar to draw itself properly
        self.tb.Realize()

        ### logwindow (last notebook tab)
        self.lw=guiwidgets.LogWindow(self.nb)
        self.nb.AddPage(self.lw, "Log")

        ### persistent dialogs
        self.dlggetphone=guiwidgets.GetPhoneDialog(self, "Get Data from Phone")
        self.dlgsendphone=guiwidgets.SendPhoneDialog(self, "Send Data to Phone")

        ### Events we handle
        EVT_MENU(self, ID_FILEEXIT, self.OnExit)
        EVT_MENU(self, ID_EDITSETTINGS, self.OnEditSettings)
        EVT_MENU(self, ID_DATAGETPHONE, self.OnDataGetPhone)
        EVT_MENU(self, ID_DATASENDPHONE, self.OnDataSendPhone)
        EVT_MENU(self, ID_VIEWLOGDATA, self.OnViewLogData)
        EVT_MENU(self, ID_VIEWFILESYSTEM, self.OnViewFilesystem)
        EVT_MENU(self, ID_FV_LIST, self.OnFileViewList)
        EVT_MENU(self, ID_FV_ICONS, self.OnFileViewIcons)
        EVT_MENU(self, ID_EDITADDENTRY, self.OnEditAddEntry)
        EVT_MENU(self, ID_EDITDELETEENTRY, self.OnEditDeleteEntry)
        EVT_MENU(self, ID_HELPABOUT, self.OnHelpAbout)
        EVT_NOTEBOOK_PAGE_CHANGED(self, -1, self.OnNotebookPageChanged)
        EVT_CLOSE(self, self.OnClose)

        ### Lets go visible
        self.Show()

        ### Double check our size is meaningful, and make bigger
        ### if necessary (especially needed on Mac and Linux)
        if min(self.GetSize())<250:
            self.SetSize( (640, 480) )

        ### remove splash screen if there is one
        global thesplashscreen
        if thesplashscreen is not None:
            wxSafeYield()
            thesplashscreen.Show(False)

        ### Is config set?
        self.configdlg=guiwidgets.ConfigDialog(self, self)
        if self.configdlg.needconfig():
            if self.configdlg.ShowModal()!=wxID_OK:
                self.OnExit()
        self.configdlg.updatevariables()

        # Final widgets that depend on config
        lv=self.config.ReadInt("logviewdata", 0)
        if lv:
            menuBar.Check(ID_VIEWLOGDATA, 1)
            self.OnViewLogData(None)

        # Populate all widgets from disk
        self.OnPopulateEverythingFromDisk()

        # Fake event to update menus/toolbars
        self.OnNotebookPageChanged()


    def OnExit(self,_=None):
        self.Close()

    # It has been requested that we shutdown
    def OnClose(self, event):
        if not self.wt:
            # worker thread doesn't exist yet
            self.Destroy()
            return
        if event.CanVeto():
            # should we close? dirty data? prompt to save?
            pass # yup close for now
        # Shutdown helper thread
        self.MakeCall( Request(self.wt.exit), Callback(self.OnCloseResults) )

    def OnCloseResults(self, exception, _):
        assert isinstance(exception, SystemExit)
        # assume it worked
        self.Destroy()

    # about and help

    def OnHelpAbout(self,_):
        import version

        str="BitPim Version "+version.versionstring
        str+="\n\n"
        if len(version.extrainfo):
            str+=version.extrainfo+"\n\n"
        str+=version.contact

        d=wxMessageDialog(self, str, "About BitPim", wxOK|wxICON_INFORMATION)
        d.ShowModal()
        d.Destroy()
        
        

    def OnViewLogData(self, _):
        # toggle state of the log data
        logdatatitle="Protocol Log"
        if self.lwdata is None:
            self.lwdata=guiwidgets.LogWindow(self.nb)
            self.nb.AddPage(self.lwdata, logdatatitle)
            self.config.WriteInt("logviewdata", 1)
        else:
            self.lwdata=None
            for i in range(0,self.nb.GetPageCount()):
                if self.nb.GetPageText(i)==logdatatitle:
                    self.nb.DeletePage(i)
                    break
            self.config.WriteInt("logviewdata", 0)

    def OnViewFilesystem(self,_):
        # toggle filesystem view
        logtitle="Log"
        fstitle="Filesystem"
        if self.filesystemwidget is None:
            for i in range(0, self.nb.GetPageCount()):
                if self.nb.GetPageText(i)==logtitle:
                    self.filesystemwidget=FileSystemView(self, self.nb)
                    self.nb.InsertPage(i, self.filesystemwidget, fstitle, True)
                    return
            print "ooops"
            return
        self.filesystemwidget=None
        for i in range(0, self.nb.GetPageCount()):
            if self.nb.GetPageText(i)==fstitle:
                self.nb.DeletePage(i)
                return
        

    ### 
    ### Main bit for getting stuff from phone
    ###
    def OnDataGetPhone(self,_):
        dlg=self.dlggetphone
        if dlg.ShowModal()!=wxID_OK:
            return
        self.MakeCall(Request(self.wt.getdata, dlg),
                      Callback(self.OnDataGetPhoneResults))

    def OnDataGetPhoneResults(self, exception, results):
        if self.HandleException(exception): return
        self.OnLog(`results.keys()`)
        self.OnLog(`results['sync']`)
        # phonebook
        if results['sync'].has_key('phonebook'):
            v=results['sync'].has_key('phonebook')
            if v=='MERGE': raise Exception("Not implemented")
            self.phonewidget.clear()
            self.phonewidget.populatefs(results)
            self.phonewidget.populate(results)
        # wallpaper
        if results['sync'].has_key('wallpaper'):
            v=results['sync'].has_key('wallpaper')
            if v=='MERGE': raise Exception("Not implemented")
            self.wallpaperwidget.populatefs(results)
            self.wallpaperwidget.populate(results)
        # ringtone
        if results['sync'].has_key('ringtone'):
            v=results['sync'].has_key('ringtone')
            if v=='MERGE': raise Exception("Not implemented")
            self.ringerwidget.populatefs(results)
            self.ringerwidget.populate(results)
        # calendar
        if results['sync'].has_key('calendar'):
            v=results['sync'].has_key('calendar')
            if v=='MERGE': raise Exception("Not implemented")
            self.calendarwidget.populatefs(results)
            self.calendarwidget.populate(results)

            
    ###
    ### Main bit for sending data to the phone
    ###
    def OnDataSendPhone(self, _):
        dlg=self.dlgsendphone
        if dlg.ShowModal()!=wxID_OK:
            return
        data={}
        todo=[]
        funcscb=[]
        ### Calendar
        v=dlg.GetCalendarSetting()
        if v!=dlg.NOTREQUESTED:
            merge=True
            if v==dlg.OVERWRITE: merge=False
            self.calendarwidget.getdata(data)
            todo.append( (self.wt.writecalendar, "Calendar", merge) )
            # writing will modify data (especially index) so
            # we repopulate on return
            funcscb.append( self.calendarwidget.populatefs )
            funcscb.append( self.calendarwidget.populate )        
        ### Wallpaper
        v=dlg.GetWallpaperSetting()
        if v!=dlg.NOTREQUESTED:
            merge=True
            if v==dlg.OVERWRITE: merge=False
            self.wallpaperwidget.getdata(data)
            todo.append( (self.wt.writewallpaper, "Wallpaper", merge) )
            # writing will modify data (especially index) so
            # we repopulate on return
            funcscb.append( self.wallpaperwidget.populatefs )
            funcscb.append( self.wallpaperwidget.populate )
        ### Ringtone
        v=dlg.GetRingtoneSetting()
        if v!=dlg.NOTREQUESTED:
            merge=True
            if v==dlg.OVERWRITE: merge=False
            self.ringerwidget.getdata(data)
            todo.append( (self.wt.writeringtone, "Ringtone", merge) )
            # writing will modify data (especially index) so
            # we repopulate on return
            funcscb.append( self.ringerwidget.populatefs )
            funcscb.append( self.ringerwidget.populate )

        ### Phonebook
        v=dlg.GetPhoneBookSetting()
        if v!=dlg.NOTREQUESTED:
            if v==dlg.OVERWRITE: 
                self.phonewidget.getdata(data)
                todo.append( (self.wt.writephonebook, "Phonebook") )

        self.MakeCall(Request(self.wt.senddata, data, todo),
                      Callback(self.OnDataSendPhoneResults, funcscb))


    def OnDataSendPhoneResults(self, funcscb, exception, results):
        if self.HandleException(exception): return
        for f in funcscb:
            f(results)
                
    # Get data from disk
    def OnPopulateEverythingFromDisk(self,_=None):
        results={}
        # get info
        self.phonewidget.getfromfs(results)
        self.wallpaperwidget.getfromfs(results)
        self.ringerwidget.getfromfs(results)
        self.calendarwidget.getfromfs(results)
        # update controls
        self.phonewidget.populate(results)
        self.wallpaperwidget.populate(results)
        self.ringerwidget.populate(results)
        self.calendarwidget.populate(results)

        
    # deal with configuring the phone (commport)
    def OnEditSettings(self, _=None):
        self.configdlg.ShowModal()

    # deal with graying out/in menu items on notebook page changing
    def OnNotebookPageChanged(self, _=None):
        # is ringers or wallpaper viewable?
        widget=self.nb.GetPage(self.nb.GetSelection())
        if widget is self.ringerwidget or \
           widget is self.wallpaperwidget:
            enablefv=True
        else: enablefv=False
        if widget is self.ringerwidget or \
           widget is self.wallpaperwidget or \
           widget is self.phonewidget:
            enableedit=True
        else: enableedit=False
        
        if IsGtk():
            enablefv=False # crummy platform
            
        self.GetToolBar().EnableTool(ID_FV_ICONS, enablefv)
        self.GetToolBar().EnableTool(ID_FV_LIST, enablefv)
        self.GetMenuBar().Enable(ID_FV_ICONS, enablefv)
        self.GetMenuBar().Enable(ID_FV_LIST, enablefv)
        self.GetMenuBar().Enable(ID_EDITADDENTRY, enableedit)
        self.GetMenuBar().Enable(ID_EDITDELETEENTRY, enableedit)
         
    # Change how file viewer items are shown
    def OnFileViewList(self, _):
        self.nb.GetPage(self.nb.GetSelection()).setlistview()

    def OnFileViewIcons(self, _):
        self.nb.GetPage(self.nb.GetSelection()).seticonview()

    # add/delete entry in the current tab
    def OnEditAddEntry(self, evt):
        self.nb.GetPage(self.nb.GetSelection()).OnAdd(evt)

    def OnEditDeleteEntry(self, evt):
        self.nb.GetPage(self.nb.GetSelection()).OnDelete(evt)

    # Busy handling
    def OnBusyStart(self):
        self.SetStatusText("BUSY")
        wxBeginBusyCursor(wxStockCursor(wxCURSOR_ARROWWAIT))

    def OnBusyEnd(self):
        wxEndBusyCursor()
        self.SetStatusText("Ready")
        self.OnProgressMajor(0,1)


    # progress and logging
    def OnProgressMinor(self, pos, max, desc=""):
        self.GetStatusBar().progressminor(pos, max, desc)

    def OnProgressMajor(self, pos, max, desc=""):
        self.GetStatusBar().progressmajor(pos, max, desc)

    def OnLog(self, str):
        self.lw.log(str)
        if self.lwdata is not None:
            self.lwdata.log(str)

    def OnLogData(self, str, data):
        if self.lwdata is not None:
            self.lwdata.logdata(str,data)

    def excepthook(self, type, value, traceback):
        value.gui_exc_info=(type,value,traceback)
        self.HandleException(value)

    def HandleException(self, exception):
        """returns true if this function handled the exception
        and the caller should not do any further processing"""
        if exception is None: return 0
        assert isinstance(exception, Exception)
        text=None
        title=None
        style=None
        if isinstance(exception, common.CommsDeviceNeedsAttention):
            text="%s: %s" % (exception.device, exception.message)
            title="Device needs attention - "+exception.device
            style=wxOK|wxICON_INFORMATION
        elif isinstance(exception, common.CommsOpenFailure):
            text="%s: %s" % (exception.device, exception.message)
            title="Failed to open communications - "+exception.device
            style=wxOK|wxICON_INFORMATION
            
        if text is not None:
            dlg=wxMessageDialog(self,text, title, style=style)
            dlg.ShowModal()
            dlg.Destroy()
            return 1
        e=ExceptionDialog(self, exception)
        e.ShowModal()
        e.Destroy()
        return 1
        
    # plumbing for the multi-threading

    def OnCallback(self, event):
        assert isinstance(event, HelperReturnEvent)
        event()

    def MakeCall(self, request, cbresult):
        assert isinstance(request, Request)
        assert isinstance(cbresult, Callback)
        self.wt.q.put( (request, cbresult) )

###
### Container for midi files
###  

#class MidiFileList(wxListCtrl):
#    pass


###
###  Dialog that deals with exceptions
###
import StringIO
import traceback

class ExceptionDialog(wxScrolledMessageDialog):
    def __init__(self, frame, exception, title="Exception"):
        s=StringIO.StringIO()
        s.write("An unexpected exception has occurred.\nPlease report the following information to the developers\n\n")
        if hasattr(exception, 'gui_exc_info'):
            traceback.print_exception(exception.gui_exc_info[0],
                                      exception.gui_exc_info[1],
                                      exception.gui_exc_info[2],
                                      file=s)
        else:
            s.write("Exception with no extra info.\n%s\n" % (exception.str(),))

        wxScrolledMessageDialog.__init__(self, frame, s.getvalue(), title)

###
###  Class that does all the comms and other stuff in a seperate
###  thread.  
###

class WorkerThread(WorkerThreadFramework):
    def __init__(self):
        WorkerThreadFramework.__init__(self)
        self.commphone=None

    def exit(self):
        if __debug__: self.checkthread()
        for i in range(0,0):
            self.progressmajor(i, 2, "Shutting down helper thread")
            time.sleep(1)
        self.log("helper thread shut down")
        raise SystemExit("helper thread shutdown")
        
    def setupcomm(self):
        if __debug__: self.checkthread()
        if self.commphone is None:
            import commport
            if self.dispatchto.commportsetting is None or \
               len(self.dispatchto.commportsetting)==0:
                raise common.CommsNeedConfiguring("LGVX4400", "Comm port not configured")
            # ::TODO:: should have failsafe code here that releases comport if
            # phone module fails to load
            comport=commport.CommConnection(self, self.dispatchto.commportsetting)
            import com_lgvx4400
            self.commphone=com_lgvx4400.Phone(self, comport)


    def getdata(self, req):
        if __debug__: self.checkthread()
        self.setupcomm()
        results={}
        willcall=[]
        sync={}
        for i in (
            (req.GetPhoneBookSetting, self.commphone.getphonebook, "Phone Book", "phonebook"),
            (req.GetCalendarSetting, self.commphone.getcalendar, "Calendar", "calendar",),
            (req.GetWallpaperSetting, self.commphone.getwallpapers, "Wallpaper", "wallpaper"),
            (req.GetRingtoneSetting, self.commphone.getringtones, "Ringtones", "ringtone")):
            st=i[0]()
            if st==req.MERGE:
                sync[i[3]]="MERGE"
                willcall.append(i)
            elif st==req.OVERWRITE:
                sync[i[3]]="OVERWRITE"
                willcall.append(i)

        results['sync']=sync
        count=0
        for i in willcall:
            self.progressmajor(count, len(willcall), i[2])
            count+=1
            i[1](results)
        
        return results

    def senddata(self, dict, todo):
        count=0
        for xx in todo:
            func=xx[0]
            desc=xx[1]
            args=[dict]
            if len(xx)>2:
                args.extend(xx[2:])
            self.progressmajor(count,len(todo),desc)
            apply(func, args)
            count+=1
        return dict

    def writewallpaper(self, data, merge):
        if __debug__: self.checkthread()
        self.setupcomm()
        return self.commphone.savewallpapers(data, merge)

    def writeringtone(self, data, merge):
        if __debug__: self.checkthread()
        self.setupcomm()
        return self.commphone.saveringtones(data, merge)

    def writephonebook(self, data):
        if __debug__: self.checkthread()
        self.setupcomm()
        return self.commphone.savephonebook(data)

    # various file operations for the benefit of the filesystem viewer
    def dirlisting(self, path, recurse=0):
        if __debug__: self.checkthread()
        self.setupcomm()
        return self.commphone.getfilesystem(path, recurse)

    def getfile(self, path):
        if __debug__: self.checkthread()
        self.setupcomm()
        return self.commphone.getfilecontents(path)

    def rmfile(self,path):
        if __debug__: self.checkthread()
        self.setupcomm()
        return self.commphone.rmfile(path)

    def writefile(self,path,contents):
        if __debug__: self.checkthread()
        self.setupcomm()
        return self.commphone.writefile(path, contents)

    def mkdir(self,path):
        if __debug__: self.checkthread()
        self.setupcomm()
        return self.commphone.mkdir(path)

    def rmdir(self,path):
        if __debug__: self.checkthread()
        self.setupcomm()
        return self.commphone.rmdir(path)


class FileSystemView(wxTreeCtrl):
    # we have to add None objects to all nodes otherwise the tree control refuses
    # sort (somewhat lame imho)
    def __init__(self, mainwindow, parent, idd=-1):
        # I was using the id function hence idd instead of id
        wxTreeCtrl.__init__(self, parent, idd, style=wxWANTS_CHARS|wxTR_DEFAULT_STYLE)
        self.mainwindow=mainwindow
        self.root=self.AddRoot("/")
        self.SetPyData(self.root, None)
        self.SetItemHasChildren(self.root, True)
        self.SetPyData(self.AppendItem(self.root, "Retrieving..."), None)
        self.dirhash={ "": 1}
        EVT_TREE_ITEM_EXPANDED(self, idd, self.OnItemExpanded)
        EVT_TREE_ITEM_ACTIVATED(self,idd, self.OnItemActivated)

        self.filemenu=wxMenu()
        self.filemenu.Append(ID_FV_SAVE, "Save ...")
        self.filemenu.Append(ID_FV_HEXVIEW, "Hexdump")
        self.filemenu.AppendSeparator()
        self.filemenu.Append(ID_FV_DELETE, "Delete")
        self.filemenu.Append(ID_FV_OVERWRITE, "Overwrite ...")

        self.dirmenu=wxMenu()
        self.dirmenu.Append(ID_FV_NEWSUBDIR, "Make subdirectory ...")
        self.dirmenu.Append(ID_FV_NEWFILE, "New File ...")
        self.dirmenu.AppendSeparator()
        self.dirmenu.Append(ID_FV_REFRESH, "Refresh")
        self.dirmenu.AppendSeparator()
        self.dirmenu.Append(ID_FV_DELETE, "Delete")

        EVT_MENU(self.filemenu, ID_FV_SAVE, self.OnFileSave)
        EVT_MENU(self.filemenu, ID_FV_HEXVIEW, self.OnHexView)
        EVT_MENU(self.filemenu, ID_FV_DELETE, self.OnFileDelete)
        EVT_MENU(self.filemenu, ID_FV_OVERWRITE, self.OnFileOverwrite)
        EVT_MENU(self.dirmenu, ID_FV_NEWSUBDIR, self.OnNewSubdir)
        EVT_MENU(self.dirmenu, ID_FV_NEWFILE, self.OnNewFile)
        EVT_MENU(self.dirmenu, ID_FV_DELETE, self.OnDirDelete)
        EVT_MENU(self.dirmenu, ID_FV_REFRESH, self.OnDirRefresh)
        EVT_RIGHT_DOWN(self, self.OnRightDown)
        EVT_RIGHT_UP(self, self.OnRightUp)

    def OnRightUp(self, event):
        pt = event.GetPosition();
        item, flags = self.HitTest(pt)
        if flags & ( wxTREE_HITTEST_ONITEMBUTTON|wxTREE_HITTEST_ONITEMICON|wxTREE_HITTEST_ONITEMINDENT|wxTREE_HITTEST_ONITEMLABEL):
            # is it a file or a directory
            path=self.itemtopath(item)
            if path in self.dirhash:
                if self.dirhash[path]:
                    self.PopupMenu(self.dirmenu, pt)
                    return
            self.PopupMenu(self.filemenu, pt)
                    
    def OnRightDown(self,event):
        # You have to capture right down otherwise it doesn't feed you right up
        pt = event.GetPosition();
        item, flags = self.HitTest(pt)
        try:
            self.SelectItem(item)
        except:
            pass

    def OnItemActivated(self,_):
        # is it a file or a directory
        item=self.GetSelection()
        path=self.itemtopath(item)
        if path in self.dirhash:
            if self.dirhash[path]:
                # directory - we ignore
                return
        self.OnHexView(self)
        

    def OnItemExpanded(self, event):
        item=event.GetItem()
        self.OnDirListing(self.itemtopath(item))

    def OnDirListing(self, path):
        mw=self.mainwindow
        mw.MakeCall( Request(mw.wt.dirlisting, path),
                     Callback(self.OnDirListingResults, path) )

    def OnDirListingResults(self, path, exception, result):
        mw=self.mainwindow
        if mw.HandleException(exception): return
        item=self.pathtoitem(path)
        l=[]
        cookie=id(result)-10000
        child,cookie=self.GetFirstChild(item,cookie)
        for dummy in range(0,self.GetChildrenCount(item,False)):
            l.append(child)
            child,cookie=self.GetNextChild(item,cookie)
        # we now have a list of children in l
        for file in result:
            f=basename(file)
            found=None
            for i in l:
                if self.GetItemText(i)==f:
                    found=i
                    break
            made=0
            if found is None:
                found=self.AppendItem(item, f)
                self.SetPyData(found, None)
                made=1
            if result[file]['type']=='file':
                self.dirhash[result[file]['name']]=0
                self.SetItemHasChildren(found, False)
            else: # it is a directory
                self.dirhash[result[file]['name']]=1
                self.SetItemHasChildren(found, True)
                if made: # only add this for new items
                    self.SetPyData(self.AppendItem(found, "Retrieving..."), None)
        for i in l: # remove all children not present in result
            if not result.has_key(self.itemtopath(i)):
                self.Delete(i)
        self.SortChildren(item)

    def OnFileSave(self, _):
        path=self.itemtopath(self.GetSelection())
        mw=self.mainwindow
        mw.MakeCall( Request(mw.wt.getfile, path),
                     Callback(self.OnFileSaveResults, path) )
        
    def OnFileSaveResults(self, path, exception, contents):
        mw=self.mainwindow
        if mw.HandleException(exception): return
        bn=basename(path)
        ext=getextension(bn)
        if len(ext):
            ext="%s files (*.%s)|*.%s" % (ext.upper(), ext, ext)
        else:
            ext="All files|*"
        dlg=wxFileDialog(self, "Save File As", defaultFile=bn, wildcard=ext,
                             style=wxSAVE|wxOVERWRITE_PROMPT|wxCHANGE_DIR)
        if dlg.ShowModal()==wxID_OK:
            f=open(dlg.GetPath(), "wb")
            f.write(contents)
            f.close()
        dlg.Destroy()
        
    def OnHexView(self, _):
        path=self.itemtopath(self.GetSelection())
        mw=self.mainwindow
        mw.MakeCall( Request(mw.wt.getfile, path),
                     Callback(self.OnHexViewResults, path) )
        
    def OnHexViewResults(self, path, exception, result):
        mw=self.mainwindow
        if mw.HandleException(exception): return
        dlg=guiwidgets.FixedScrolledMessageDialog(self, common.datatohexstring(result), path+" Contents")
        dlg.Show()

    def OnFileDelete(self, _):
        path=self.itemtopath(self.GetSelection())
        mw=self.mainwindow
        mw.MakeCall( Request(mw.wt.rmfile, path),
                     Callback(self.OnFileDeleteResults, dirname(path)) )
        
    def OnFileDeleteResults(self, parentdir, exception, _):
        mw=self.mainwindow
        if mw.HandleException(exception): return
        self.OnDirListing(parentdir)

    def OnFileOverwrite(self,_):
        path=self.itemtopath(self.GetSelection())
        dlg=wxFileDialog(self, style=wxOPEN|wxHIDE_READONLY|wxCHANGE_DIR)
        if dlg.ShowModal()!=wxID_OK:
            dlg.Destroy()
            return
        infile=dlg.GetPath()
        f=open(infile, "rb")
        contents=f.read()
        f.close()
        mw=self.mainwindow
        mw.MakeCall( Request(mw.wt.writefile, path, contents),
                     Callback(self.OnFileOverwriteResults, dirname(path)) )
        dlg.Destroy()
        
    def OnFileOverwriteResults(self, parentdir, exception, _):
        mw=self.mainwindow
        if mw.HandleException(exception): return
        self.OnDirListing(parentdir)

    def OnNewSubdir(self, _):
        dlg=wxTextEntryDialog(self, "Subdirectory name?", "Create Subdirectory", "newfolder")
        if dlg.ShowModal()!=wxID_OK:
            dlg.Destroy()
            return
        parent=self.itemtopath(self.GetSelection())
        if len(parent):
            path=parent+"/"+dlg.GetValue()
        else:
            path=dlg.GetValue()
        mw=self.mainwindow
        mw.MakeCall( Request(mw.wt.mkdir, path),
                     Callback(self.OnNewSubdirResults, parent) )
        dlg.Destroy()
            
    def OnNewSubdirResults(self, parentdir, exception, _):
        mw=self.mainwindow
        if mw.HandleException(exception): return
        self.OnDirListing(parentdir)
        
    def OnNewFile(self,_):
        parent=self.itemtopath(self.GetSelection())
        dlg=wxFileDialog(self, style=wxOPEN|wxHIDE_READONLY|wxCHANGE_DIR)
        if dlg.ShowModal()!=wxID_OK:
            dlg.Destroy()
            return
        infile=dlg.GetPath()
        f=open(infile, "rb")
        contents=f.read()
        f.close()
        if len(parent):
            path=parent+"/"+os.path.basename(dlg.GetPath())
        else:
            path=os.path.basename(dlg.GetPath()) # you can't create files in root but I won't stop you
        mw=self.mainwindow
        mw.MakeCall( Request(mw.wt.writefile, path, contents),
                     Callback(self.OnNewFileResults, parent) )
        dlg.Destroy()
        
    def OnNewFileResults(self, parentdir, exception, _):
        mw=self.mainwindow
        if mw.HandleException(exception): return
        self.OnDirListing(parentdir)

    def OnDirDelete(self, _):
        path=self.itemtopath(self.GetSelection())
        mw=self.mainwindow
        mw.MakeCall( Request(mw.wt.rmdir, path),
                     Callback(self.OnDirDeleteResults, dirname(path)) )
        
    def OnDirDeleteResults(self, parentdir, exception, _):
        mw=self.mainwindow
        if mw.HandleException(exception): return
        self.OnDirListing(parentdir)

    def OnDirRefresh(self, _):
        path=self.itemtopath(self.GetSelection())
        self.OnDirListing(path)

    def itemtopath(self, item):
        if item==self.root: return ""
        res=self.GetItemText(item)
        while 1:
            parent=self.GetItemParent(item)
            if parent==self.root:
                return res
            item=parent
            res=self.GetItemText(item)+"/"+res

    def pathtoitem(self, path):
        if path=="": return self.root
        dirs=path.split('/')
        node=self.root
        for n in range(0, len(dirs)):
            cookie=id(node)-10000
            foundnode=None
            child,cookie=self.GetFirstChild(node,cookie)
            for dummy in range(0, self.GetChildrenCount(node, False)):
                d=self.GetItemText(child)
                if d==dirs[n]:
                    node=child
                    foundnode=node
                    break
                child,cookie=self.GetNextChild(node,cookie)
            if foundnode is not None:
                continue
            # make the node
            node=self.AppendItem(node, dirs[n])
            self.SetPyData(node, None)
        return node

###
### Various functions not attached to classes
###

# Filename functions.  These work on brew names which use forward slash /
# as the directory delimiter.  The builtin Python functions can't be used
# as they are platform specific (eg they use \ on Windows)

def getextension(str):
    """Returns the extension of a filename (characters after last period)

    An empty string is returned if the file has no extension.  The period
    character is not returned"""
    str=basename(str)
    if str.rfind('.')>=0:
        return str[str.rfind('.')+1:]
    return ""

def basename(str):
    """Returns the last part of the name (everything after last /)"""
    if str.rfind('/')<0: return str
    return str[str.rfind('/')+1:]

def dirname(str):
    """Returns everything before the last / in the name""" 
    if str.rfind('/')<0: return ""
    return str[:str.rfind('/')]

def HasFullyFunctionalListView():
    """Can the list view widget be switched between icon view and report views

    @rtype: Bool"""
    if IsMSWindows():
        return True
    return False

def IsMSWindows():
    """Are we running on Windows?

    @rtype: Bool"""
    return wxPlatform=='__WXMSW__'

def IsGtk():
    """Are we running on GTK (Linux)

    @rtype: Bool"""
    return wxPlatform=='__WXGTK__'

def getbitmap(name):
    """Gets a bitmap from the resource directory

    @rtype: wxBitmap
    """
    for ext in ("", ".png", ".jpg"):
        if os.path.exists(getresourcefile(name+ext)):
            return wxImage(getresourcefile(name+ext)).ConvertToBitmap()
    print "You need to make "+name+".png"
    return getbitmap('unknown')

def getresourcefile(filename):
    """Returns name of file by adding it to resource directory pathname

    No attempt is made to verify the file exists
    @rtype: string
    """
    return os.path.join(resourcedirectory, filename)

# Where to find bitmaps etc
resourcedirectory=os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), 'resources'))

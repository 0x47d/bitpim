### BITPIM
###
### Copyright (C) 2003-2004 Roger Binns <rogerb@rogerbinns.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""The main gui code for BitPim"""

# System modules
import thread, threading
import Queue
import time
import os
import cStringIO
import zipfile
import re
import sys

# wx modules
import wx
import wx.lib.colourdb
import wx.gizmos

# temporarily needed due to bugs
import wxPython.gizmosc as gizmosc

# my modules
import guiwidgets
import common
import version
import helpids
import comdiagnose
import phonebook
import importexport
import wallpaper
import ringers
import guihelper
import bpcalendar
import bphtml
import bitflingscan

###
### Used to check our threading
###
mainthreadid=thread.get_ident()
helperthreadid=-1 # set later



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

class HelperReturnEvent(wx.PyEvent):
    def __init__(self, callback, *args, **kwargs):
        if __debug__:
            # verify not being called in main thread.  We could be called in
            # the comms worker thread, or in the XML-RPC worker threads
            global helperthreadid
            assert helperthreadid==thread.get_ident()
        global EVT_CALLBACK
        wx.PyEvent.__init__(self)
        self.SetEventType(EVT_CALLBACK)
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
        while True:
            if not first:
                wx.PostEvent(self.dispatchto, HelperReturnEvent(self.dispatchto.endbusycb))
            else:
                first=0
            item=self.q.get()
            wx.PostEvent(self.dispatchto, HelperReturnEvent(self.dispatchto.startbusycb))
            call=item[0]
            resultcb=item[1]
            ex=None
            res=None
            try:
                res=call()
            except Exception,e:
                ex=e
                if not hasattr(e,"gui_exc_info"):
                    ex.gui_exc_info=sys.exc_info()
            wx.PostEvent(self.dispatchto, HelperReturnEvent(resultcb, ex, res))
            if isinstance(ex, SystemExit):
                raise ex

    def progressminor(self, pos, max, desc=""):
        wx.PostEvent(self.dispatchto, HelperReturnEvent(self.dispatchto.progressminorcb, pos, max, desc))

    def progressmajor(self, pos, max, desc=""):
        wx.PostEvent(self.dispatchto, HelperReturnEvent(self.dispatchto.progressmajorcb, pos, max, desc))

    def progress(self, pos, max, desc=""):
        self.progressminor(pos, max, desc)

    def log(self, str):
        if self.dispatchto.wantlog:
            wx.PostEvent(self.dispatchto, HelperReturnEvent(self.dispatchto.logcb, str))

    def logdata(self, str, data, klass=None):
        if self.dispatchto.wantlog:
            wx.PostEvent(self.dispatchto, HelperReturnEvent(self.dispatchto.logdatacb, str, data, klass))


###
###  Splash screen
###

thesplashscreen=None  # set to non-none if there is one

class MySplashScreen(wx.SplashScreen):
    def __init__(self, app, config):
        self.app=app
        # how long are we going to be up for?
        time=config.ReadInt("splashscreentime", 2500)
        if time>0:
            bmp=guihelper.getbitmap("splashscreen")
            self.drawnameandnumber(bmp)
            wx.SplashScreen.__init__(self, bmp, wx.SPLASH_CENTRE_ON_SCREEN|wx.SPLASH_TIMEOUT,
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
        dc=wx.MemoryDC()
        dc.SelectObject(bmp)
        # where we start writing
        x=23 
        y=40
        # Product name
        if False:
            str=version.name
            dc.SetTextForeground( wx.NamedColour("MEDIUMORCHID4") ) 
            dc.SetFont( self._gimmethedamnsizeirequested(25, wx.ROMAN, wx.NORMAL, wx.NORMAL) )
            w,h=dc.GetTextExtent(str)
            dc.DrawText(str, x, y)
            y+=h+0
        # Version number
        x=58
        y=127
        str=version.versionstring
        dc.SetTextForeground( wx.NamedColour("MEDIUMBLUE") )
        dc.SetFont( self._gimmethedamnsizeirequested(15, wx.ROMAN, wx.NORMAL, wx.NORMAL) )
        w,h=dc.GetTextExtent(str)
        dc.DrawText(str, x+10, y)
        y+=h+0
        # all done
        dc.SelectObject(wx.NullBitmap)

    def _gimmethedamnsizeirequested(self, ps, family, style, weight):
        # on Linux we have to ask for bigger than we want
        if guihelper.IsGtk():
            ps=ps*1.6
        font=wx.TheFontList.FindOrCreateFont(ps, family, style, weight)
        return font

    def goforit(self):
        self.app.makemainwindow()
        
    def OnClose(self, evt):
        self.goforit()
        evt.Skip()

####
#### Main application class.  Runs the event loop etc
####            
EVT_CALLBACK=None
class MainApp(wx.App):
    def __init__(self, *_):
        wx.App.__init__(self, redirect=False, useBestVisual=True)
        sys.setcheckinterval(100)
        
    def OnInit(self):
        self.made=False
        # Routine maintenance
        wx.InitAllImageHandlers()
        wx.lib.colourdb.updateColourDB()
        
        # Thread stuff
        global mainthreadid
        mainthreadid=thread.get_ident()

        # Establish config stuff
        cfgstr='bitpim'
        if guihelper.IsMSWindows():
            cfgstr="BitPim"  # nicely capitalized on Windows
        self.config=wx.Config(cfgstr, style=wx.CONFIG_USE_LOCAL_FILE)

        # for help to save prefs
        self.SetAppName(cfgstr)
        self.SetVendorName(cfgstr)

        # setup help system
        self.setuphelp()

        # html easy printing
        self.htmlprinter=bphtml.HtmlEasyPrinting(None, self.config, "printing")

        global EVT_CALLBACK
        EVT_CALLBACK=wx.NewEventType()

        # get the splash screen up
        MySplashScreen(self, self.config)

        return True

##    def setuphelpiwant(self):
##        """This is how the setuphelp code is supposed to be, but stuff is missing from wx"""
##        self.helpcontroller=wx.BestHelpController()
##        self.helpcontroller.Initialize(gethelpfilename)

    def setuphelp(self):
        """Does all the nonsense to get help working"""
        import wx.html
        # htmlhelp isn't correctly wrapper in wx package
        from wxPython.htmlhelp import wxHtmlHelpController
        # Add the Zip filesystem
        wx.FileSystem_AddHandler(wx.ZipFSHandler())
        # Get the help working
        self.helpcontroller=wxHtmlHelpController()
        self.helpcontroller.AddBook(guihelper.gethelpfilename()+".htb")
        self.helpcontroller.UseConfig(self.config, "help")

        # now context help
        # (currently borken)
        # self.helpprovider=wx.HelpControllerHelpProvider(self.helpcontroller)
        # wx.HelpProvider_Set(provider)



    def displayhelpid(self, id):
        self.helpcontroller.Display(id)

    def makemainwindow(self):
        if self.made:
            return # already been called
        self.made=True
        # make the main frame
        frame=MainWindow(None, -1, "BitPim", self.config)
        frame.Connect(-1, -1, EVT_CALLBACK, frame.OnCallback)

        # make the worker thread
        wt=WorkerThread()
        wt.setdispatch(frame)
        wt.setDaemon(1)
        wt.start()
        frame.wt=wt
        self.frame=frame
        self.SetTopWindow(frame)
        self.SetExitOnFrameDelete(True)

    def OnExit(self): 
        self.config.Flush()
        # we get stupid messages about daemon threads, and Python's library
        # doesn't provide any way to interrupt them, nor to suppress these
        # messages.  ::TODO:: maybe remove the onexit handler installed by
        # treading._MainThread
        sys.excepthook=donothingexceptionhandler

# do nothing exception handler
def donothingexceptionhandler(*args):
    pass

# Entry point
def run(*args):
    m=MainApp(*args)
    res=m.MainLoop()
    return res

###
### Main Window (frame) class
###

class MainWindow(wx.Frame):
    def __init__(self, parent, id, title, config):
        wx.Frame.__init__(self, parent, id, title,
                         style=wx.DEFAULT_FRAME_STYLE|wx.NO_FULL_REPAINT_ON_RESIZE)

        # does bitfling work?  -- commented out for moment
        # import bitfling.client

        wx.GetApp().htmlprinter.SetParentFrame(self)

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

        menuBar = wx.MenuBar()
        self.SetMenuBar(menuBar)
        menu = wx.Menu()
        # menu.Append(guihelper.ID_FILENEW,  "&New", "Start from new")
        # menu.Append(guihelper.ID_FILEOPEN, "&Open", "Open a file")
        # menu.Append(guihelper.ID_FILESAVE, "&Save", "Save your work")
        menu.Append(guihelper.ID_FILEPRINT, "&Print...", "Print phonebook")
        # menu.AppendSeparator()
        menu.Append(guihelper.ID_FILEIMPORT, "Import CSV...", "Import a CSV file for the phonebook")
        menu.AppendSeparator()
        menu.Append(guihelper.ID_FILEEXIT, "E&xit", "Close down this program")
        menuBar.Append(menu, "&File");
        menu=wx.Menu()
        menu.Append(guihelper.ID_EDITADDENTRY, "Add...", "Add an item")
        menu.Append(guihelper.ID_EDITDELETEENTRY, "Delete", "Delete currently selected entry")
        if guihelper.HasFullyFunctionalListView():
            menu.AppendSeparator()
            menu.Append(guihelper.ID_FV_ICONS, "View as Images", "Show items as images")
            menu.Append(guihelper.ID_FV_LIST, "View As List", "Show items as a report")
        menu.AppendSeparator()
        menu.Append(guihelper.ID_EDITSETTINGS, "&Settings", "Edit settings")
        menuBar.Append(menu, "&Edit");

        menu=wx.Menu()
        menu.Append(guihelper.ID_DATAGETPHONE, "Get Phone &Data ...", "Loads data from the phone")
        menu.Append(guihelper.ID_DATASENDPHONE, "&Send Phone Data ...", "Sends data to the phone")
        menuBar.Append(menu, "&Data")

        menu=wx.Menu()
        menu.Append(guihelper.ID_VIEWCOLUMNS, "Columns ...", "Which columns to show")
        menu.AppendSeparator()
        menu.AppendCheckItem(guihelper.ID_VIEWLOGDATA, "View protocol logging", "View protocol logging information")
        menu.Append(guihelper.ID_VIEWCLEARLOGS, "Clear logs", "Clears the contents of the log panes")
        menu.AppendSeparator()
        menu.AppendCheckItem(guihelper.ID_VIEWFILESYSTEM, "View filesystem", "View filesystem on the phone")
        menuBar.Append(menu, "&View")
        

        menu=wx.Menu()
        menu.Append(guihelper.ID_HELPHELP, "&Help", "Help for the panel you are looking at")
        menu.Append(guihelper.ID_HELPTOUR, "&Tour", "Tour of BitPim")
        menu.Append(guihelper.ID_HELPCONTENTS, "&Contents", "Table of contents for the online help")
        menu.AppendSeparator()
        menu.Append(guihelper.ID_HELPABOUT, "&About", "Display program information")
        menuBar.Append(menu, "&Help");

        

        ### toolbar
        # self.tb=self.CreateToolBar(wx.TB_HORIZONTAL|wx.NO_BORDER|wx.TB_FLAT)
        self.tb=self.CreateToolBar(wx.TB_HORIZONTAL|wx.TB_TEXT)
        #self.tb.SetToolBitmapSize(wx.Size(32,32))
        sz=self.tb.GetToolBitmapSize()
        # work around a bug on Linux that returns random (large) numbers
        if sz[0]<10 or sz[0]>100: sz=wx.Size(32,32)

        if guihelper.HasFullyFunctionalListView():
            # The art names are the opposite way round than people would normally describe ...
            self.tb.AddLabelTool(guihelper.ID_FV_LIST, "List", wx.ArtProvider_GetBitmap(wx.ART_REPORT_VIEW, wx.ART_TOOLBAR, sz),
                                  shortHelp="List View", longHelp="View items as a list")
            self.tb.AddLabelTool(guihelper.ID_FV_ICONS, "Images", wx.ArtProvider_GetBitmap(wx.ART_LIST_VIEW, wx.ART_TOOLBAR, sz),
                                  shortHelp="Icon View", longHelp="View items as icons")
            self.tb.AddSeparator()

        # add and delete tools
        self.tb.AddLabelTool(guihelper.ID_EDITADDENTRY, "Add", wx.ArtProvider_GetBitmap(wx.ART_ADD_BOOKMARK, wx.ART_TOOLBAR, sz),
                              shortHelp="Add", longHelp="Add an item")
        self.tb.AddLabelTool(guihelper.ID_EDITDELETEENTRY, "Delete", wx.ArtProvider_GetBitmap(wx.ART_DEL_BOOKMARK, wx.ART_TOOLBAR, sz),
                              shortHelp="Delete", longHelp="Delete item")
            
        # You have to make this call for the toolbar to draw itself properly
        self.tb.Realize()


        ### persistent dialogs
        self.dlggetphone=guiwidgets.GetPhoneDialog(self, "Get Data from Phone")
        self.dlgsendphone=guiwidgets.SendPhoneDialog(self, "Send Data to Phone")

        ### Events we handle
        wx.EVT_MENU(self, guihelper.ID_FILEIMPORT, self.OnFileImport)
        wx.EVT_MENU(self, guihelper.ID_FILEPRINT, self.OnFilePrint)
        wx.EVT_MENU(self, guihelper.ID_FILEEXIT, self.OnExit)
        wx.EVT_MENU(self, guihelper.ID_EDITSETTINGS, self.OnEditSettings)
        wx.EVT_MENU(self, guihelper.ID_DATAGETPHONE, self.OnDataGetPhone)
        wx.EVT_MENU(self, guihelper.ID_DATASENDPHONE, self.OnDataSendPhone)
        wx.EVT_MENU(self, guihelper.ID_VIEWCOLUMNS, self.OnViewColumns)
        wx.EVT_MENU(self, guihelper.ID_VIEWCLEARLOGS, self.OnViewClearLogs)
        wx.EVT_MENU(self, guihelper.ID_VIEWLOGDATA, self.OnViewLogData)
        wx.EVT_MENU(self, guihelper.ID_VIEWFILESYSTEM, self.OnViewFilesystem)
        wx.EVT_MENU(self, guihelper.ID_FV_LIST, self.OnFileViewList)
        wx.EVT_MENU(self, guihelper.ID_FV_ICONS, self.OnFileViewIcons)
        wx.EVT_MENU(self, guihelper.ID_EDITADDENTRY, self.OnEditAddEntry)
        wx.EVT_MENU(self, guihelper.ID_EDITDELETEENTRY, self.OnEditDeleteEntry)
        wx.EVT_MENU(self, guihelper.ID_HELPABOUT, self.OnHelpAbout)
        wx.EVT_MENU(self, guihelper.ID_HELPHELP, self.OnHelpHelp)
        wx.EVT_MENU(self, guihelper.ID_HELPCONTENTS, self.OnHelpContents)
        wx.EVT_MENU(self, guihelper.ID_HELPTOUR, self.OnHelpTour)
        wx.EVT_CLOSE(self, self.OnClose)

        ### Double check our size is meaningful, and make bigger
        ### if necessary (especially needed on Mac and Linux)
        if min(self.GetSize())<250:
            self.SetSize( (640, 480) )


        ### Is config set?
        self.configdlg=guiwidgets.ConfigDialog(self, self)
        if self.configdlg.needconfig():
            self.CloseSplashScreen()
            if self.configdlg.ShowModal()!=wx.ID_OK:
                self.OnExit()
                return
        self.configdlg.updatevariables()
        
        ### notebook
        self.nb=wx.Notebook(self,-1, style=wx.NO_FULL_REPAINT_ON_RESIZE)
        # wx.EVT_ERASE_BACKGROUND(self.nb, lambda _=None: 0)

        ### notebook tabs
        self.phonewidget=phonebook.PhoneWidget(self, self.nb, self.config)
        self.nb.AddPage(self.phonewidget, "PhoneBook")
        self.wallpaperwidget=wallpaper.WallpaperView(self, self.nb)
        self.nb.AddPage(self.wallpaperwidget, "Wallpaper")
        self.ringerwidget=ringers.RingerView(self, self.nb)
        self.nb.AddPage(self.ringerwidget, "Ringers")
        self.calendarwidget=bpcalendar.Calendar(self, self.nb)
        self.nb.AddPage(self.calendarwidget, "Calendar")


        ### logwindow (last notebook tab)
        self.lw=guiwidgets.LogWindow(self.nb)
        self.nb.AddPage(self.lw, "Log")

        # Final widgets that depend on config
        lv=self.config.ReadInt("viewlogdata", 0)
        if lv:
            menuBar.Check(guihelper.ID_VIEWLOGDATA, 1)
            self.OnViewLogData(None)

        fv=self.config.ReadInt("viewfilesystem", 0)
        if fv:
            menuBar.Check(guihelper.ID_VIEWFILESYSTEM, 1)
            self.OnViewFilesystem(None)
            wx.Yield()

        # now register for notebook changes
        wx.EVT_NOTEBOOK_PAGE_CHANGED(self, -1, self.OnNotebookPageChanged)


        # show the last page we were on
        pg=self.config.Read("viewnotebookpage", "")
        sel=0
        if len(pg):
            for i in range(self.nb.GetPageCount()):
                if pg==self.nb.GetPageText(i):
                    sel=i
                    break

        if sel==self.nb.GetSelection():
            # no callback is generated if we change to the page we are already
            # on, but we need to update toolbar etc so fake it
            self.OnNotebookPageChanged()
        else:
            self.nb.SetSelection(sel)

        # Retrieve saved settings... Use 80% of screen if not specified
        guiwidgets.set_size(self.config, "MainWin", self, screenpct=90)

        ### Lets go visible
        self.Show()

        # Show tour on first use
        if self.config.ReadInt("firstrun", True):
            self.config.WriteInt("firstrun", False)
            self.config.Flush()
            wx.CallAfter(self.OnHelpTour)

        # Populate all widgets from disk
        wx.CallAfter(self.OnPopulateEverythingFromDisk)

    def CloseSplashScreen(self):
        ### remove splash screen if there is one
        global thesplashscreen
        if thesplashscreen is not None:
            try:
        # on Linux this is often already deleted and generates an exception
                thesplashscreen.Show(False)
            except:
                pass
            thesplashscreen=None
            wx.SafeYield(onlyIfNeeded=True)

    def OnExit(self,_=None):
        self.Close()

    # It has been requested that we shutdown
    def OnClose(self, event):
        self.saveSize()
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
        wx.GetApp().ExitMainLoop()

    # about and help

    def OnHelpAbout(self,_):
        import version

        str="BitPim Version "+version.versionstring
        str+="\n\n"
        if len(version.extrainfo):
            str+=version.extrainfo+"\n\n"
        str+=version.contact

        d=wx.MessageDialog(self, str, "About BitPim", wx.OK|wx.ICON_INFORMATION)
        d.ShowModal()
        d.Destroy()
        
    def OnHelpHelp(self, _):
        text=re.sub("[^A-Za-z]", "", self.nb.GetPageText(self.nb.GetSelection()))
        wx.GetApp().displayhelpid(getattr(helpids, "ID_TAB_"+text.upper()))

    def OnHelpContents(self, _):
        wx.GetApp().helpcontroller.DisplayContents()

    def OnHelpTour(self, _=None):
        wx.GetApp().displayhelpid(helpids.ID_TOUR)

    def OnViewColumns(self, _):
        dlg=phonebook.ColumnSelectorDialog(self, self.config, self.phonewidget)
        dlg.ShowModal()
        dlg.Destroy()

    def OnViewLogData(self, _):
        # toggle state of the log data
        logdatatitle="Protocol Log"
        if self.lwdata is None:
            self.lwdata=guiwidgets.LogWindow(self.nb)
            self.nb.AddPage(self.lwdata, logdatatitle)
            self.config.WriteInt("viewlogdata", 1)
        else:
            self.lwdata=None
            for i in range(0,self.nb.GetPageCount()):
                if self.nb.GetPageText(i)==logdatatitle:
                    self.nb.DeletePage(i)
                    break
            self.config.WriteInt("viewlogdata", 0)

    def OnViewFilesystem(self,_):
        # toggle filesystem view
        logtitle="Log"
        fstitle="Filesystem"
        if self.filesystemwidget is None:
            for i in range(0, self.nb.GetPageCount()):
                if self.nb.GetPageText(i)==logtitle:
                    self.filesystemwidget=FileSystemView(self, self.nb, id=97)
                    self.nb.InsertPage(i, self.filesystemwidget, fstitle, True)
                    self.config.WriteInt("viewfilesystem", True)
                    return
            assert False, "log page is missing!"
            return
        self.filesystemwidget=None
        for i in range(0, self.nb.GetPageCount()):
            if self.nb.GetPageText(i)==fstitle:
                self.nb.DeletePage(i)
                self.config.WriteInt("viewfilesystem", False)
                return
        assert False, "filesytem view page is missing!"
        

    def OnFileImport(self,_):
        dlg=wx.FileDialog(self, "Import CSV file", wildcard="CSV files (*.csv)|*.csv|Tab Seperated file (*.tsv)|*.tsv|All files|*",
                         style=wx.OPEN|wx.HIDE_READONLY|wx.CHANGE_DIR)
        path=None
        if dlg.ShowModal()==wx.ID_OK:
            path=dlg.GetPath()
        dlg.Destroy()
        if path is None:
            return
        importexport.OnImportCSVPhoneBook(self, self.phonewidget, path)

    def OnFilePrint(self,_):
        self.phonewidget.OnPrintDialog(self, self.config)

    ### 
    ### Main bit for getting stuff from phone
    ###
    def OnDataGetPhone(self,_):
        dlg=self.dlggetphone
        print self.phoneprofile
        dlg.UpdateWithProfile(self.phoneprofile)
        if dlg.ShowModal()!=wx.ID_OK:
            return
        self.MakeCall(Request(self.wt.getdata, dlg),
                      Callback(self.OnDataGetPhoneResults))

    def OnDataGetPhoneResults(self, exception, results):
        if self.HandleException(exception): return
        self.OnLog(`results.keys()`)
        self.OnLog(`results['sync']`)
        # phonebook
        if results['sync'].has_key('phonebook'):
            v=results['sync']['phonebook']

            print "phonebookmergesetting is",v
            if v=='MERGE': 
                merge=True
            else:
                merge=False
            self.phonewidget.importdata(results['phonebook'], results.get('categories', []), merge)

        # wallpaper
        updwp=False # did we update the wallpaper
        if results['sync'].has_key('wallpaper'):
            v=results['sync']['wallpaper']
            if v=='MERGE': raise Exception("Not implemented")
            updwp=True
            self.wallpaperwidget.populatefs(results)
            self.wallpaperwidget.populate(results)
        # wallpaper-index
        if not updwp and results.has_key('wallpaper-index'):
            self.wallpaperwidget.updateindex(results['wallpaper-index'])
        # ringtone
        updrng=False # did we update ringtones
        if results['sync'].has_key('ringtone'):
            v=results['sync']['ringtone']
            if v=='MERGE': raise Exception("Not implemented")
            updrng=True
            self.ringerwidget.populatefs(results)
            self.ringerwidget.populate(results)
        # wallpaper-index
        if not updrng and results.has_key('ringtone-index'):
            self.ringerwidget.updateindex(results['ringtone-index'])            
        # calendar
        if results['sync'].has_key('calendar'):
            v=results['sync']['calendar']
            if v=='MERGE': raise Exception("Not implemented")
            self.calendarwidget.populatefs(results)
            self.calendarwidget.populate(results)

            
    ###
    ### Main bit for sending data to the phone
    ###
    def OnDataSendPhone(self, _):
        dlg=self.dlgsendphone
        print self.phoneprofile
        dlg.UpdateWithProfile(self.phoneprofile)
        if dlg.ShowModal()!=wx.ID_OK:
            return
        data={}
        convertors=[]
        todo=[]
        funcscb=[]
        ### Calendar
        v=dlg.GetCalendarSetting()
        if v!=dlg.NOTREQUESTED:
            merge=True
            if v==dlg.OVERWRITE: merge=False
            self.calendarwidget.getdata(data)
            todo.append( (self.wt.writecalendar, "Calendar", merge) )
        ### Wallpaper
        v=dlg.GetWallpaperSetting()
        if v!=dlg.NOTREQUESTED:
            merge=True
            if v==dlg.OVERWRITE: merge=False
            if merge:
                want=self.wallpaperwidget.SELECTED
            else:
                want=self.wallpaperwidget.ALL
            self.wallpaperwidget.getdata(data, want)
            todo.append( (self.wt.writewallpaper, "Wallpaper", merge) )
            # funcscb.append( self.wallpaperwidget.populate )
        ### Ringtone
        v=dlg.GetRingtoneSetting()
        if v!=dlg.NOTREQUESTED:
            merge=True
            if v==dlg.OVERWRITE: merge=False
            if merge:
                want=self.ringerwidget.SELECTED
            else:
                want=self.ringerwidget.ALL
            self.ringerwidget.getdata(data, want)
            todo.append( (self.wt.writeringtone, "Ringtone", merge) )
            # funcscb.append( self.ringerwidget.populate )

        ### Phonebook
        v=dlg.GetPhoneBookSetting()
        if v!=dlg.NOTREQUESTED:
            if v==dlg.OVERWRITE: 
                self.phonewidget.getdata(data)
                todo.append( (self.wt.writephonebook, "Phonebook") )
            convertors.append(self.phonewidget.converttophone)
            # writing will modify serials so we need to update
            funcscb.append(self.phonewidget.updateserials)

        todo.append((self.wt.rebootcheck, "Phone Reboot"))
        self.MakeCall(Request(self.wt.getfundamentals),
                      Callback(self.OnDataSendPhoneGotFundamentals, data, todo, convertors, funcscb))

    def OnDataSendPhoneGotFundamentals(self,data,todo,convertors, funcscb, exception, results):
        if self.HandleException(exception): return
        data.update(results)
        # call each widget to update fundamentals
        # for widget in self.calendarwidget, self.wallpaperwidget, self.ringerwidget, self.phonewidget:
        #    widget.updatefundamentals(data)
        
        # call convertors
        for f in convertors:
            f(data)

        # Now scribble to phone
        self.MakeCall(Request(self.wt.senddata, data, todo),
                      Callback(self.OnDataSendPhoneResults, funcscb))

    def OnDataSendPhoneResults(self, funcscb, exception, results):
        if self.HandleException(exception): return
        print results.keys()
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
        wx.SafeYield(onlyIfNeeded=True)
        self.phonewidget.populate(results)
        wx.SafeYield(onlyIfNeeded=True)
        self.wallpaperwidget.populate(results)
        wx.SafeYield(onlyIfNeeded=True)
        self.ringerwidget.populate(results)
        wx.SafeYield(onlyIfNeeded=True)
        self.calendarwidget.populate(results)
        # close the splash screen if it is still up
        self.CloseSplashScreen()
        
    # deal with configuring the phone (commport)
    def OnEditSettings(self, _=None):
        if wx.IsBusy():
            wx.MessageBox("BitPim is busy.  You can't change settings until it has finished talking to your phone.",
                         "BitPim is busy.", wx.OK|wx.ICON_EXCLAMATION)
        else:
            self.configdlg.ShowModal()

    # deal with graying out/in menu items on notebook page changing
    def OnNotebookPageChanged(self, _=None):
        # remember what we are looking at
        text=self.nb.GetPageText(self.nb.GetSelection())
        if text is not None:
            self.config.Write("viewnotebookpage", text)
        # is ringers viewable?
        widget=self.nb.GetPage(self.nb.GetSelection())
        if widget is self.ringerwidget:
            enablefv=True
        else: enablefv=False
        if widget is self.ringerwidget or \
           widget is self.wallpaperwidget or \
           widget is self.phonewidget:
            enableedit=True
        else: enableedit=False

        # Toolbar
        if guihelper.HasFullyFunctionalListView():
            self.GetToolBar().EnableTool(guihelper.ID_FV_ICONS, enablefv)
            self.GetToolBar().EnableTool(guihelper.ID_FV_LIST, enablefv)
        self.GetToolBar().EnableTool(guihelper.ID_EDITADDENTRY, enableedit)
        self.GetToolBar().EnableTool(guihelper.ID_EDITDELETEENTRY, enableedit)
        # menu items
        if guihelper.HasFullyFunctionalListView():
            self.GetMenuBar().Enable(guihelper.ID_FV_ICONS, enablefv)
            self.GetMenuBar().Enable(guihelper.ID_FV_LIST, enablefv)
        self.GetMenuBar().Enable(guihelper.ID_EDITADDENTRY, enableedit)
        self.GetMenuBar().Enable(guihelper.ID_EDITDELETEENTRY, enableedit)

        # View Columns .. is only in Phonebook
        self.GetMenuBar().Enable(guihelper.ID_VIEWCOLUMNS, widget is self.phonewidget)
        # as is File Print
        self.GetMenuBar().Enable(guihelper.ID_FILEPRINT, widget is self.phonewidget)
         
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
        wx.BeginBusyCursor(wx.StockCursor(wx.CURSOR_ARROWWAIT))

    def OnBusyEnd(self):
        wx.EndBusyCursor()
        self.SetStatusText("Ready")
        self.OnProgressMajor(0,1)


    # progress and logging
    def OnViewClearLogs(self, _):
        self.lw.Clear()
        if self.lwdata is not None:
            self.lwdata.Clear()

    def OnProgressMinor(self, pos, max, desc=""):
        self.GetStatusBar().progressminor(pos, max, desc)

    def OnProgressMajor(self, pos, max, desc=""):
        self.GetStatusBar().progressmajor(pos, max, desc)

    def OnLog(self, str):
        self.lw.log(str)
        if self.lwdata is not None:
            self.lwdata.log(str)

    def OnLogData(self, str, data, klass=None):
        if self.lwdata is not None:
            self.lwdata.logdata(str,data, klass)

    def excepthook(self, type, value, traceback):
        if not hasattr(value, "gui_exc_info"):
            value.gui_exc_info=(type,value,traceback)
        self.HandleException(value)

    def HandleException(self, exception):
        """returns true if this function handled the exception
        and the caller should not do any further processing"""
        if exception is None: return False
        assert isinstance(exception, Exception)
        self.CloseSplashScreen()
        text=None
        title=None
        style=None
        # Here is where we turn the exception into something user friendly
        if isinstance(exception, common.CommsDeviceNeedsAttention):
            text="%s: %s" % (exception.device, exception.message)
            title="Device needs attention - "+exception.device
            style=wx.OK|wx.ICON_INFORMATION
            help=lambda _: wx.GetApp().displayhelpid(helpids.ID_DEVICE_NEEDS_ATTENTION)
        elif isinstance(exception, common.CommsOpenFailure):
            text="%s: %s" % (exception.device, exception.message)
            title="Failed to open communications - "+exception.device
            style=wx.OK|wx.ICON_INFORMATION
            help=lambda _: wx.GetApp().displayhelpid(helpids.ID_FAILED_TO_OPEN_DEVICE)
        elif isinstance(exception, common.AutoPortsFailure):
            text=exception.message
            title="Failed to automatically detect port"
            style=wx.OK|wx.ICON_INFORMATION
            help=lambda _: wx.GetApp().displayhelpid(helpids.ID_FAILED_TO_AUTODETECT_PORT)
            
        if text is not None:
            self.OnLog("Error: "+title+"\n"+text)
            dlg=guiwidgets.AlertDialogWithHelp(self,text, title, help, style=style)
            dlg.ShowModal()
            dlg.Destroy()
            return True
        e=guiwidgets.ExceptionDialog(self, exception)
        try:
            self.OnLog("Exception: "+e.getexceptiontext())
        except AttributeError:
            # this can happen if main gui hasn't been built yet
            pass
        e.ShowModal()
        e.Destroy()
        return True
        
    # plumbing for the multi-threading

    def OnCallback(self, event):
        assert isinstance(event, HelperReturnEvent)
        event()

    def MakeCall(self, request, cbresult):
        assert isinstance(request, Request)
        assert isinstance(cbresult, Callback)
        self.wt.q.put( (request, cbresult) )

    def saveSize(self):
        guiwidgets.save_size(self.config, "MainWin", self.GetRect())


###
### Container for midi files
###  

#class MidiFileList(wx.ListCtrl):
#    pass




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


    def clearcomm(self):
        if self.commphone is None:
            return
        self.commphone.close()
        self.commphone=None
        
        
    def setupcomm(self):
        if __debug__: self.checkthread()
        if self.commphone is None:
            import commport
            if self.dispatchto.commportsetting is None or \
               len(self.dispatchto.commportsetting)==0:
                raise common.CommsNeedConfiguring("Comm port not configured", "DEVICE")

            if self.dispatchto.commportsetting=="auto":
                autofunc=comdiagnose.autoguessports
            else:
                autofunc=None
            comcfg=self.dispatchto.commparams

            name=self.dispatchto.commportsetting
            if name.startswith("bitfling::"):
                klass=bitflingscan.CommConnection
            else:
                klass=commport.CommConnection
                
            comport=klass(self, self.dispatchto.commportsetting, autolistfunc=autofunc,
                          autolistargs=(self.dispatchto.phonemodule,),
                          baud=comcfg['baud'], timeout=comcfg['timeout'],
                          hardwareflow=comcfg['hardwareflow'],
                          softwareflow=comcfg['softwareflow'],
                          configparameters=comcfg)
                
            try:
                self.commphone=self.dispatchto.phonemodule.Phone(self, comport)
            except:
                comport.close()
                raise

    def getfundamentals(self):
        if __debug__: self.checkthread()
        self.setupcomm()
        results={}
        self.commphone.getfundamentals(results)
        return results

    def getdata(self, req):
        if __debug__: self.checkthread()
        self.setupcomm()
        results=self.getfundamentals()
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

    def rebootcheck(self, results):
        if __debug__: self.checkthread()
        if results.has_key('rebootphone'):
            self.phonerebootrequest()
            self.clearcomm()
            
    def writecalendar(self, data, merge):
        if __debug__: self.checkthread()
        self.setupcomm()
        return self.commphone.savecalendar(data, merge)
        

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

    def rmdirs(self,path):
        if __debug__: self.checkthread()
        self.setupcomm()
        self.progressminor(0,1, "Listing child files and directories")
        all=self.dirlisting(path, 100)
        keys=all.keys()
        keys.sort()
        keys.reverse()
        count=0
        for k in keys:
            self.progressminor(count, len(keys), "Deleting "+k)
            count+=1
            if all[k]['type']=='directory':
                self.rmdir(k)
            else:
                self.rmfile(k)
        self.rmdir(path)

    # offline/reboot
    def phonerebootrequest(self):
        if __debug__: self.checkthread()
        self.setupcomm()
        return self.commphone.offlinerequest(reset=True)

    def phoneofflinerequest(self):
        if __debug__: self.checkthread()
        self.setupcomm()
        return self.commphone.offlinerequest()

    # backups etc
    def getbackup(self,path,recurse=0):
        if __debug__: self.checkthread()
        self.setupcomm()
        self.progressmajor(0,0,"Listing files")
        files=self.dirlisting(path, recurse)
        if path=="/" or path=="":
            strip=0 # root dir
        else:
            strip=len(path)+1 # child

        keys=files.keys()
        keys.sort()
        
        op=cStringIO.StringIO()
        zip=zipfile.ZipFile(op, "w", zipfile.ZIP_DEFLATED)

        count=0
        for k in keys:
            count+=1
            if files[k]['type']!='file':
                continue
            self.progressmajor(count, len(keys)+1, "Getting files")
            # get the contents
            contents=self.getfile(k)
            # an artificial sleep. if you get files too quickly, the 4400 eventually
            # runs out of buffers and returns truncated packets
            time.sleep(0.3)
            # add to zip file
            zi=zipfile.ZipInfo()
            zi.filename=k[strip:]
            if files[k]['date'][0]==0:
                zi.date_time=(0,0,0,0,0,0)
            else:
                zi.date_time=time.gmtime(files[k]['date'][0])[:6]
            zi.compress_type=zipfile.ZIP_DEFLATED
            zip.writestr(zi, contents)
        zip.close()

        return op.getvalue()
    
    def restorefiles(self, files):
        if __debug__: self.checkthread()
        self.setupcomm()

        results=[]

        seendirs=[]

        count=0
        for name, contents in files:
            self.progressmajor(count, len(files), "Restoring files")
            count+=1
            d=guihelper.dirname(name)
            if d not in seendirs:
                seendirs.append(d)
                self.commphone.mkdirs(d)
            self.writefile(name, contents)
            results.append( (True, name) )

        return results


class FileSystemView(wx.gizmos.TreeListCtrl):

    # the gizmos.py shipped with wx 2.4.1.2 has wrong implementation
    # of these three methods.  We have fixed versions here.  They will be removed
    # when a later version of wx ships
    def GetFirstChild(self, *_args, **_kwargs):
        val = gizmosc.wxTreeListCtrl_GetFirstChild(self, *_args, **_kwargs)
        return val
    def GetNextChild(self, *_args, **_kwargs):
        val = gizmosc.wxTreeListCtrl_GetNextChild(self, *_args, **_kwargs)
        return val
    def HitTest(self, point):
        w = self.GetMainWindow()
        return gizmosc.wxTreeListCtrl_HitTest(self, self.ScreenToClient(w.ClientToScreen(point)))

    # we have to add None objects to all nodes otherwise the tree control refuses
    # sort (somewhat lame imho)
    def __init__(self, mainwindow, parent, id=-1):
        self.datacolumn=False # used for debugging and inspection of values
        wx.gizmos.TreeListCtrl.__init__(self, parent, id, style=wx.WANTS_CHARS|wx.TR_DEFAULT_STYLE)
        self.AddColumn("Name")
        self.AddColumn("Size")
        self.AddColumn("Date")
        self.SetMainColumn(0)
        self.SetColumnWidth(0, 300)
        self.SetColumnWidth(2, 200)
        if self.datacolumn:
            self.AddColumn("Extra Stuff")
            self.SetColumnWidth(3, 400)
        self.SetColumnAlignment(1, wx.LIST_FORMAT_RIGHT)
        self.mainwindow=mainwindow
        self.root=self.AddRoot("/")
        self.SetPyData(self.root, None)
        self.SetItemHasChildren(self.root, True)
        self.SetPyData(self.AppendItem(self.root, "Retrieving..."), None)
        self.dirhash={ "": 1}
        wx.EVT_TREE_ITEM_EXPANDED(self, id, self.OnItemExpanded)
        wx.EVT_TREE_ITEM_ACTIVATED(self,id, self.OnItemActivated)

        self.filemenu=wx.Menu()
        self.filemenu.Append(guihelper.ID_FV_SAVE, "Save ...")
        self.filemenu.Append(guihelper.ID_FV_HEXVIEW, "Hexdump")
        self.filemenu.AppendSeparator()
        self.filemenu.Append(guihelper.ID_FV_DELETE, "Delete")
        self.filemenu.Append(guihelper.ID_FV_OVERWRITE, "Overwrite ...")

        self.dirmenu=wx.Menu()
        self.dirmenu.Append(guihelper.ID_FV_NEWSUBDIR, "Make subdirectory ...")
        self.dirmenu.Append(guihelper.ID_FV_NEWFILE, "New File ...")
        self.dirmenu.AppendSeparator()
        self.dirmenu.Append(guihelper.ID_FV_BACKUP, "Backup directory ...")
        self.dirmenu.Append(guihelper.ID_FV_BACKUP_TREE, "Backup entire tree ...")
        self.dirmenu.Append(guihelper.ID_FV_RESTORE, "Restore ...")
        self.dirmenu.AppendSeparator()
        self.dirmenu.Append(guihelper.ID_FV_REFRESH, "Refresh")
        self.dirmenu.AppendSeparator()
        self.dirmenu.Append(guihelper.ID_FV_DELETE, "Delete")
        self.dirmenu.AppendSeparator()
        self.dirmenu.Append(guihelper.ID_FV_OFFLINEPHONE, "Offline Phone")
        self.dirmenu.Append(guihelper.ID_FV_REBOOTPHONE, "Reboot Phone")

        wx.EVT_MENU(self.filemenu, guihelper.ID_FV_SAVE, self.OnFileSave)
        wx.EVT_MENU(self.filemenu, guihelper.ID_FV_HEXVIEW, self.OnHexView)
        wx.EVT_MENU(self.filemenu, guihelper.ID_FV_DELETE, self.OnFileDelete)
        wx.EVT_MENU(self.filemenu, guihelper.ID_FV_OVERWRITE, self.OnFileOverwrite)
        wx.EVT_MENU(self.dirmenu, guihelper.ID_FV_NEWSUBDIR, self.OnNewSubdir)
        wx.EVT_MENU(self.dirmenu, guihelper.ID_FV_NEWFILE, self.OnNewFile)
        wx.EVT_MENU(self.dirmenu, guihelper.ID_FV_DELETE, self.OnDirDelete)
        wx.EVT_MENU(self.dirmenu, guihelper.ID_FV_BACKUP, self.OnBackupDirectory)
        wx.EVT_MENU(self.dirmenu, guihelper.ID_FV_BACKUP_TREE, self.OnBackupTree)
        wx.EVT_MENU(self.dirmenu, guihelper.ID_FV_RESTORE, self.OnRestore)
        wx.EVT_MENU(self.dirmenu, guihelper.ID_FV_REFRESH, self.OnDirRefresh)
        wx.EVT_MENU(self.dirmenu, guihelper.ID_FV_OFFLINEPHONE, self.OnPhoneOffline)
        wx.EVT_MENU(self.dirmenu, guihelper.ID_FV_REBOOTPHONE, self.OnPhoneReboot)
        wx.EVT_RIGHT_DOWN(self.GetMainWindow(), self.OnRightDown)
        wx.EVT_RIGHT_UP(self.GetMainWindow(), self.OnRightUp)

    def OnRightUp(self, event):
        pt = event.GetPosition();
        item, flags,unknown = self.HitTest(pt)
        if flags:
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
        item, flags, unknown = self.HitTest(pt)
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
            f=guihelper.basename(file)
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
                self.SetItemText(found, `result[file]['size']  `, 1)
                self.SetItemText(found, "  "+result[file]['date'][1], 2)
                if self.datacolumn:
                    self.SetItemText(found, result[file]['data'], 3)
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
        bn=guihelper.basename(path)
        ext=guihelper.getextension(bn)
        if len(ext):
            ext="%s files (*.%s)|*.%s" % (ext.upper(), ext, ext)
        else:
            ext="All files|*"
        dlg=wx.FileDialog(self, "Save File As", defaultFile=bn, wildcard=ext,
                             style=wx.SAVE|wx.OVERWRITE_PROMPT|wx.CHANGE_DIR)
        if dlg.ShowModal()==wx.ID_OK:
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
        # ::TODO:: make this use HexEditor
        dlg=guiwidgets.MyFixedScrolledMessageDialog(self, common.datatohexstring(result),
                                                    path+" Contents", helpids.ID_HEXVIEW_DIALOG)
        dlg.Show()

    def OnFileDelete(self, _):
        path=self.itemtopath(self.GetSelection())
        mw=self.mainwindow
        mw.MakeCall( Request(mw.wt.rmfile, path),
                     Callback(self.OnFileDeleteResults, guihelper.dirname(path)) )
        
    def OnFileDeleteResults(self, parentdir, exception, _):
        mw=self.mainwindow
        if mw.HandleException(exception): return
        self.OnDirListing(parentdir)

    def OnFileOverwrite(self,_):
        path=self.itemtopath(self.GetSelection())
        dlg=wx.FileDialog(self, style=wx.OPEN|wx.HIDE_READONLY|wx.CHANGE_DIR)
        if dlg.ShowModal()!=wx.ID_OK:
            dlg.Destroy()
            return
        infile=dlg.GetPath()
        f=open(infile, "rb")
        contents=f.read()
        f.close()
        mw=self.mainwindow
        mw.MakeCall( Request(mw.wt.writefile, path, contents),
                     Callback(self.OnFileOverwriteResults, guihelper.dirname(path)) )
        dlg.Destroy()
        
    def OnFileOverwriteResults(self, parentdir, exception, _):
        mw=self.mainwindow
        if mw.HandleException(exception): return
        self.OnDirListing(parentdir)

    def OnNewSubdir(self, _):
        dlg=wx.TextEntryDialog(self, "Subdirectory name?", "Create Subdirectory", "newfolder")
        if dlg.ShowModal()!=wx.ID_OK:
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
        dlg=wx.FileDialog(self, style=wx.OPEN|wx.HIDE_READONLY|wx.CHANGE_DIR)
        if dlg.ShowModal()!=wx.ID_OK:
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
        mw.MakeCall( Request(mw.wt.rmdirs, path),
                     Callback(self.OnDirDeleteResults, guihelper.dirname(path)) )
        
    def OnDirDeleteResults(self, parentdir, exception, _):
        mw=self.mainwindow
        if mw.HandleException(exception): return
        self.OnDirListing(parentdir)

    def OnPhoneReboot(self,_):
        mw=self.mainwindow
        mw.MakeCall( Request(mw.wt.phonerebootrequest),
                     Callback(self.OnPhoneRebootResults) )

    def OnPhoneRebootResults(self, exception, _):
        # special case - we always clear the comm connection
        # it is needed if the reboot succeeds, and if it didn't
        # we probably have bad comms anyway
        mw=self.mainwindow
        mw.wt.clearcomm()
        if mw.HandleException(exception): return

    def OnPhoneOffline(self,_):
        mw=self.mainwindow
        mw.MakeCall( Request(mw.wt.phoneofflinerequest),
                     Callback(self.OnPhoneOfflineResults) )

    def OnPhoneOfflineResults(self, exception, _):
        mw=self.mainwindow
        if mw.HandleException(exception): return


    def OnBackupTree(self, _):
        self.OnBackup(recurse=100)

    def OnBackupDirectory(self, _):
        self.OnBackup()

    def OnBackup(self, recurse=0):
        path=self.itemtopath(self.GetSelection())
        mw=self.mainwindow
        mw.MakeCall( Request(mw.wt.getbackup, path, recurse),
                     Callback(self.OnBackupResults, path) )

    def OnBackupResults(self, path, exception, backup):
        mw=self.mainwindow
        if mw.HandleException(exception): return
        bn=guihelper.basename(path)
        if len(bn)<1:
            bn="root"
        bn+=".zip"
        ext="Zip files|*.zip|All Files|*"
        dlg=wx.FileDialog(self, "Save File As", defaultFile=bn, wildcard=ext,
                             style=wx.SAVE|wx.OVERWRITE_PROMPT|wx.CHANGE_DIR)
        if dlg.ShowModal()==wx.ID_OK:
            f=open(dlg.GetPath(), "wb")
            f.write(backup)
            f.close()
        dlg.Destroy()

    def OnRestore(self, _):
        ext="Zip files|*.zip|All Files|*"
        path=self.itemtopath(self.GetSelection())
        bn=guihelper.basename(path)
        if len(bn)<1:
            bn="root"
        bn+=".zip"
        ext="Zip files|*.zip|All Files|*"
        dlg=wx.FileDialog(self, "Open backup file", defaultFile=bn, wildcard=ext,
                             style=wx.OPEN|wx.HIDE_READONLY|wx.CHANGE_DIR)
        if dlg.ShowModal()!=wx.ID_OK:
            return
        name=dlg.GetPath()
        if not zipfile.is_zipfile(name):
            dlg=guiwidgets.AlertDialogWithHelp(self.mainwindow, name+" is not a valid zipfile.", "Zip file required",
                                               lambda _: wx.GetApp().displayhelpid(helpids.ID_NOT_A_ZIPFILE),
                                               style=wx.OK|wx.ICON_ERROR)
            dlg.ShowModal()
            dlg.Destroy()
            return
        zipf=zipfile.ZipFile(name, "r")
        xx=zipf.testzip()
        if xx is not None:
            dlg=guiwidgets.AlertDialogWithHelp(self.mainwindow, name+" has corrupted contents.  Use a repair utility to fix it",
                                               "Zip file corrupted",
                                               lambda _: wx.GetApp().displayhelpid(helpids.ID_ZIPFILE_CORRUPTED),
                                               style=wx.OK|wx.ICON_ERROR)
            dlg.ShowModal()
            dlg.Destroy()
            return

        dlg=RestoreDialog(self.mainwindow, "Restore files", zipf, path, self.OnRestoreOK)
        dlg.Show(True)

    def OnRestoreOK(self, zipf, names, parentdir):
        if len(names)==0:
            wx.MessageBox("You didn't select any files to restore!", "No files selected",
                         wx.OK|wx.ICON_EXCLAMATION)
            return
        l=[]
        for zipname, fsname in names:
            l.append( (fsname, zipf.read(zipname)) )

        mw=self.mainwindow
        mw.MakeCall( Request(mw.wt.restorefiles, l),
                     Callback(self.OnRestoreResults, parentdir) )

    def OnRestoreResults(self, parentdir, exception, results):
        mw=self.mainwindow
        if mw.HandleException(exception): return
        ok=filter(lambda s: s[0], results)
        fail=filter(lambda s: not s[0], results)

        if len(parentdir):
            dirs=[]
            for _, name in results:
                while(len(name)>len(parentdir)):
                    name=guihelper.dirname(name)
                    if name not in dirs:
                        dirs.append(name)
            dirs.sort()
            for d in dirs:
                self.OnDirListing(d)

        self.OnDirListing(parentdir)

        if len(ok) and len(fail)==0:
            dlg=wx.MessageDialog(mw, "All files restored ok", "All files restored",
                                wx.OK|wx.ICON_INFORMATION)
            dlg.Show(True)
            return
        if len(fail) and len(ok)==0:
            wx.MessageBox("All files failed to restore", "No files restored",
                         wx.OK|wx.ICON_ERROR)
            return

        op="Failed to restore some files.  Check the log for reasons.:\n\n"
        for s,n in fail:
            op+="   "+n+"\n"

        wx.MessageBox(op, "Some restores failed", wx.OK|wx.ICON_ERROR)
            

    def OnDirRefresh(self, _):
        path=self.itemtopath(self.GetSelection())
        self.OnDirListing(path)

    def itemtopath(self, item):
        if item==self.root: return ""
        res=self.GetItemText(item)
        while True:
            parent=self.GetItemParent(item)
            if parent==self.root:
                return res
            item=parent
            res=self.GetItemText(item)+"/"+res
        # can't get here, but pychecker doesn't seem to realise
        assert False
        return ""
        
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

class RestoreDialog(wx.Dialog):
    """A dialog that lists all the files that will be restored"""
    
    def __init__(self, parent, title, zipf, path, okcb):
        """Constructor

        @param path: Placed before names in the archive.  Should not include a
                       trailing slash.
        """
        wx.Dialog.__init__(self, parent, -1, title, style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        vbs=wx.BoxSizer(wx.VERTICAL)
        vbs.Add( wx.StaticText(self, -1, "Choose files to restore"), 0, wx.ALIGN_CENTRE|wx.ALL, 5)

        nl=zipf.namelist()
        nl.sort()

        prefix=path
        if len(prefix)=="/" or prefix=="":
            prefix=""
        else:
            prefix+="/"

        nnl=map(lambda i: prefix+i, nl)

        self.clb=wx.CheckListBox(self, -1, choices=nnl, style=wx.LB_SINGLE|wx.LB_HSCROLL|wx.LB_NEEDED_SB, size=wx.Size(200,300))

        for i in range(len(nnl)):
            self.clb.Check(i, True)

        vbs.Add( self.clb, 1, wx.EXPAND|wx.ALL, 5)

        vbs.Add(wx.StaticLine(self, -1, style=wx.LI_HORIZONTAL), 0, wx.EXPAND|wx.ALL, 5)

        vbs.Add(self.CreateButtonSizer(wx.OK|wx.CANCEL|wx.HELP), 0, wx.ALIGN_CENTER|wx.ALL, 5)
    
        self.SetSizer(vbs)
        self.SetAutoLayout(True)
        vbs.Fit(self)

        wx.EVT_BUTTON(self, wx.ID_HELP, lambda _: wx.GetApp().displayhelpid(helpids.ID_RESTOREDIALOG))
        wx.EVT_BUTTON(self, wx.ID_OK, self.OnOK)
        self.okcb=okcb
        self.zipf=zipf
        self.nl=zip(nl, nnl)
        self.path=path

    def OnOK(self, _):
        names=[]
        for i in range(len(self.nl)):
            if self.clb.IsChecked(i):
                names.append(self.nl[i])
        self.okcb(self.zipf, names, self.path)
        self.Show(False)
        self.Destroy()


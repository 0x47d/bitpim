### BITPIM
###
### Copyright (C) 2003-2004 Roger Binns <rogerb@rogerbinns.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

# Standard modules
import webbrowser
import re
import htmlentitydefs
import HTMLParser
import cStringIO

# wx modules
import wx
import wx.html

# my modules
import guihelper
import fixedwxpTag

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
        wx.html.HtmlWindow.__init__(self, parent, id)
        wx.EVT_KEY_UP(self, self.OnKeyUp)
        self.thetext=""
        self.SetFontScale(relsize)

    def SetFontScale(self, scale):
        if guihelper.IsGtk():
            basefonts=[10,13,17,20,23,27,30] # Linux
        elif guihelper.IsMac():
            basefonts=[9,12,14,18,24,30,36]  # MacOSX - s/b NULL for defaults
        else:
            basefonts=[7,8,10,12,16,22,30]   # Windows/other
        self.SetFonts("", "", [int(sz*scale) for sz in basefonts])
        # the html widget clears itself if you set the scale
        if len(self.thetext):
            wx.html.HtmlWindow.SetPage(self,self.thetext)

##    def OnCellMouseHover(self, cell, x, y):
##        print cell
##        print dir(cell)
##        print cell.GetId()

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
### HTML Parsing for our pseudo styles system
###

class TreeParser(HTMLParser.HTMLParser):
    """Turns the HTML data into a tree structure

    Note that the HTML needs to be well formed (ie closing tags must be present)"""

    class TreeNode:

        def __init__(self):
            self.tag=""
            self.attrs=[]
            self.children=[]
            self.data=""
            self.styles=[]
    
    def __init__(self, data):
        HTMLParser.HTMLParser.__init__(self)
        self.rootnode=self.TreeNode()
        self.nodestack=[self.rootnode]
        self.feed(data)
        self.close()
        assert len(self.rootnode.children)==1
        self.rootnode=self.rootnode.children[0]
        assert self.rootnode.tag=="html"
        # self.mergedata()

    def handle_starttag(self, tag, attrs):
        # print "start",tag,attrs
        node=self.TreeNode()
        node.tag=tag
        node.attrs=attrs
        self.nodestack[-1].children.append(node)
        self.nodestack.append(node)

    def handle_endtag(self, tag):
        # print "end",tag
        if tag==self.nodestack[-1].tag:
            self.nodestack=self.nodestack[:-1]
        else:
            print tag,"doesn't match tos",self.nodestack[-1].tag
            self.printtree()
            assert False, "HTML is not well formed"


    def handle_entityref(self, name):
        data=htmlentitydefs.entitydefs[name]
        if data=="\xa0": # hard space
            return 
        self.handle_data("&%s;" % (name,))
            
    def handle_data(self, data):
        if len(data.strip())==0:
            return
        # print "data",data
        node=self.TreeNode()
        node.data=data
        self.nodestack[-1].children.append(node)

    def printtree(self, node=None, indent=0):
        if node is None:
            node=self.rootnode
        ins="  "*indent
        if len(node.data):
            print ins+`node.data`
            assert len(node.children)==0
            assert len(node.attrs)==0
        else:
            print ins+"<"+node.tag+"> "+`node.attrs`
            for c in node.children:
               self.printtree(c, indent+1)

    def flatten(self):
        io=cStringIO.StringIO()
        self._flatten(self.rootnode, io)
        return io.getvalue()

    _nltags=("p", "head", "title", "h1", "h2", "h3", "h4", "h5", "table", "tr")
    def _flatten(self, node, io):
        if len(node.data):
            io.write(node.data)
            return

        if node.tag in self._nltags:
            io.write("\n")

        io.write("<%s" % (node.tag,))
        for a,v in node.styles:
            io.write(' %s="%s"' % (a,v))
        for a,v in node.attrs:
            io.write(' %s="%s"' % (a,v))
        io.write(">")

        for child in node.children:
            self._flatten(child,io)

        io.write("</%s>" % (node.tag,))

        if node.tag in self._nltags:
            io.write("\n")

                 

###
###  Turn HTML with style classes in it into expanded HTML without classes
###  This is needed as wxHTML doesn't support style classes
###

def applyhtmlstyles(html, styles):
    tp=TreeParser(html)
    _applystyles(tp.rootnode, styles)
    return tp.flatten()

def _hasclass(node):
    for a,_ in node.attrs:
        if a=="class":
            return True
    return False

def _applystyles(node, styles):
    if len(node.data):
        return

    # wxp tags are left alone
    if node.tag=="wxp":
        return

    if _hasclass(node):
        newattrs=[]
        for a,v in node.attrs:
            if a!="class":
                newattrs.append( (a,v) )
                continue
            c=styles.get(v,None)
            if c is None:
                continue
            _applystyle(node, c)
        node.attrs=newattrs

    for c in node.children:
        _applystyles(c, styles)

def _applystyle(node, style):
    if len(style)==0: return
    if len(node.data): return
    s=style.get('', None)
    if s is not None:
        assert len(s)&1==0 # must even number of items
        for i in range(len(s)/2):
            node.styles.append( (s[i*2], s[i*2+1]) )
        style=style.copy()
        del style['']
    # do we have any add styles
    if len([k for k in style if k[0]=='+']):
        newstyle={}
        for k in style:
            if k[0]!='+':
                newstyle[k]=style[k]
                continue
            # make a child node with this style in it
            kid=TreeParser.TreeNode()
            kid.tag=k[1:]
            kid.children=node.children
            node.children=[kid]
            # copy style
            s=style[k]
            assert len(s)&1==0 # must even number of items
            for i in range(len(s)/2):
                kid.styles.append( (s[i*2], s[i*2+1]) )
        style=newstyle
    if len(style)==0: return
    # ok, apply style to us and any children
    if node.tag in style:
        s=style[node.tag]
        assert len(s)&1==0 # must even number of items
        for i in range(len(s)/2):
            node.styles.append( (s[i*2], s[i*2+1]) )
    for i in node.children:
        _applystyle(i, style)

class HtmlEasyPrinting:
    """Similar to wxHtmlEasyPrinting, except this is actually useful.

    The following additions are present:

      - The various settings are saved in a supplied config object
      - You can set the scale for the fonts, otherwise the default
        is way too large (you would get about 80 chars across)
    """

    def __init__(self, parent=None, config=None, configstr=None):
        self.parent=parent
        self.config=config
        self.configstr=configstr
        self.printData=wx.PrintData()
        self._configtoprintdata(self.printData)
        # setup margins
        self._configtopagesetupdata()

    def SetParentFrame(self, parent):
        self.parent=parent

    def PrinterSetup(self):
        printerDialog = wx.PrintDialog(self.parent)
        printerDialog.GetPrintDialogData().SetPrintData(self.printData)
        printerDialog.GetPrintDialogData().SetSetupDialog(True)
        if printerDialog.ShowModal()==wx.ID_OK:
            self.printData = printerDialog.GetPrintDialogData().GetPrintData()
            self._printdatatoconfig(self.printData)
        printerDialog.Destroy()

    def PageSetup(self):
        psdd=wx.PageSetupDialogData()
        psdd.SetPrintData(self.printData)
        self._configtopagesetupdata(psdd)
        pageDialog=wx.PageSetupDialog(self.parent, psdd)
        if pageDialog.ShowModal()==wx.ID_OK:
            self.printData = pageDialog.GetPageSetupData().GetPrintData()
            self._printdatatoconfig(self.printData)
            self._pagesetupdatatoconfig(pageDialog.GetPageSetupData())
        pageDialog.Destroy()

    def PreviewText(self, htmltext, basepath="", scale=1.0):
        printout1=self._getprintout(htmltext, basepath, scale)
        printout2=self._getprintout(htmltext, basepath, scale)
        preview=wx.PrintPreview(printout1, printout2, self.printData)
        if not preview.Ok():
            print "preview problem"
            assert False, "preview problem"
            return
        self.frame=wx.PreviewFrame(preview, self.parent, "Print Preview")
        guiwidgets.set_size(self.config, "PrintPreview", self.frame, screenpct=90, aspect=0.58)
        wx.EVT_CLOSE(self.frame, self.OnPreviewClose)
        self.frame.Initialize()
        # self.frame.SetPosition(self.parent.GetPosition())
        # self.frame.SetSize(self.parent.GetSize())
        self.frame.Show(True)

    def PrintText(self, htmltext, basepath="", scale=1.0):
        pdd=wx.PrintDialogData()
        pdd.SetPrintData(self.printData)
        printer=wx.Printer(pdd)
        printout=self._getprintout(htmltext, basepath, scale)
        if printer.Print(self.parent, printout):
            self.printData=printer.GetPrintDialogData().GetPrintData()
            self._printdatatoconfig(self.printData)
        printout.Destroy()

    def _getprintout(self, htmltext, basepath, scale):
        print "scale is",scale," margins are", self.margins
        printout=wx.html.HtmlPrintout()
        basesizes=[7,8,10,12,16,22,30]
        printout.SetFonts("", "", [int(sz*scale) for sz in basesizes])
        printout.SetMargins(*self.margins)
        printout.SetHtmlText(htmltext, basepath)
        return printout

    def _printdatatoconfig(self, pd):
        if self.config is None: return
        c=self.config
        cstr=self.configstr

        for key,func in [ ("collate", pd.GetCollate),
                          ("colour", pd.GetColour),
                          ("duplex", pd.GetDuplex),
                          ("nocopies", pd.GetNoCopies),
                          ("orientation", pd.GetOrientation),
                          ("paperid", pd.GetPaperId),
                          ]:
            c.WriteInt(cstr+"/"+key, func())
        c.Write(cstr+"/printer", pd.GetPrinterName())
        c.Flush()
        
    def _configtoprintdata(self, pd):
        if self.config is None: return
        c=self.config
        cstr=self.configstr
        for key,func in [ ("collate", pd.SetCollate),
                          ("colour", pd.SetColour),
                          ("duplex", pd.SetDuplex),
                          ("nocopies", pd.SetNoCopies),
                          ("orientation", pd.SetOrientation),
                          ("paperid", pd.SetPaperId),
                          ]:
            if c.HasEntry(cstr+"/"+key): func(c.ReadInt(cstr+"/"+key))
        # special case - set paper to letter if not explicitly set (wx defaults to A4)
        if not c.HasEntry(cstr+"/paperid"):
            pd.SetPaperId(wx.PAPER_LETTER)
        # printer name
        pd.SetPrinterName(c.Read(cstr+"/printer", ""))

    def _configtopagesetupdata(self, psdd=None):
        v=self.config.Read(self.configstr+"/margins", "")
        if len(v):
            l=[int(x) for x in v.split(',')]
        else:
            l=[15,15,15,15]
        if psdd is not None:
            psdd.SetMarginTopLeft( (l[0], l[1]) )
            psdd.SetMarginBottomRight( (l[2], l[3]) )
        self.margins=l

    def _pagesetupdatatoconfig(self, psdd):
        tl=psdd.GetMarginTopLeft()
        br=psdd.GetMarginBottomRight()
        v="%d,%d,%d,%d" % (tl[0], tl[1], br[0], br[1])
        self.config.Write(self.configstr+"/margins", v)
        self.margins=[tl[0],tl[1],br[0],br[1]]

    def OnPreviewClose(self, event):
        guiwidgets.save_size(self.config, "PrintPreview", self.frame.GetRect())
        event.Skip()

# done down here to prevent circular imports
import guiwidgets

        
if __name__=='__main__':
    src="""
<HTML>
<head><title>A title</title></head>

<body>
<h1 cLaSs="gaudy">Heading 1</h1>

<p>This is my sentence <span class=hilite>with some hilite</span></p>

<p><table><tr><th>one</th><th>two</th></tr>
<tr><td class="orange">orange</td><td>Normal</td></tr>
<tr class="orange"><td>whole row is</td><td>orange</td></tr>
</table></p>
</body>
</html>
"""
    styles={
        'gaudy': 
        {
        '+font': ('color', '#123456'),
        '': ('bgcolor', 'grey'),
        },
        
        'orange':
        {
        '+font': ('color', '#001122'),
        'tr': ('bgcolor', '#cc1122'),
        'td': ('bgcolor', '#cc1122'),
        },
    
        'hilite':
        {
        '+b': (),
        '+font': ('color', '#564bef'),
        }
                   
        }

    tp=TreeParser(src)
    _applystyles(tp.rootnode, styles)
    tp.printtree()
    print tp.flatten()

    app=wx.PySimpleApp()

    f=wx.Frame(None, -1, "HTML Test")
    h=HTMLWindow(f, -1)
    f.Show(True)
    h.SetPage(tp.flatten())
    app.MainLoop()
    sys.exit(0)

# a test of the easy printing
if __name__=='__main__':
    import sys

    def OnSlider(evt):
        global scale
        scale=szlist[evt.GetPosition()]

    f=open(sys.argv[1], "rt")
    html=f.read()
    f.close()

    app=wx.PySimpleApp()

    f=wx.Frame(None, -1, "Print Test")
    butsetup=wx.Button(f, wx.NewId(), "Setup")
    butpreview=wx.Button(f, wx.NewId(), "Preview")
    butprint=wx.Button(f, wx.NewId(), "Print")

    slider=wx.Slider(f, wx.NewId(), 5, 0, 10, style=wx.SL_HORIZONTAL)

    szlist=[0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4]

    scale=1.0

    bs=wx.BoxSizer(wx.HORIZONTAL)
    bs.Add(slider, 1, wx.EXPAND|wx.ALL, 5)
    for i in (butsetup,butpreview, butprint):
        bs.Add(i, 0, wx.EXPAND|wx.ALL, 5)
    f.SetSizer(bs)
    bs.Fit(f)

    hep=HtmlEasyPrinting(f, None, None)

    wx.EVT_BUTTON(f, butsetup.GetId(), lambda _: hep.PrinterSetup())
    wx.EVT_BUTTON(f, butpreview.GetId(), lambda _: hep.PreviewText(html, scale=scale))
    wx.EVT_BUTTON(f, butprint.GetId(), lambda _: hep.PrintText(html, scale=scale))
    wx.EVT_COMMAND_SCROLL(f, slider.GetId(), OnSlider)

    f.Show(True)
    app.MainLoop()
    

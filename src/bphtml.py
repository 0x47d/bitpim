### BITPIM
###
### Copyright (C) 2003-2004 Roger Binns <rogerb@rogerbinns.com>
###
### This software is under the Artistic license.
### Please see the accompanying LICENSE file
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
        self.handle_data(data)
            
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
    applystyles(tp.rootnode, styles)
    return tp.flatten()

def _hasclass(node):
    for a,_ in node.attrs:
        if a=="class":
            return True
    return False

def applystyles(node, styles):
    if len(node.data):
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
        applystyles(c, styles)

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
    applystyles(tp.rootnode, styles)
    tp.printtree()
    print tp.flatten()

    app=wx.PySimpleApp()

    f=wx.Frame(None, -1, "HTML Test")
    h=HTMLWindow(f, -1)
    f.Show(True)
    h.SetPage(tp.flatten())
    app.MainLoop()

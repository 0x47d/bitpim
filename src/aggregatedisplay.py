### BITPIM
###
### Copyright (C) 2004 Roger Binns <rogerb@rogerbinns.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"Displays a number of sections each with a number of items"

import wx

import guihelper

class Display(wx.ScrolledWindow):
    "This is the view"

    # See the long note in OnPaint before touching this

    VSCROLLPIXELS=1 # how many pixels we scroll by
    
    def __init__(self, parent, datasource, watermark=None):
        wx.ScrolledWindow.__init__(self, parent, id=wx.NewId(), style=wx.FULL_REPAINT_ON_RESIZE)
        self.EnableScrolling(False, False)
        self.datasource=datasource
        self._bufbmp=None
        self._w, self._h=self.GetSize()
        self._realw=self._w
        self.vheight, self.maxheight=self._h,self._h
        self.sections=[]
        self.sectionheights=[]
        self._scrollbarwidth=wx.SystemSettings_GetMetric(wx.SYS_VSCROLL_X)
        wx.EVT_SIZE(self, self.OnSize)
        wx.EVT_PAINT(self, self.OnPaint)
        wx.EVT_ERASE_BACKGROUND(self, self.OnEraseBackground)
        # wx.EVT_SCROLLWIN(self, self.OnScroll)
        self.bgbrush=wx.TheBrushList.FindOrCreateBrush(wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW), wx.SOLID)
        if watermark:
            self.watermark=guihelper.getbitmap(watermark)
        else:
            self.watermark=None
        self.relayoutpending=False
        self.ReLayout()

    def OnSize(self, evt):
        w,h=evt.GetSize()
        # we do this check as it saves relayouts when making the window smaller
        if w!=self._realw or h!=self._h:
            self.ReLayout()
        else:
            if not self.relayoutpending:
                print "saved a relayout"
        self._w, self._h=evt.GetSize()
        self._realw=self._w
        if self.vheight>self._h:
            self._w-=self._scrollbarwidth

    def OnEraseBackground(self, _):
        pass

    def OnPaint(self, _):
        # Getting this drawing right involved hours of fighting wxPython/wxWidgets.
        # Those hours of sweating and cursing reveal the following:
        #
        # - The bufferedpaintdc only allocates a bitmap large enough to cover the
        #   viewable window size.  That is used irrespective of the scroll position
        #   which means you get garbage for any part of your window beyond the
        #   initial physical viewable size
        #
        # - The bufferedpaintdc must have its origin reset back to zero by the time
        #   its destructor is called otherwise it won't draw in the right place
        #
        # - The various other calls are very carefully placed (eg size handler, ReLayout
        #   being a callafter etc).  Otherwise really silly things happen due to the
        #   order that things get displayed in, scrollbars adjustments causing your
        #   window to get cropped behind the scenes and various other annoyances, setting
        #   scrollbars changing size etc
        #
        # - The ReLayout happens very frequently.  It may be possible to optimise out
        #   some calls to it.  Tread very carefully and test on multiple platforms.
        #
        # - wx sometimes misbehaves if the window height isn't set to an exact multiple of the
        #   VSCROLLPIXELS
        if self._bufbmp is None or self._bufbmp.GetWidth()<self._w or self._bufbmp.GetHeight()<self.maxheight:
            self._bufbmp=wx.EmptyBitmap(self._w, self.maxheight)
        dc=wx.BufferedPaintDC(self, self._bufbmp)
        origin=self.GetViewStart()[1]*self.VSCROLLPIXELS
        dc.SetBackground(self.bgbrush)
        dc.Clear()
        if self.watermark:
            # place in the middle
            # dc.DrawBitmap(self.watermark, self._w/2-self.watermark.GetWidth()/2, origin+self._h/2-self.watermark.GetHeight()/2, True)
            # place in bottom right
            dc.DrawBitmap(self.watermark, self._w-self.watermark.GetWidth(), origin+self._h-self.watermark.GetHeight(), True)
        cury=0
        for i, section in enumerate(self.sections):
            dc.SetDeviceOrigin(0, +cury )
            section.Draw(dc, self._w)
            cury+=self.sectionheights[i]
        dc.SetDeviceOrigin(0,0)

    def ReLayout(self):
        if self.relayoutpending:
            return
        self.relayoutpending=True
        wx.CallAfter(self._ReLayout)

    def _ReLayout(self):
        self.relayoutpending=False
        self.sections=self.datasource.GetSections()
        self.sectionheights=[]
        self.vheight=0
        for i,section in enumerate(self.sections):
            self.sectionheights.append(section.GetHeight())
        self.vheight+=sum(self.sectionheights)

        # You can't adjust self._w here to take into account the presence of the
        # scrollbar since a size event is generated after the call to setscrollbars
        # so we do the adjustment in the size handler.

        # set the height we want wx to think the window is
        self.maxheight=max(self.vheight,self._h)
        # adjust scrollbar
        self.SetScrollbars(0,1,0,self.maxheight,0, self.GetViewStart()[1])
        self.SetScrollRate(0, self.VSCROLLPIXELS)

class SectionHeader:
    "A generic section header implementation"

    def __init__(self, label):
        self.label=label
        self.InitAttributes()

    def InitAttributes(self):
        "Initialise our font and colours"
        self.font=wx.TheFontList.FindOrCreateFont(60, family=wx.SWISS, style=wx.NORMAL, weight=wx.NORMAL)
        self.font2=wx.TheFontList.FindOrCreateFont(60, family=wx.SWISS, style=wx.NORMAL, weight=wx.LIGHT)
        self.fontcolour=wx.SystemSettings_GetColour(wx.SYS_COLOUR_BTNTEXT)
        self.font2colour=wx.SystemSettings_GetColour(wx.SYS_COLOUR_BTNSHADOW)
        dc=wx.MemoryDC()
        w,h,d,l=dc.GetFullTextExtent("I", font=self.font)
        self.height=h+3
        self.descent=d

    def GetHeight(self):
        return self.height

    def Draw(self, dc, width):
        oldc=dc.GetTextForeground()
        oldf=dc.GetFont()
        dc.DrawLine(3, self.height-self.descent, width-3, self.height-self.descent)
        dc.SetTextForeground(self.font2colour)
        dc.SetFont(self.font2)
        for xoff in (0,1,2):
            for yoff in (0,1,2):
                dc.DrawText(self.label, xoff, yoff)
        dc.SetTextForeground(self.fontcolour)
        dc.SetFont(self.font)
        dc.DrawText(self.label, 1,1)
        dc.SetTextForeground(oldc)
        dc.SetFont(oldf)
                

class DataSource:
    "This is the model"

    def GetSections(self):
        "Return a list of section headers"
        raise NotImplementedError()
    

if __name__=="__main__":

    class TestDS(DataSource):

        def GetSections(self):
            return [SectionHeader(x) for x in ("Camera", "Wallpaper", "Oranges", "Lemons")]


    app=wx.PySimpleApp()
    f=wx.Frame(None)
    ds=TestDS()
    d=Display(f,ds, "wallpaper-watermark")
    f.Show()

    app.MainLoop()
    
    

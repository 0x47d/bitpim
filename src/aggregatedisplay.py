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

    # See the long note in OnPaint before touching this code

    VSCROLLPIXELS=1 # how many pixels we scroll by

    ITEMPADDING=5   # how many pixels we pad items by
    
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
        if watermark is not None:
            wx.EVT_SCROLLWIN(self, self.OnScroll)
        self.bgbrush=wx.TheBrushList.FindOrCreateBrush(wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW), wx.SOLID)
        if watermark:
            self.watermark=guihelper.getbitmap(watermark)
        else:
            self.watermark=None
        self.relayoutpending=False
        self.UpdateItems()

    def OnScroll(self, evt):
        self.Refresh(False)
        evt.Skip()

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
        # we redraw everything that is in the visible area of the screen
        origin=self.GetViewStart()[1]*self.VSCROLLPIXELS
        firstvisible=origin
        lastvisible=origin+self._h

        # clear background
        dc.SetBackground(self.bgbrush)
        dc.Clear()
        # draw watermark
        if self.watermark:
            # place in the middle:
            # dc.DrawBitmap(self.watermark, self._w/2-self.watermark.GetWidth()/2, origin+self._h/2-self.watermark.GetHeight()/2, True)
            # place in bottom right:
            dc.DrawBitmap(self.watermark, self._w-self.watermark.GetWidth(), origin+self._h-self.watermark.GetHeight(), True)

        # draw each section
        cury=0
        for i, section in enumerate(self.sections):
            if _isvisible(cury, cury+self.sectionheights[i], firstvisible, lastvisible):
                dc.SetDeviceOrigin(0, cury )
                section.Draw(dc, self._w)
            cury+=self.sectionheights[i]
            extrawidth=(self._w-6)-(self.itemsize[i][0]+self.ITEMPADDING)*self.itemsperrow[i]
            extrawidth/=self.itemsperrow[i]
            if extrawidth<0: extrawidth=0
            # now draw items in this section
            num=0
            while num<len(self.items[i]):
                x=(num%self.itemsperrow[i])
                y=(num/self.itemsperrow[i])
                posy=cury+y*(self.itemsize[i][1]+self.ITEMPADDING)
                # skip the entire row if it isn't visible
                if x==0 and not _isvisible(posy, posy+self.itemsize[i][1], firstvisible, lastvisible):
                    num+=self.itemsperrow[i]
                    continue
                item=self.items[i][num]
                dc.SetDeviceOrigin(3+x*(self.itemsize[i][0]+self.ITEMPADDING+extrawidth), posy)
                dc.ResetBoundingBox()
                item.Draw(dc, self.itemsize[i][0]+extrawidth, self.itemsize[i][1], False)
                #print "bb",dc.MinX(), dc.MinY(), dc.MaxX(), dc.MaxY()
                num+=1
            cury+=(len(self.items[i])+self.itemsperrow[i]-1)/self.itemsperrow[i]*(self.itemsize[i][1]+self.ITEMPADDING)
                    
        # must do this or the world ends ...
        dc.SetDeviceOrigin(0,0)

    def ReLayout(self):
        "Called if the window size has changed"
        if self.relayoutpending:
            return
        self.relayoutpending=True
        wx.CallAfter(self._ReLayout)

    def _ReLayout(self):
        self.relayoutpending=False
        self.itemsperrow=[]
        self.vheight=0
        for i,section in enumerate(self.sections):
            self.vheight+=self.sectionheights[-1]
            self.itemsperrow.append(max((self._w-6)/(self.itemsize[i][0]+self.ITEMPADDING),1))
            rows=(len(self.items[i])+self.itemsperrow[i]-1)/self.itemsperrow[i]
            self.vheight+=rows*(self.itemsize[i][1]+self.ITEMPADDING)

        # set the height we want wx to think the window is
        self.maxheight=max(self.vheight,self._h)
        # adjust scrollbar
        self.SetScrollbars(0,1,0,self.vheight,0, self.GetViewStart()[1])
        self.SetScrollRate(0, self.VSCROLLPIXELS)

    def UpdateItems(self):
        "Called if you want the items to be refetched from the model"
        self.sections=self.datasource.GetSections()
        self.items=[]
        self.itemsize=[]
        self.sectionheights=[]
        for i,section in enumerate(self.sections):
            self.sectionheights.append(section.GetHeight())
            self.itemsize.append(self.datasource.GetItemSize(i,section))
            items=self.datasource.GetItemsFromSection(i,section)            
            self.items.append(items)
        # we have to relayout immediately otherwise there could a be paint call
        # between this function and relayout and the variables would be in an
        # inconsistent state
        self._ReLayout()
            
def _isvisible(start, end, firstvisible, lastvisible):
    return start <= firstvisible <= end <= lastvisible or \
           (start >= firstvisible and start <= lastvisible) or \
           (start <= firstvisible and end >=lastvisible)


class SectionHeader(object):
    "A generic section header implementation"

    def __init__(self, label):
        self.label=label
        self.InitAttributes()

    def InitAttributes(self):
        "Initialise our font and colours"
        self.font=wx.TheFontList.FindOrCreateFont(20, family=wx.SWISS, style=wx.NORMAL, weight=wx.NORMAL)
        self.font2=wx.TheFontList.FindOrCreateFont(20, family=wx.SWISS, style=wx.NORMAL, weight=wx.LIGHT)
        self.fontcolour=wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNTEXT)
        self.font2colour=wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNSHADOW)
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
                dc.DrawText(self.label, xoff+3, yoff)
        dc.SetTextForeground(self.fontcolour)
        dc.SetFont(self.font)
        dc.DrawText(self.label, 1+3,1)
        dc.SetTextForeground(oldc)
        dc.SetFont(oldf)
                
class Item(object):
    """A generic item implementation.

    You don't need to inherit from this - it is mainly to document what you have to implement."""

    def Draw(self, dc, width, height, selected):
        """Draw yourself into the available space.  0,0 will be your top left.

        Note that the width may be larger than the
        L{DataSource.GetItemSize} method returned because unused space
        is spread amongst the items.  It will never be smaller than
        what was returned.  You should set the clipping region if
        necessary.

        @param dc:  The device context to draw into
        @param width: maximum space to use
        @param height: maximum space to use
        @param selected: if the item is currently selected"""
        raise NotImplementedError()
    


class DataSource(object):
    """This is the model

    You don't need to inherit from this - it is mainly to document what you have to implement."""

    def GetSections(self):
        "Return a list of section headers"
        raise NotImplementedError()

    def GetItemSize(self, sectionnumber, sectionheader):
        "Return (width, height of each item)"
        return (160, 80)

    def GetItemsFromSection(self,sectionnumber,sectionheader):
        """Return a list of the items for the section.

        @param sectionnumber: the index into the list returned by L{GetSections}
        @param sectionheader: the section header object from that list
        """
        raise NotImplementedError()

if __name__=="__main__":
    app=wx.PySimpleApp()

    import sys
    import common
    sys.excepthook=common.formatexceptioneh
    import wx.html
    import os
    import brewcompressedimage
    import wallpaper


    # find bitpim wallpaper directory
    config=wx.Config("bitpim", style=wx.CONFIG_USE_LOCAL_FILE)

    p=config.Read("path", "resources")
    pn=os.path.join(p, "wallpaper")
    if os.path.isdir(pn):
        p=pn

    imagespath=p
    images=[name for name in os.listdir(imagespath) if name[-4:] in (".bci", ".bmp", ".jpg", ".png")]
    images.sort()
    #images=images[:9]

    print imagespath
    print images

    class WallpaperManager:

        def GetImageStatInformation(self,name):
            return wallpaper.statinfo(os.path.join(imagespath, name))    

        def GetImageConstructionInformation(self,file):
            file=os.path.join(imagespath, file)

            if file.endswith(".mp4") or not os.path.isfile(file):
                return guihelper.getresourcefile('wallpaper.png'), wx.Image
            if self.isBCI(file):
                return file, lambda name: brewcompressedimage.getimage(brewcompressedimage.FileInputStream(file))
            return file, wx.Image

        def isBCI(self, filename):
            # is it a bci file?
            return open(filename, "rb").read(4)=="BCI\x00"

    
    wx.FileSystem_AddHandler(wallpaper.BPFSHandler(WallpaperManager()))
    
    class TestItem(Item):

        def __init__(self, ds, secnum, itemnum, label):
            super(TestItem,self).__init__()
            self.label=label
            self.ds=ds
            self.secnum=secnum
            self.itemnum=itemnum

        def Draw(self, dc, width, height, selected):
            # uncomment to see exactly what size is given
            #dc.DrawRectangle(0,0,width,height)

            us=dc.GetUserScale()
            dc.SetClippingRegion(0,0,width,height)
            hdc=wx.html.HtmlDCRenderer()
            hdc.SetDC(dc, 1)
            hdc.SetSize(99999, 9999) # width is deliberately wide so that no wrapping happens
            hdc.SetHtmlText(self.genhtml(), '.', True)
            hdc.Render(0,0)
            del hdc
            # restore scale hdc messes
            dc.SetUserScale(*us)
            dc.DestroyClippingRegion()

        def genhtml(self):
            return """<table><tr><td valign=top><p><img src="bpuserimage:%s;width=%d;height=%d;valign=top"><td valign=top><b>%s</b><br>BMP format<br>123x925<br>Camera</tr></table>""" \
                   % (images[self.itemnum], self.ds.IMGSIZES[self.secnum][0], self.ds.IMGSIZES[self.secnum][1], self.label, )

    class TestDS(DataSource):

        SECTIONS=("Camera", "Wallpaper", "Oranges", "Lemons")
        ITEMSIZES=( (240,240), (160,70), (48,48), (160,70) )
        IMGSIZES=[ (w-110,h-20) for w,h in ITEMSIZES]
        IMGSIZES[2]=(16,16)

        def GetSections(self):
            return [SectionHeader(x) for x in self.SECTIONS]

        def GetItemsFromSection(self, sectionnumber, sectionheader):
            return [TestItem(self, sectionnumber, i, "%s-#%d" % (sectionheader.label,i)) for i in range(len(images))]

        def GetItemSize(self, sectionnumber, sectionheader):
            return self.ITEMSIZES[sectionnumber]

    f=wx.Frame(None, title="Aggregate Display Test")
    ds=TestDS()
    d=Display(f,ds, "wallpaper-watermark")
    f.Show()

    app.MainLoop()
    
    

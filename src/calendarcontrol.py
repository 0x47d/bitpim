#!/usr/bin/env python

from wxPython.wx import *

class CalendarCellAttributes:
    def __init__(self):
        # Set some defaults
        self.labelfont=wxFont(20, wxSWISS, wxNORMAL, wxNORMAL )
        self.labelforeground=wxNamedColour("CORNFLOWER BLUE")
        self.labelalign=wxALIGN_RIGHT
        self.timefont=wxFont(10, wxSWISS, wxNORMAL, wxNORMAL )
        self.timeforeground=wxNamedColour("ORCHID")
        self.entryfont=wxFont(15, wxSWISS, wxNORMAL, wxNORMAL )
        self.entryforeground=wxNamedColour("BLACK")
        self.miltime=True

    def isrightaligned(self):
        return self.labelalign==wxALIGN_RIGHT

    def ismiltime(self):
        return self.miltime

    def setforlabel(self, dc):
        dc.SetFont(self.labelfont)
        dc.SetTextForeground(self.labelforeground)

    def setfortime(self,dc):
        dc.SetFont(self.timefont)
        dc.SetTextForeground(self.timeforeground)

    def setforentry(self, dc):
        dc.SetFont(self.entryfont)
        dc.SetTextForeground(self.entryforeground)


DefaultCalendarCellAttributes=CalendarCellAttributes()

class CalendarCell(wxWindow):

    def __init__(self, parent, id, attr=DefaultCalendarCellAttributes, style=wxSIMPLE_BORDER):
        wxWindow.__init__(self, parent, id, style=style)
        self.attr=attr
        self.day=13
        EVT_PAINT(self, self.OnPaint)
        EVT_SIZE(self, self.OnSize)
        self.OnSize(None)

        self.entries=(
            (1, 88, "Early morning"),
            (10,15, "Some explanatory text" ),
            (11,11, "Look at me!"),
            (12,30, "More text here"),
            (15,30, "A very large amount of text that will never fit"),
            (20,30, "Evening drinks"),
            )

    def OnSize(self, _=None):
        self.width, self.height = self.GetClientSizeTuple()

    def OnPaint(self, _=None):
        dc=wxPaintDC(self)
        self.draw(dc)

    def draw(self, dc):
        print "draw", self.width, self.height
        # do the label
        self.attr.setforlabel(dc)
        w,h=dc.GetTextExtent(`self.day`)
        x=5
        if self.attr.isrightaligned():
            x=self.width-(w+5)
        dc.DrawText(`self.day`, x, 0)

        entrystart=h
        dc.DestroyClippingRegion()
        dc.SetClippingRegion( 0, entrystart, self.width, self.height-entrystart)

        while 1: # this loop scales the contents to fit the space available
            # now calculate how much space is needed for the time fields
            self.attr.setfortime(dc)
            boundingspace=10
            space,_=dc.GetTextExtent(" ")
            timespace,timeheight=dc.GetTextExtent("88:88")
            if self.attr.ismiltime():
                ampm=0
            else:
                ampm,_=dc.GetTextExtent(" mm")

            leading=0

            self.attr.setforentry(dc)
            _,entryheight=dc.GetTextExtent(" ")
            firstrowheight=max(timeheight, entryheight)

            # Now draw each item
            lastap=""
            y=entrystart/dc.GetUserScale()[0]+5
            for h,m,desc in self.entries:
                x=0
                self.attr.setfortime(dc)
                # bounding
                x+=boundingspace # we don't draw anything yet
                timey=y
                if timeheight<firstrowheight:
                    timey+=firstrowheight-timeheight
                text=""
                if not self.attr.ismiltime():
                    ap="am"
                    if h>=12: ap="pm"
                    h%=12
                    if h==0: h=12
                if h<10: text+=" "
                text+="%d:%02d" % (h,m)
                dc.DrawText(text, x, timey)
                x+=timespace
                x+=space
                if not self.attr.ismiltime():
                    if lastap!=ap:
                        dc.DrawText(ap, x, timey)
                        lastap=ap
                    x+=ampm+space
                self.attr.setforentry(dc)
                ey=y
                if entryheight<firstrowheight:
                    ey+=firstrowheight-ey
                dc.DrawText(desc, x, ey)
                # that row is dealt with!
                y+=firstrowheight
            if y>self.height/dc.GetUserScale()[1]:
                dc.Clear()
                factorx,factory=dc.GetUserScale()
                dc.SetUserScale(0.9*factorx, 0.9*factory)
            else:
                break

        



if __name__=="__main__":
    class MainWindow(wxFrame):
        def __init__(self, parent, id, title):
            wxFrame.__init__(self, parent, id, title, size=(200,100),
                             style=wxDEFAULT_FRAME_STYLE|wxNO_FULL_REPAINT_ON_RESIZE)
            self.control=CalendarCell(self, 1)
            self.Show(True)
    
    app=wxPySimpleApp()
    frame=MainWindow(None, -1, "Calendar Test")
    app.MainLoop()

#!/usr/bin/env python

### BITPIM
###
### Copyright (C) 2003 Roger Binns <rogerb@rogerbinns.com>
###
### This software is under the Artistic license.
### http://www.opensource.org/licenses/artistic-license.php
###
### $Id$

# This design is with aplogies to Alan Cooper

from wxPython.wx import *
from wxPython.lib.rcsizer import RowColSizer
import calendar
import time

class CalendarCellAttributes:
    def __init__(self):
        # Set some defaults
        self.labelfont=wxFont(20, wxSWISS, wxNORMAL, wxNORMAL )
        self.labelforeground=wxNamedColour("CORNFLOWER BLUE")
        self.labelalign=wxALIGN_RIGHT
        self.timefont=wxFont(10, wxMODERN, wxNORMAL, wxNORMAL )
        self.timeforeground=wxNamedColour("ORCHID")
        self.entryfont=wxFont(15, wxSWISS, wxNORMAL, wxNORMAL )
        self.entryforeground=wxNamedColour("BLACK")
        self.miltime=True

    def isrightaligned(self):
        return self.labelalign==wxALIGN_RIGHT

    def ismiltime(self):
        return self.miltime

    def setforlabel(self, dc, fontscale=1):
        self.setscaledfont(dc, self.labelfont, fontscale)
        dc.SetTextForeground(self.labelforeground)

    def setfortime(self,dc, fontscale=1):
        self.setscaledfont(dc, self.timefont, fontscale)
        dc.SetTextForeground(self.timeforeground)

    def setforentry(self, dc, fontscale=1):
        self.setscaledfont(dc, self.entryfont, fontscale)
        dc.SetTextForeground(self.entryforeground)

    def setscaledfont(self, dc, font, fontscale):
        if fontscale==1:
            dc.SetFont(font)
            return
        f=wxFont(font.GetPointSize()*fontscale, font.GetFamily(), font.GetStyle(), font.GetWeight())
        dc.SetFont(f)


DefaultCalendarCellAttributes=CalendarCellAttributes()

class CalendarCell(wxWindow):

    def __init__(self, parent, id, attr=DefaultCalendarCellAttributes, style=wxSIMPLE_BORDER):
        wxWindow.__init__(self, parent, id, style=style)
        self.attr=attr
        self.day=33
        self.year=2033
        self.month=3
        self.buffer=None
        self.needsupdate=True

        # Some fake entries for testing
        self.entries=(
            (1, 88, "Early morning"),
            (10,15, "Some explanatory text" ),
            (11,11, "Look at me!"),
            (12,30, "More text here"),
            (15,30, "A very large amount of text that will never fit"),
            (20,30, "Evening drinks"),
            )

        EVT_PAINT(self, self.OnPaint)
        EVT_SIZE(self, self.OnSize)
        EVT_ERASE_BACKGROUND(self, self.OnEraseBackground)
        self.OnSize(None)

    def OnEraseBackground(self, _):
        pass

    def setdate(self, year, month, day):
        self.year=year
        self.month=month
        self.day=day
        self.needsupdate=True
        self.Refresh(False)

    def getdate(self):
        return (self.year, self.month, self.day)

    def OnSize(self, _=None):
        self.width, self.height = self.GetClientSizeTuple()
        self.needsupdate=True

    def redraw(self):
        if self.buffer is None or \
           self.buffer.GetWidth()!=self.width or \
           self.buffer.GetHeight()!=self.height:
            if self.buffer is not None:
                del self.buffer
            self.buffer=wxEmptyBitmap(self.width, self.height)

        mdc=wxMemoryDC()
        mdc.SelectObject(self.buffer)
        mdc.Clear()
        self.draw(mdc)
        mdc.SelectObject(wxNullBitmap)
        del mdc

    def OnPaint(self, _=None):
        if self.needsupdate:
            self.needsupdate=False
            self.redraw()
        dc=wxPaintDC(self)
        dc.DrawBitmap(self.buffer, 0, 0, False)

    def draw(self, dc):
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

        fontscale=1.0
        iteration=0
        while 1: # this loop scales the contents to fit the space available
            iteration+=1
            # now calculate how much space is needed for the time fields
            self.attr.setfortime(dc, fontscale)
            boundingspace=10
            space,_=dc.GetTextExtent(" ")
            timespace,timeheight=dc.GetTextExtent("88:88")
            if self.attr.ismiltime():
                ampm=0
            else:
                ampm,_=dc.GetTextExtent(" mm")

            leading=0

            self.attr.setforentry(dc, fontscale)
            _,entryheight=dc.GetTextExtent(" ")
            firstrowheight=max(timeheight, entryheight)

            # Now draw each item
            lastap=""
            y=entrystart+5
            for h,m,desc in self.entries:
                x=0
                self.attr.setfortime(dc, fontscale)
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
                self.attr.setforentry(dc, fontscale)
                ey=y
                if entryheight<firstrowheight:
                    ey+=firstrowheight-ey
                dc.DrawText(desc, x, ey)
                # that row is dealt with!
                y+=firstrowheight
            if iteration<10 and y>self.height:
                dc.Clear()
                # how much too big were we?
                fontscale=fontscale*float(self.height)/y
            else:
                break

class CalendarLabel(wxWindow):
    # This is the label on the left of the day cells that shows
    # the month (rotated text)
    def __init__(self, parent, cells, id=-1):
        wxWindow.__init__(self, parent, id)
        self.needsupdate=True
        self.buffer=None
        self.cells=cells
        EVT_PAINT(self, self.OnPaint)
        EVT_SIZE(self, self.OnSize)
        EVT_ERASE_BACKGROUND(self, self.OnEraseBackground)
        self.setfont(wxFont(20, wxSWISS, wxNORMAL, wxBOLD ))
        self.settextcolour(wxNamedColour("ORCHID"))
        self.OnSize(None)

    def OnEraseBackground(self, _):
        pass

    def OnSize(self, _=None):
        self.width, self.height = self.GetClientSizeTuple()
        self.needsupdate=True
        
    def OnPaint(self, _=None):
        if self.needsupdate:
            self.needsupdate=False
            self.redraw()
        dc=wxPaintDC(self)
        dc.DrawBitmap(self.buffer, 0, 0, False)

    def setfont(self, font):
        self.font=font

    def settextcolour(self, colour):
        self.colour=colour

    def changenotify(self):
        self.needsupdate=True
        self.Refresh()

    def redraw(self):
        if self.buffer is None or \
           self.buffer.GetWidth()!=self.width or \
           self.buffer.GetHeight()!=self.height:
            if self.buffer is not None:
                del self.buffer
            self.buffer=wxEmptyBitmap(self.width, self.height)

        mdc=wxMemoryDC()
        mdc.SelectObject(self.buffer)
        mdc.SetBackground(wxTheBrushList.FindOrCreateBrush(self.GetBackgroundColour(), wxSOLID))
        mdc.Clear()
        self.draw(mdc)
        mdc.SelectObject(wxNullBitmap)
        del mdc

    def draw(self, dc):
        # find the lines for each cell
        row=0
        while row<len(self.cells):
            month=self.cells[row].month
            endrow=row
            for r2 in range(row+1,len(self.cells)):
                if month==self.cells[r2].month:
                    endrow=r2
                else:
                    break
            # row is begining row, endrow is end, inclusive

            # find the space available.  we do lots of lovely math
            # in order to translate the coordinates from the rows
            # into our window
            x=0
            y=self.cells[row].GetPositionTuple()[1]-self.cells[0].GetPositionTuple()[1]
            w=self.width
            h=self.cells[endrow].GetPositionTuple()[1]+self.cells[endrow].GetRect().height \
               -self.cells[row].GetPositionTuple()[1]

            
            print x,y,w,h

            dc.DestroyClippingRegion()
            dc.SetClippingRegion(x,y,w,h)
            dc.SetPen(wxThePenList.FindOrCreatePen("BLACK", 3, wxSOLID))
            # draw line at top and bottom
            if row!=0:
                dc.DrawLine(x, y, x+w, y)
            if endrow!=len(self.cells)-1:
                dc.DrawLine(x, y+h, x+w, y+h)
            month=calendar.month_name[month]
            dc.SetFont(self.font)
            dc.SetTextForeground(self.colour)
            tw,th=dc.GetTextExtent(month)
            # Now figure out where to draw it
            if tw<h:
                # it fits, so centre
                dc.DrawRotatedText(month, w/2-th/2, y + h/2 + tw/2, 90)
                


            # Loop around
            row=endrow+1


class Calendar(wxPanel):
    # All the horrible date code is an excellent case for metric time!
    ID_UP=1
    ID_DOWN=2
    def __init__(self, parent, rows=5, id=-1):
        wxPanel.__init__(self, parent, id, style=wxNO_FULL_REPAINT_ON_RESIZE)
        sizer=RowColSizer()
        self.upbutt=wxButton(self, self.ID_UP, "^")
        sizer.Add(self.upbutt, flag=wxEXPAND, row=0,col=0, colspan=8)
        self.year=wxButton(self, -1, "2003")
        sizer.Add(self.year, flag=wxEXPAND, row=1, col=0)
        p=1
        calendar.setfirstweekday(calendar.SUNDAY)
        for i in ( "Sun", "Mon", "Tue", "Wed" , "Thu", "Fri", "Sat" ):
           sizer.Add(  wxStaticText( self, -1, i, style=wxALIGN_CENTER|wxALIGN_CENTER_VERTICAL),
                       flag=wxALIGN_CENTER_VERTICAL|wxALIGN_CENTER_HORIZONTAL|wxEXPAND, row=1, col=p)
           sizer.AddGrowableCol(p)
           p+=1
        self.numrows=rows
        self.showrow=rows/2
        self.rows=[]
        for i in range(0, rows):
            self.rows.append( self.makerow(sizer, i+2) )
        self.downbutt=wxButton(self, self.ID_DOWN, "V")
        sizer.Add(self.downbutt, flag=wxEXPAND, row=2+rows, col=0, colspan=8)
        self.label=CalendarLabel(self, map(lambda x: x[0], self.rows))
        sizer.Add(self.label, flag=wxEXPAND, row=2, col=0, rowspan=self.numrows)
        self.SetSizer(sizer)
        self.SetAutoLayout(True)
#        EVT_BUTTON(self, self.ID_UP, self.OnUp)
        EVT_BUTTON(self, self.ID_DOWN, self.OnScrollDown)
        EVT_ERASE_BACKGROUND(self, self.OnEraseBackground)


    def OnEraseBackground(self, _):
        pass

    def makerow(self, sizer, row):
        res=[]
        sizer.AddGrowableRow(row)
        for i in range(0,7):
            res.append( CalendarCell(self, -1) )
            sizer.Add( res[-1], flag=wxEXPAND, row=row, col=i+1)
        return res

    def OnScrollDown(self, _=None):
        # user has pressed scroll down button
        for row in range(0, self.numrows):
                y,m,d=self.rows[row][0].getdate()
                y,m,d=normalizedate(y,m,d+7)
                self.updaterow(row, y,m,d)
        self.label.changenotify()
        

    def setday(self, year, month, day):
        # makes specified day be shown and selected
        d=calendar.weekday(year, month, day)
        d=(d+1)%7

        r=self.showrow
        c=d
        y=year
        m=month
        d=day
        # Fill in calendar going forward
        daysinmonth=calendar.monthrange(y, m)[1]
        while r<self.numrows:
            self.updatecell(r, c, y, m, d)
            if d==daysinmonth:
                d=1
                m+=1
                if m==13:
                    m=1
                    y+=1
                daysinmonth=calendar.monthrange(y, m)
            else:
                d+=1
            c+=1
            if c==7:
                r+=1
                c=0
        # Fill in going backwards
        d=calendar.weekday(year, month, day)
        d=(d+1)%7

        r=self.showrow
        c=d
        y=year
        m=month
        d=day
        while r>=0:
            self.updatecell(r, c, y, m, d)
            if d==1:
                m-=1
                if m==0:
                    m=12
                    y-=1
                d=calendar.monthrange(y,m)[1]
            else: d-=1
            c-=1
            if c<0:
                c=6
                r-=1

    def updaterow(self, row, y, m, d):
        daysinmonth=calendar.monthrange(y, m)[1]
        for c in range(0,7):
            self.updatecell(row, c, y, m, d)
            if d==daysinmonth:
                d=1
                m+=1
                if m==13:
                    m=1
                    y+=1
                daysinmonth=calendar.monthrange(y, m)[1]
            else:
                d+=1

    def updatecell(self, row, column, y, m, d):
        self.rows[row][column].setdate(y,m,d)
        # ::TODO:: get events for this day
        


def normalizedate(year, month, day):
    # metric system please .....
    if month<1:
        year-=1
        month=month+12
    if month>12:
        year+=1
        month-=13
    if day<1:
        month-=1
        if month<1:
            month=12
            year-=1
        num=calendar.monthrange(year, month)[1]
        day=num-day
    else:
        num=calendar.monthrange(year, month)[1]
        if day>num:
            month+=1
            if month>12:
                month=1
                year+=1
            day=day-num
    return year, month, day
            

 


if __name__=="__main__":
    class MainWindow(wxFrame):
        def __init__(self, parent, id, title):
            wxFrame.__init__(self, parent, id, title, size=(800,600),
                             style=wxDEFAULT_FRAME_STYLE|wxNO_FULL_REPAINT_ON_RESIZE)
            #self.control=CalendarCell(self, 1) # test just the cell
            self.control=Calendar(self)
            now=time.localtime()
            self.control.setday(now[0], now[1], now[2])
            self.Show(True)
    
    app=wxPySimpleApp()
    frame=MainWindow(None, -1, "Calendar Test")
    app.MainLoop()

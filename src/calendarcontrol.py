#!/usr/bin/env python

### BITPIM
###
### Copyright (C) 2003 Roger Binns <rogerb@rogerbinns.com>
###
### This software is under the Artistic license.
### http://www.opensource.org/licenses/artistic-license.php
###
### $Id$

# This design is with apologies to Alan Cooper

from wxPython.wx import *
from wxPython.lib.rcsizer import RowColSizer
from wxPython.calendar import *
import cStringIO
import calendar
import time


class FontscaleCache(dict):
    # cache results of what the scale factor is to fit a number of lines in a space is
    def get(self, y, attr, numentries):
        return dict.get(self, (y, id(attr), numentries), 1)
    def set(self, y, attr, numentries, scale):
        self[(y, id(attr),  numentries)]=scale
    def uncache(self, *args):
        # clear out any cached attrs listed in args (eg when they are changed)
        keys=self.keys()
        l2=[id(x) for x in args]
        for y, idattr, numentries in keys:
            if idattr in l2:
                del self[ (y, idattr, numentries) ]

thefontscalecache=FontscaleCache()

class CalendarCellAttributes:
    def __init__(self):
        # Set some defaults
        self.cellbackground=wxTheBrushList.FindOrCreateBrush(wxColour(230,255,255), wxSOLID)
        #self.cellbackground=wxBrush(wxColour(197,255,255), wxSOLID)
        self.labelfont=wxFont(14, wxSWISS, wxNORMAL, wxNORMAL )
        self.labelforeground=wxNamedColour("CORNFLOWER BLUE")
        self.labelalign=wxALIGN_RIGHT
        self.timefont=wxFont(10, wxSWISS, wxNORMAL, wxNORMAL )
        self.timeforeground=wxNamedColour("ORCHID")
        self.entryfont=wxFont(10, wxSWISS, wxNORMAL, wxNORMAL )
        self.entryforeground=wxNamedColour("BLACK")
        self.miltime=False
        self.initdone=True

    def __setattr__(self, k, v):
        self.__dict__[k]=v
        if hasattr(self, 'initdone'):
            thefontscalecache.uncache(self)

    def isrightaligned(self):
        return self.labelalign==wxALIGN_RIGHT

    def ismiltime(self):
        return self.miltime

    def setforcellbackground(self, dc):
        dc.SetBackground(self.cellbackground)

    def setforlabel(self, dc, fontscale=1):
        dc.SetTextForeground(self.labelforeground)
        return self.setscaledfont(dc, self.labelfont, fontscale)

    def setfortime(self,dc, fontscale=1):
        dc.SetTextForeground(self.timeforeground)
        return self.setscaledfont(dc, self.timefont, fontscale)

    def setforentry(self, dc, fontscale=1):
        dc.SetTextForeground(self.entryforeground)
        return self.setscaledfont(dc, self.entryfont, fontscale)
                
    def setscaledfont(self, dc, font, fontscale):
        "Returns False if the font is already at smallest scale"
        if fontscale==1:
            dc.SetFont(font)
            return True
        ps=int(font.GetPointSize()*fontscale)
        if ps<2:
            ps=2
        f=wxTheFontList.FindOrCreateFont(ps, font.GetFamily(), font.GetStyle(), font.GetWeight())
        dc.SetFont(f)
        if ps==2:
            return False
        return True


DefaultCalendarCellAttributes=CalendarCellAttributes()

                
class CalendarCell(wxWindow):

    fontscalecache=FontscaleCache()

    def __init__(self, parent, id, attr=DefaultCalendarCellAttributes, style=wxSIMPLE_BORDER):
        wxWindow.__init__(self, parent, id, style=style|wxWANTS_CHARS)
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

    def setattr(self, attr):
        self.attr=attr
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
        self.attr.setforcellbackground(mdc)
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
        x=1
        if self.attr.isrightaligned():
            x=self.width-(w+5)
        dc.DrawText(`self.day`, x, 0)

        entrystart=h # +5
        dc.DestroyClippingRegion()
        dc.SetClippingRegion( 0, entrystart, self.width, self.height-entrystart)

        fontscale=thefontscalecache.get(self.height-entrystart, self.attr, len(self.entries))
        iteration=0
         # this loop scales the contents to fit the space available
         # we do it as a loop because even when we ask for a smaller font
         # after finding out that it was too big the first time, the
         # smaller font may not be as small as we requested
        while 1:
            y=entrystart
            iteration+=1
            # now calculate how much space is needed for the time fields
            self.attr.setfortime(dc, fontscale)
            boundingspace=2
            space,_=dc.GetTextExtent("i")
            timespace,timeheight=dc.GetTextExtent("mm:mm")
            if self.attr.ismiltime():
                ampm=0
            else:
                ampm,_=dc.GetTextExtent("a")

            leading=0

            r=self.attr.setforentry(dc, fontscale)
            if not r: iteration=-1 # font can't be made this small
            _,entryheight=dc.GetTextExtent("I")
            firstrowheight=max(timeheight, entryheight)

            # Now draw each item
            lastap=""
            for h,m,desc in self.entries:
                x=0
                self.attr.setfortime(dc, fontscale)
                # bounding
                x+=boundingspace # we don't draw anything yet
                timey=y
                if timeheight<firstrowheight:
                    timey+=(firstrowheight-timeheight)/2
                text=""
                
                if self.attr.ismiltime():
                    ap=""
                else:
                    ap="a"
                    if h>=12: ap="p"
                    h%=12
                    if h==0: h=12
                    if ap==lastap:
                        ap=""
                    else:
                        lastap=ap
                if h<10: text+=" "
                
                text+="%d:%02d%s" % (h,m,ap)
                dc.DrawText(text, x, timey)
                x+=timespace
                if not self.attr.ismiltime: x+=ampm
                
                self.attr.setforentry(dc, fontscale)
                ey=y
                if entryheight<firstrowheight:
                    ey+=(firstrowheight-entryheight)/2
                dc.DrawText(desc, x, ey)
                # that row is dealt with!
                y+=firstrowheight
            if iteration==1 and fontscale!=1:
                # came from cache
                break
            if iteration==-1:
                # update cache
                thefontscalecache.set(self.height-entrystart, self.attr, len(self.entries), fontscale)
                break # reached limit of font scaling
            if iteration<10 and y>self.height:
                dc.Clear()
                # how much too big were we?
                fontscale=fontscale*float(self.height-entrystart)/(y-entrystart)
                # print iteration, y, self.height, fontscale
            else:
                thefontscalecache.set(self.height-entrystart, self.attr, len(self.entries), fontscale)
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
        self.settextcolour(wxNamedColour("BLACK"))
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
            else:
                 # it doesn't fit
                 if row==0:
                     # top one shows start of text
                     dc.DrawRotatedText(month, w/2-th/2, y + h -5, 90)
                 else:
                     # show end of text at bottom
                     dc.DrawRotatedText(month, w/2-th/2, y + 5 + tw, 90)

            # Loop around
            row=endrow+1


class Calendar(wxPanel):
    # All the horrible date code is an excellent case for metric time!
    ID_UP=1
    ID_DOWN=2
    ID_YEARBUTTON=3

    attrevenmonth=CalendarCellAttributes()
    attroddmonth=CalendarCellAttributes()
    attroddmonth.cellbackground=wxTheBrushList.FindOrCreateBrush( wxColour(255, 255, 230), wxSOLID)
    attrselectedcell=CalendarCellAttributes()
    attrselectedcell.cellbackground=wxTheBrushList.FindOrCreateBrush( wxColour(240,240,240), wxSOLID)
    attrselectedcell.labelfont=wxFont(17, wxSWISS, wxNORMAL, wxBOLD )
    attrselectedcell.labelforeground=wxNamedColour("BLACK")
    
    def __init__(self, parent, rows=5, id=-1):
        wxPanel.__init__(self, parent, id, style=wxNO_FULL_REPAINT_ON_RESIZE|wxWANTS_CHARS)
        sizer=RowColSizer()
        self.upbutt=wxBitmapButton(self, self.ID_UP, getupbitmapBitmap())
        sizer.Add(self.upbutt, flag=wxEXPAND, row=0,col=0, colspan=8)
        self.year=wxButton(self, self.ID_YEARBUTTON, "2003")
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
        self.downbutt=wxBitmapButton(self, self.ID_DOWN, getdownbitmapBitmap())
        sizer.Add(self.downbutt, flag=wxEXPAND, row=2+rows, col=0, colspan=8)
        self.label=CalendarLabel(self, map(lambda x: x[0], self.rows))
        sizer.Add(self.label, flag=wxEXPAND, row=2, col=0, rowspan=self.numrows)
        self.SetSizer(sizer)
        self.SetAutoLayout(True)

        self.popupcalendar=PopupCalendar(self, self)

        EVT_BUTTON(self, self.ID_UP, self.OnScrollUp)
        EVT_BUTTON(self, self.ID_DOWN, self.OnScrollDown)
        EVT_BUTTON(self, self.ID_YEARBUTTON, self.OnYearButton)
        EVT_ERASE_BACKGROUND(self, self.OnEraseBackground)
        # grab key down from all children
        map(lambda child: EVT_KEY_DOWN(child, self.OnKeyDown), self.GetChildren())

        self.selectedcell=(-1,-1)
        self.selecteddate=(-1,-1,-1)

        self.showday(*time.localtime()[:3]+(self.showrow,))
        self.setday(*time.localtime()[:3])

    def OnKeyDown(self, event):
        key=event.GetKeyCode()
        if key==WXK_NEXT:
           self.scrollby( (self.numrows-1)*7)
        elif key==WXK_PRIOR:
           self.scrollby( (self.numrows-1)*-7)
        elif key==WXK_LEFT:
           self.setday(*normalizedate( self.selecteddate[0], self.selecteddate[1], self.selecteddate[2]-1) )
        elif key==WXK_RIGHT:
           self.setday(*normalizedate( self.selecteddate[0], self.selecteddate[1], self.selecteddate[2]+1) )
        elif key==WXK_UP:
           self.setday(*normalizedate( self.selecteddate[0], self.selecteddate[1], self.selecteddate[2]-7) )
        elif key==WXK_DOWN:
           self.setday(*normalizedate( self.selecteddate[0], self.selecteddate[1], self.selecteddate[2]+7) )
        elif key==WXK_HOME:  # back a month
           self.setday(*normalizedate( self.selecteddate[0], self.selecteddate[1]-1, self.selecteddate[2]) )
        elif key==WXK_END: # forward a month
           self.setday(*normalizedate( self.selecteddate[0], self.selecteddate[1]+1, self.selecteddate[2]) )
        else:
           event.Skip()  # control can have it

    def OnYearButton(self, event):
        self.popupcalendar.Popup( * (self.selecteddate + (event,)) )

    def OnEraseBackground(self, _):
        pass

    def makerow(self, sizer, row):
        res=[]
        sizer.AddGrowableRow(row)
        for i in range(0,7):
            res.append( CalendarCell(self, -1) )
            sizer.Add( res[-1], flag=wxEXPAND, row=row, col=i+1)
        return res

    def scrollby(self, amount):
        assert abs(amount)%7==0
        for row in range(0, self.numrows):
                y,m,d=self.rows[row][0].getdate()
                y,m,d=normalizedate(y,m,d+amount)
                self.updaterow(row, y,m,d)
        self.setselection(*self.selecteddate)
        self.label.changenotify()
        self.ensureallpainted()

    def ensureallpainted(self):
        # doesn't return until cells have been painted
        self.Update()

    def OnScrollDown(self, _=None):
        # user has pressed scroll down button
        self.scrollby(7)
        
    def OnScrollUp(self, _=None):
       # user has pressed scroll up button
       self.scrollby(-7)

    def setday(self, year, month, day):
       # makes specified day be shown and selected
       self.showday(year, month, day)
       self.setselection(year, month, day)
       
    def showday(self, year, month, day, rowtoshow=-1):
       # ensures specified day is onscreen
       # if rowtoshow is >=0 then it will be forced to appear in that row
       # check first cell
       y,m,d=self.rows[0][0].year, self.rows[0][0].month, self.rows[0][0].day
       if rowtoshow==-1:
          if year<y or (year<=y and month<m) or (year<=y and month<=m and day<d):
             rowtoshow=0
       # check last cell   
       y,m,d=self.rows[-1][-1].year, self.rows[-1][-1].month, self.rows[-1][-1].day
       if rowtoshow==-1:
          if year>y or (year>=y and month>m) or (year>=y and month>=m and day>d):
             rowtoshow=self.numrows-1
       if rowtoshow!=-1:
          d=calendar.weekday(year, month, day)
          d=(d+1)%7
          
          d=day-d # go back to begining of week
          d-=7*rowtoshow # then begining of screen
          y,m,d=normalizedate(year, month, d)
          for row in range(0,self.numrows):
             self.updaterow(row, *normalizedate(y, m, d+7*row))
          self.label.changenotify()
          self.ensureallpainted()

    def setselection(self, year, month, day):
       self.selecteddate=(year,month,day)
       d=calendar.weekday(year, month, day)
       d=(d+1)%7
       for row in range(0, self.numrows):
          cell=self.rows[row][d]
          if cell.year==year and cell.month==month and cell.day==day:
             self._unselect()
             self.rows[row][d].setattr(self.attrselectedcell)
             self.selectedcell=(row,d)
             self.ensureallpainted()
             return

    def _unselect(self):
       if self.selectedcell!=(-1,-1):
          self.updatecell(*self.selectedcell)
          self.selectedcell=(-1,-1)

    def updatecell(self, row, column, y=-1, m=-1, d=-1):
       if y!=-1:
          self.rows[row][column].setdate(y,m,d)
       if self.rows[row][column].month%2:
          self.rows[row][column].setattr(self.attroddmonth)
       else:
          self.rows[row][column].setattr(self.attrevenmonth)
       if y!=-1 and row==0 and column==0:
          self.year.SetLabel(`y`)
        # ::TODO:: get events for this day if y,m,d !=-1

    def updaterow(self, row, y, m, d):
        daysinmonth=monthrange(y, m)
        for c in range(0,7):
            self.updatecell(row, c, y, m, d)
            if d==daysinmonth:
                d=1
                m+=1
                if m==13:
                    m=1
                    y+=1
                daysinmonth=monthrange(y, m)
            else:
                d+=1


class PopupCalendar(wxDialog):
    def __init__(self, parent, calendar, style=wxSIMPLE_BORDER):
        wxDialog.__init__(self, parent, -1, '', style=wxSTAY_ON_TOP)
        self.calendar=calendar
        self.control=wxCalendarCtrl(self, 1, style=wxCAL_SUNDAY_FIRST, pos=(0,0))
        sz=self.control.GetBestSize()
        self.SetSize(sz)
        EVT_CALENDAR(self, self.control.GetId(), self.OnCalSelected)

    def Popup(self, year, month, day, event):
        d=wxDateTimeFromDMY(day, month, year)
        self.control.SetDate(d)
        btn=event.GetEventObject()
        pos=btn.ClientToScreen( (0,0) )
        sz=btn.GetSize()
        self.Move( (pos[0], pos[1]+sz.height ) )
        self.ShowModal()

    def OnCalSelected(self, evt):
        dt=evt.GetDate()
        self.calendar.setday(dt.GetYear(), dt.GetMonth()+1, dt.GetDay())
        self.calendar.ensureallpainted()
        self.EndModal(1)
        

_monthranges=[0, 31, -1, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

def monthrange(year, month):
    if month==2:
        return calendar.monthrange(year, month)[1]
    return _monthranges[month]

def normalizedate(year, month, day):
    # metric system please .....
    while day<1 or month<1 or month>12 or (day>28 and day>monthrange(year, month)):
        if day<1:
            month-=1
            if month<1:
                month=12
                year-=1
            num=monthrange(year, month)
            day=num+day
            continue
        if day>28 and day>monthrange(year, month):
            num=calendar.monthrange(year, month)[1]
            month+=1
            if month>12:
                month=1
                year+=1
            day=day-num
            continue    
        if month<1:
            year-=1
            month=month+12
            continue
        if month>12:
            year+=1
            month-=12
            continue
        assert False, "can't get here"

    return year, month, day
            
# Up and down bitmap icons

def getupbitmapData():
    return \
'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00 \x00\x00\x00\x10\x08\x06\
\x00\x00\x00w\x00}Y\x00\x00\x00\x04sBIT\x08\x08\x08\x08|\x08d\x88\x00\x00\
\x00}IDATx\x9c\xbd\xd5K\x0e\xc0 \x08\x04P\xe0\x04\xdc\xff\x94\xdc\xa0\xdd6\
\xad\xca\xf0)n\\\xa83/1FVU\xca\x0e3\xbbT\x95\xd3\x01D$\x95\xf2\xe7<\nx\x97V\
\x10a\xc0\xae,\x8b\x08\x01\xbc\x92\x0c\x02\x06\xa0\xe1Q\x04\x04\x88\x86F\xf6\
\xbb\x80\xec\xdd\xa2\xe7\x8e\x80\xea\x13C\xceo\x01\xd5r4g\t\xe8*G\xf2>\x80\
\xeer/W\x90M\x7f"\xe4\xb48\x81\x90\xc9\xf2\x15\x82+\xdfq\xc7\xb8\x01;]o#\xdc\
D \x03\x00\x00\x00\x00IEND\xaeB`\x82' 

def getupbitmapBitmap():
    return wxBitmapFromImage(getupbitmapImage())

def getupbitmapImage():
    stream = cStringIO.StringIO(getupbitmapData())
    return wxImageFromStream(stream)

def getdownbitmapData():
    return \
'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00 \x00\x00\x00\x10\x08\x06\
\x00\x00\x00w\x00}Y\x00\x00\x00\x04sBIT\x08\x08\x08\x08|\x08d\x88\x00\x00\
\x00\x80IDATx\x9c\xc5\xd3\xd1\r\x80 \x0c\x04\xd0B\x1c\xe0\xf6\x9f\xb2\x1b\
\xe8\x97\t\x91R\xda\x02\x95/!r\xf7bj\x01@\x7f\xae\xeb}`\xe6;\xbb\x1c@\xa9\
\xed&\xbb\x9c\x88\xa8J\x87Y\xe5\x1d \x03\xf1\xcd\xef\x00\'\x11R\xae\x088\x81\
\x18\xe5\r\x01;\x11Z\x8e\n\xd8\x81\x98\xdd\x9f\x02V\x10\x96{&@\x04a}\xdf\x0c\
\xf0\x84z\xb0.\x80%\xdc\xfb\xa5\xdc\x00\xad$2+!\x80T\x16\x1d\xd40\xa0-]\xf9U\
\x1f\xf8\xca\t\xael-\x16\x86\x00\x00\x00\x00IEND\xaeB`\x82' 

def getdownbitmapBitmap():
    return wxBitmapFromImage(getdownbitmapImage())

def getdownbitmapImage():
    stream = cStringIO.StringIO(getdownbitmapData())
    return wxImageFromStream(stream)


 


if __name__=="__main__":
    class MainWindow(wxFrame):
        def __init__(self, parent, id, title):
            wxFrame.__init__(self, parent, id, title, size=(800,600),
                             style=wxDEFAULT_FRAME_STYLE|wxNO_FULL_REPAINT_ON_RESIZE)
            #self.control=CalendarCell(self, 1) # test just the cell
            self.control=Calendar(self)
            self.Show(True)
    
    app=wxPySimpleApp()
    frame=MainWindow(None, -1, "Calendar Test")
    if 0:
        import profile
        profile.run("app.MainLoop()", "fooprof")
    else:
        app.MainLoop()

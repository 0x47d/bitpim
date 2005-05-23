#!/usr/bin/env python
### BITPIM
###
### Copyright (C) 2003-2004 Roger Binns <rogerb@rogerbinns.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""A hex editor widget"""

import string
import struct

import wx

class HexEditor(wx.ScrolledWindow):

    _addr_range=xrange(8)
    _hex_range_start=10
    _hex_range_start2=33
    _hex_range=xrange(_hex_range_start, 58)
    _ascii_range_start=60
    _ascii_range=xrange(60, 76)

    def __init__(self, parent, id=-1, style=wx.WANTS_CHARS,
                 _set_pos=None, _set_sel=None, _set_val=None):
        wx.ScrolledWindow.__init__(self, parent, id, style=style)
        self.parent=parent
        self.data=""
        self.title=""
        self.buffer=None
        self.hasfocus=False
        self.dragging=False
        self.current_ofs=None
        self._module=None
        # ways of displaying status
        self.set_pos=_set_pos or self._set_pos
        self.set_val=_set_val or self._set_val
        self.set_sel=_set_sel or self._set_sel
        # some GUI setup
        self.SetBackgroundColour("WHITE")
        self.SetCursor(wx.StockCursor(wx.CURSOR_IBEAM))
        self.sethighlight(wx.NamedColour("BLACK"), wx.NamedColour("YELLOW"))
        self.setnormal(wx.NamedColour("BLACK"), wx.NamedColour("WHITE"))
        self.setfont(wx.TheFontList.FindOrCreateFont(10, wx.MODERN, wx.NORMAL, wx.NORMAL))
        self.OnSize(None)
        self.highlightrange(None, None)
        # other stuff
        self._create_context_menu()
        self._map_events()

    def _map_events(self):
        wx.EVT_SCROLLWIN(self, self.OnScrollWin)
        wx.EVT_PAINT(self, self.OnPaint)
        wx.EVT_SIZE(self, self.OnSize)
        wx.EVT_ERASE_BACKGROUND(self, self.OnEraseBackground)
        wx.EVT_SET_FOCUS(self, self.OnGainFocus)
        wx.EVT_KILL_FOCUS(self, self.OnLoseFocus)
        wx.EVT_LEFT_DOWN(self, self.OnStartSelection)
        wx.EVT_LEFT_UP(self, self.OnEndSelection)
        wx.EVT_MOTION(self, self.OnMakeSelection)
        wx.EVT_RIGHT_UP(self, self.OnRightClick)

    def _create_context_menu(self):
        file_menu=wx.Menu()
        id=wx.NewId()
        file_menu.Append(id, 'Load')
        wx.EVT_MENU(self, id, self.OnLoadFile)
        id=wx.NewId()
        file_menu.Append(id, 'Save As')
        wx.EVT_MENU(self, id, self.OnSaveAs)
        id=wx.NewId()
        file_menu.Append(id, 'Save Selection As')
        wx.EVT_MENU(self, id, self.OnSaveSelection)
        id=wx.NewId()
        file_menu.Append(id, 'Save Hexdump As')
        wx.EVT_MENU(self, id, self.OnSaveHexdumpAs)
        set_sel_menu=wx.Menu()
        id=wx.NewId()
        set_sel_menu.Append(id, 'Start')
        wx.EVT_MENU(self, id, self.OnStartSelMenu)
        id=wx.NewId()
        set_sel_menu.Append(id, 'End')
        wx.EVT_MENU(self, id, self.OnEndSelMenu)
        self._bgmenu=wx.Menu()
        self._bgmenu.AppendMenu(wx.NewId(), 'File', file_menu)
        self._bgmenu.AppendMenu(wx.NewId(), 'Set Selection', set_sel_menu)
        id=wx.NewId()
        self._bgmenu.Append(id, 'Value')
        wx.EVT_MENU(self, id, self.OnViewValue)
        id=wx.NewId()
        self._bgmenu.Append(id, 'Import Python Module')
        wx.EVT_MENU(self, id, self.OnImportModule)
        self._reload_menu_id=wx.NewId()
        self._bgmenu.Append(self._reload_menu_id, 'Reload Python Module')
        wx.EVT_MENU(self, self._reload_menu_id, self.OnReloadModule)
        self._apply_menu_id=wx.NewId()
        self._bgmenu.Append(self._apply_menu_id, 'Apply Python Func')
        wx.EVT_MENU(self, self._apply_menu_id, self.OnApplyFunc)

    def SetData(self, data):
        self.data=data
        self.needsupdate=True
        self.updatescrollbars()
        self.Refresh()

    def SetTitle(self, title):
        self.title=title

    def SetStatusDisplay(self, _set_pos=None, _set_sel=None, _set_val=None):
        self.set_pos=_set_pos or self._set_pos
        self.set_sel=_set_sel or self._set_sel
        self.set_val=_set_val or self._set_val

    def OnEraseBackground(self, _):
        pass
    def _set_pos(self, pos):
        pass
    def _set_sel(self, sel_start, sel_end):
        pass
    def _set_val(self, v):
        pass

    def _to_char_line(self, x, y):
        """Convert an x,y point to (char, line)
        """
        return x/self.charwidth, y/self.charheight
    def _to_xy(self, char, line):
        return char*self.charwidth, line*self.charheight
    def _to_buffer_offset(self, char, line):
        if char in self._hex_range:
            if char>self._hex_range_start2:
                char-=1
            if ((char-self._hex_range_start)%3)<2:
                return line*16+(char-self._hex_range_start)/3
        elif char in self._ascii_range:
            return line*16+char-self._ascii_range_start
    def _set_and_move(self, evt):
        c,l=self._to_char_line(evt.GetX(), evt.GetY())
        self.GetCaret().Move(self._to_xy(c, l))
        x0, y0=self.GetViewStart()
        char_x=c+x0
        line_y=l+y0
        return self._to_buffer_offset(char_x, line_y)
    _value_formats=(
        ('unsigned char', 'B', struct.calcsize('B')),
        ('signed char', 'b', struct.calcsize('b')),
        ('LE unsigned short', '<H', struct.calcsize('<H')),
        ('LE signed short', '<h', struct.calcsize('<h')),
        ('BE unsigned short', '>H', struct.calcsize('>H')),
        ('BE signed short', '>h', struct.calcsize('>h')),
        ('LE unsigned int', '<I', struct.calcsize('<I')),
        ('LE signed int', '<i', struct.calcsize('<i')),
        ('BE unsigned int', '>I', struct.calcsize('>I')),
        ('BE signed int', '>i', struct.calcsize('>i')),
        )
    def _gen_values(self, _data, _ofs):
        """ Generate the values of various number formats starting at the
        current offset.
        """
        n=_data[_ofs:]
        len_n=len(n)
        s='0x%X=%d'%(_ofs, _ofs)
        res=[{ 'Data Offset': s}, {'':''} ]
        for i,e in enumerate(self._value_formats):
            if len_n<e[2]:
                continue
            v=struct.unpack(e[1], n[:e[2]])[0]
            if i%2:
                s='%d'%v
            else:
                fmt='0x%0'+str(e[2]*2)+'X=%d'
                s=fmt%(v,v)
            res.append({ e[0]: s })
        return res

    def _display_result(self, result):
        """ Display the results from applying a Python routine over the data
        """
        s=''
        for d in result:
            for k,e in d.items():
                s+=k+':\t'+e+'\n'
        dlg=wx.MessageDialog(self, s, 'Results', style=wx.OK)
        dlg.ShowModal()
        dlg.Destroy()

    def OnLoadFile(self, _):
        dlg=wx.FileDialog(self, 'Select a file to load',
                          style=wx.OPEN|wx.FILE_MUST_EXIST)
        if dlg.ShowModal()==wx.ID_OK:
            self.SetData(file(dlg.GetPath(), 'rb').read())
        dlg.Destroy()
    def OnSaveAs(self, _):
        dlg=wx.FileDialog(self, 'Select a file to save',
                          style=wx.SAVE|wx.OVERWRITE_PROMPT)
        if dlg.ShowModal()==wx.ID_OK:
            file(dlg.GetPath(), 'wb').write(self.data)
        dlg.Destroy()
    def hexdumpdata(self):
        res=""
        l=len(self.data)
        if self.title:
            res += self.title+": "+`l`+" bytes\n"
        res += "<#! !#>\n"
        pos=0
        while pos<l:
            text="%08X "%(pos)
            line=self.data[pos:pos+16]
            for i in range(len(line)):
                text+="%02X "%(ord(line[i]))
            text+="   "*(16-len(line))
            text+="    "
            for i in range(len(line)):
                c=line[i]
                if (ord(c)>=32 and string.printable.find(c)>=0):
                    text+=c
                else:
                    text+='.'
            res+=text+"\n"
            pos+=16
        return res
        
    def OnSaveHexdumpAs(self, _):
        dlg=wx.FileDialog(self, 'Select a file to save',
                          style=wx.SAVE|wx.OVERWRITE_PROMPT)
        if dlg.ShowModal()==wx.ID_OK:
            file(dlg.GetPath(), 'wb').write(self.hexdumpdata())
        dlg.Destroy()
    def OnSaveSelection(self, _):
        if self.highlightstart is None or self.highlightstart==-1 or \
           self.highlightend is None or self.highlightend==-1:
            # no selection
            return
        dlg=wx.FileDialog(self, 'Select a file to save',
                          style=wx.SAVE|wx.OVERWRITE_PROMPT)
        if dlg.ShowModal()==wx.ID_OK:
            file(dlg.GetPath(), 'wb').write(
                self.data[self.highlightstart:self.highlightend])
        dlg.Destroy()

    def OnReloadModule(self, _):
        try:
            reload(self._module)
        except:
            self._module=None
            w=wx.MessageDialog(self, 'Failed to reload module',
                               'Reload Module Error',
                               style=wx.OK|wx.ICON_ERROR)
            w.ShowModal()
            w.Destroy()
    def OnApplyFunc(self, _):
        choices=[x for x in dir(self._module) \
                 if callable(getattr(self._module, x))]
        dlg=wx.SingleChoiceDialog(self, 'Select a function to apply:',
                            'Apply Python Func',
                            choices)
        if dlg.ShowModal()==wx.ID_OK:
            try:
                res=getattr(self._module, dlg.GetStringSelection())(
                    self, self.data, self.current_ofs)
                self._display_result(res)
            except:
                raise
                w=wx.MessageDialog(self, 'Apply Func raised an exception',
                                   'Apply Func Error',
                                   style=wx.OK|wx.ICON_ERROR)
                w.ShowModal()
                w.Destroy()
        dlg.Destroy()
    def OnImportModule(self, _):
        dlg=wx.TextEntryDialog(self, 'Enter the name of a Python Module:',
                               'Module Import')
        if dlg.ShowModal()==wx.ID_OK:
            try:
                self._module=__import__(dlg.GetValue())
            except ImportError:
                self._module=None
                w=wx.MessageDialog(self, 'Failed to import module: '+dlg.GetValue(),
                                 'Module Import Error',
                                 style=wx.OK|wx.ICON_ERROR)
                w.ShowModal()
                w.Destroy()
        dlg.Destroy()

    def OnStartSelMenu(self, evt):
        ofs=self.current_ofs
        if ofs is not None:
            self.highlightstart=ofs
            self.needsupdate=True
            self.Refresh()
        self.set_sel(self.highlightstart, self.highlightend)
            
    def OnEndSelMenu(self, _):
        ofs=self.current_ofs
        if ofs is not None:
            self.highlightend=ofs+1
            self.needsupdate=True
            self.Refresh()
        self.set_sel(self.highlightstart, self.highlightend)

    def OnViewValue(self, _):
        ofs=self.current_ofs
        if ofs is not None:
            self._display_result(self._gen_values(self.data, ofs))

    def OnStartSelection(self, evt):
        self.highlightstart=self.highlightend=None
        ofs=self._set_and_move(evt)
        if ofs is not None:
            self.highlightstart=ofs
            self.dragging=True
            self.set_val(self.data[ofs:])
        else:
            self.set_val(None)
        self.needsupdate=True
        self.Refresh()
        self.set_pos(ofs)
        self.set_sel(self.highlightstart, self.highlightend)
        
    def OnMakeSelection(self, evt):
        if not self.dragging:
            return
        ofs=self._set_and_move(evt)
        if ofs is not None:
            self.highlightend=ofs+1
            self.needsupdate=True
            self.Refresh()
        self.set_pos(ofs)
        self.set_sel(self.highlightstart, self.highlightend)
    def OnEndSelection(self, evt):
        self.dragging=False
        ofs=self._set_and_move(evt)
        self.set_pos(ofs)
        self.set_sel(self.highlightstart, self.highlightend)

    def OnRightClick(self, evt):
        self.current_ofs=self._set_and_move(evt)
        if self.current_ofs is None:
            self.set_val(None)
        else:
            self.set_val(self.data[self.current_ofs:])
        self.set_pos(self.current_ofs)
        self._bgmenu.Enable(self._apply_menu_id, self._module is not None)
        self._bgmenu.Enable(self._reload_menu_id, self._module is not None)
        self.PopupMenu(self._bgmenu, evt.GetPosition())

    def OnSize(self, evt):
        # uncomment these lines to prevent going wider than is needed
        # if self.width>self.widthinchars*self.charwidth:
        #    self.SetClientSize( (self.widthinchars*self.charwidth, self.height) )
        if evt is None:
            self.width=(self.widthinchars+3)*self.charwidth
            self.height=self.charheight*20
            self.SetClientSize((self.width, self.height))
            self.SetCaret(wx.Caret(self, (self.charwidth, self.charheight)))
            self.GetCaret().Show(True)
        else:
            self.width,self.height=self.GetClientSizeTuple()
        self.needsupdate=True

    def OnGainFocus(self,_):
        self.hasfocus=True
        self.needsupdate=True
        self.Refresh()

    def OnLoseFocus(self,_):
        self.hasfocus=False
        self.needsupdate=True
        self.Refresh()

    def highlightrange(self, start, end):
        self.needsupdate=True
        self.highlightstart=start
        self.highlightend=end
        self.Refresh()
        self.set_pos(None)
        self.set_sel(self.highlightstart, self.highlightend)
        self.set_val(None)

    def _ishighlighted(self, pos):
        return pos>=self.highlightstart and pos<self.highlightend

    def sethighlight(self, foreground, background):
        self.highlight=foreground,background

    def setnormal(self, foreground, background):
        self.normal=foreground,background

    def setfont(self, font):
        dc=wx.ClientDC(self)
        dc.SetFont(font)
        self.charwidth, self.charheight=dc.GetTextExtent("M")
        self.font=font
        self.updatescrollbars()

    def updatescrollbars(self):
        # how many lines are we?
        lines=len(self.data)/16
        if lines==0 or len(self.data)%16:
            lines+=1
        self.datalines=lines
##        lines+=1 # status line
        # fixed width
        self.widthinchars=8+2+3*16+1+2+16
        self.SetScrollbars(self.charwidth, self.charheight, self.widthinchars, lines, self.GetViewStart()[0], self.GetViewStart()[1])

    def _setnormal(self,dc):
        dc.SetTextForeground(self.normal[0])
        dc.SetTextBackground(self.normal[1])

    def _sethighlight(self,dc):
        dc.SetTextForeground(self.highlight[0])
        dc.SetTextBackground(self.highlight[1])    

    def _setstatus(self,dc):
        dc.SetTextForeground(self.normal[1])
        dc.SetTextBackground(self.normal[0])
        dc.SetBrush(wx.BLACK_BRUSH)
        

    def OnDraw(self, dc):
        xd,yd=self.GetViewStart()
        st=0  # 0=normal, 1=highlight
        dc.BeginDrawing()
        dc.SetBackgroundMode(wx.SOLID)
        dc.SetFont(self.font)
        for line in range(yd, min(self.datalines, yd+self.height/self.charheight+1)):
            # address
            self._setnormal(dc)
            st=0
            dc.DrawText("%08X" % (line*16), 0, line*self.charheight)
            # bytes
            for i in range(16):
                pos=line*16+i
                if pos>=len(self.data):
                    break
                hl=self._ishighlighted(pos)
                if hl!=st:
                    if hl:
                        st=1
                        self._sethighlight(dc)
                    else:
                        st=0
                        self._setnormal(dc)
                if hl:
                    space=""
                    if i<15:
                        if self._ishighlighted(pos+1):
                            space=" "
                            if i==7:
                                space="  "
                else:
                    space=""
                c=self.data[pos]
                dc.DrawText("%02X%s" % (ord(c),space), (10+(3*i)+(i>=8))*self.charwidth, line*self.charheight)
                if not (ord(c)>=32 and string.printable.find(c)>=0):
                    c='.'
                dc.DrawText(c, (10+(3*16)+2+i)*self.charwidth, line*self.charheight)

##        if self.hasfocus:
##            self._setstatus(dc)
##            w,h=self.GetClientSizeTuple()
##            dc.DrawRectangle(0,h-self.charheight+yd*self.charheight,self.widthinchars*self.charwidth,self.charheight)
##            dc.DrawText("A test of stuff "+`yd`, 0, h-self.charheight+yd*self.charheight)
                
        dc.EndDrawing()

    def updatebuffer(self):
        if self.buffer is None or \
           self.buffer.GetWidth()!=self.width or \
           self.buffer.GetHeight()!=self.height:
            if self.buffer is not None:
                del self.buffer
            self.buffer=wx.EmptyBitmap(self.width, self.height)

        mdc=wx.MemoryDC()
        mdc.SelectObject(self.buffer)
        mdc.SetBackground(wx.TheBrushList.FindOrCreateBrush(self.GetBackgroundColour(), wx.SOLID))
        mdc.Clear()
        self.PrepareDC(mdc)
        self.OnDraw(mdc)
        mdc.SelectObject(wx.NullBitmap)
        del mdc

    def OnPaint(self, event):
        if self.needsupdate:
            self.needsupdate=False
            self.updatebuffer()
        dc=wx.PaintDC(self)
        dc.BeginDrawing()
        dc.DrawBitmap(self.buffer, 0, 0, False)
        dc.EndDrawing()

    def OnScrollWin(self, event):
        self.needsupdate=True
        self.Refresh() # clear whole widget
        event.Skip() # default event handlers now do scrolling etc

class HexEditorDialog(wx.Dialog):
    _pane_widths=[-2, -3, -4]
    _pos_pane_index=0
    _sel_pane_index=1
    _val_pane_index=2
    def __init__(self, parent, data='', title='BitPim Hex Editor', helpd_id=-1):
        super(HexEditorDialog, self).__init__(parent, -1, title,
                                              size=(500, 500),
                                              style=wx.DEFAULT_DIALOG_STYLE|\
                                              wx.RESIZE_BORDER)
        self._status_bar=wx.StatusBar(self, -1)
        self._status_bar.SetFieldsCount(len(self._pane_widths))
        self._status_bar.SetStatusWidths(self._pane_widths)
        vbs=wx.BoxSizer(wx.VERTICAL)
        self._hex_editor=HexEditor(self, _set_pos=self.set_pos,
                                   _set_val=self.set_val,
                                   _set_sel=self.set_sel)
        self._hex_editor.SetData(data)
        self._hex_editor.SetTitle(title)
        vbs.Add(self._hex_editor, 1, wx.EXPAND|wx.ALL, 5)
        vbs.Add(wx.StaticLine(self), 0, wx.EXPAND|wx.ALL, 5)
        ok_btn=wx.Button(self, wx.ID_OK, 'OK')
        vbs.Add(ok_btn, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
        vbs.Add(self._status_bar, 0, wx.EXPAND|wx.ALL, 0)
        self.SetSizer(vbs)
        self.SetAutoLayout(True)
        vbs.Fit(self)
    def set_pos(self, pos):
        """Display the current buffer offset in the format of
        Pos: 0x12=18
        """
        if pos is None:
            s=''
        else:
            s='Pos: 0x%X=%d'%(pos, pos)
        self._status_bar.SetStatusText(s, self._pos_pane_index)
    def set_sel(self, sel_start, sel_end):
        if sel_start is None or sel_start==-1 or\
           sel_end is None or sel_end ==-1:
            s=''
        else:
            sel_len=sel_end-sel_start
            sel_end-=1
            s='Sel: 0x%X=%d to 0x%X=%d (0x%X=%d bytes)'%(
                sel_start, sel_start, sel_end, sel_end,
                sel_len, sel_len)
        self._status_bar.SetStatusText(s, self._sel_pane_index)
    def set_val(self, v):
        if v:
            # char
            s='Val: 0x%02X=%d'%(ord(v[0]), ord(v[0]))
            if len(v)>1:
                # short
                u_s=struct.unpack('<H', v[:struct.calcsize('<H')])[0]
                s+=' 0x%04X=%d'%(u_s,  u_s)
            if len(v)>3:
                # int/long
                u_i=struct.unpack('<I', v[:struct.calcsize('<I')])[0]
                s+=' 0x%08X=%d'%(u_i, u_i)
        else:
            s=''
        self._status_bar.SetStatusText(s, self._val_pane_index)

    def set(self, data):
        self._hex_editor.SetData(data)

        
if __name__=='__main__':
    import sys

    if len(sys.argv)!=2:
        print 'Usage:',sys.argv[0],'<File Name>'
        sys.exit(1)
    app=wx.PySimpleApp()
    dlg=HexEditorDialog(None, file(sys.argv[1], 'rb').read(),
                        sys.argv[1])
    if True:
        dlg.ShowModal()
    else:
        import hotshot
        f=hotshot.Profile("hexeprof",1)
        f.runcall(dlg.ShowModal)
        f.close()
        import hotshot.stats
        stats=hotshot.stats.load("hexeprof")
        stats.strip_dirs()
        # stats.sort_stats("cumulative")
        stats.sort_stats("time", "calls")
        stats.print_stats(30)

    dlg.Destroy()
    sys.exit(0)

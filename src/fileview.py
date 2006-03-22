#!/usr/bin/env python

### BITPIM
###
### Copyright (C) 2003-2006 Roger Binns <rogerb@rogerbinns.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id: guiwidgets.py 2851 2006-03-03 05:53:55Z djpham $


###
### File viewer
###

import os
import phone_media_codec
import wx
import guihelper
import aggregatedisplay
import common
import widgets

def DrawTextWithLimit(dc, x, y, text, widthavailable, guardspace, term="..."):
    """Draws text and if it will overflow the width available, truncates and  puts ... at the end

    @param x: start position for text
    @param y: start position for text
    @param text: the string to draw
    @param widthavailable: the total amount of space available
    @param guardspace: if the text is longer than widthavailable then this amount of space is
             reclaimed from the right handside and term put there instead.  Consequently
             this value should be at least the width of term
    @param term: the string that is placed in the guardspace if it gets truncated.  Make sure guardspace
             is at least the width of this string!
    @returns: The extent of the text that was drawn in the end as a tuple of (width, height)
    """
    w,h=dc.GetTextExtent(text)
    if w<widthavailable:
        dc.DrawText(text,x,y)
        return w,h
    extents=dc.GetPartialTextExtents(text)
    limit=widthavailable-guardspace
    # find out how many chars in we have to go before hitting limit
    for i,offset in enumerate(extents):
        if offset>limit:
            break
    # back off 1 in case the new text's a tad long
    if i:
        i-=1
    text=text[:i]+term
    w,h=dc.GetTextExtent(text)
    assert w<=widthavailable
    dc.DrawText(text, x, y)
    return w,h

media_codec=phone_media_codec.codec_name
class MyFileDropTarget(wx.FileDropTarget):
    def __init__(self, target, drag_over=False, enter_leave=False):
        wx.FileDropTarget.__init__(self)
        self.target=target
        self.drag_over=drag_over
        self.enter_leave=enter_leave
        
    def OnDropFiles(self, x, y, filenames):
        return self.target.OnDropFiles(x,y,filenames)

    def OnDragOver(self, x, y, d):
        if self.drag_over:
            return self.target.OnDragOver(x,y,d)
        return wx.FileDropTarget.base_OnDragOver(self, x, y, d)

    def OnEnter(self, x, y, d):
        if self.enter_leave:
            return self.target.OnEnter(x,y,d)
        return wx.FileDropTarget.base_OnEnter(self, x, y, d)

    def OnLeave(self):
        if self.enter_leave:
            return self.target.OnLeave()
        return wx.FileDropTarget.base_OnLeave(self)

class FileView(wx.Panel, widgets.BitPimWidget):

    # Various DC objects used for drawing the items.  We have to calculate them in the constructor as
    # the app object hasn't been constructed when this file is imported.
    item_selection_brush=None
    item_selection_pen=None
    item_line_font=None
    item_term="..."
    item_guardspace=None
    # Files we should ignore
    skiplist= ( 'desktop.ini', 'thumbs.db', 'zbthumbnail.info' )

    # how much data do we want in call to getdata
    NONE=0
    SELECTED=1
    ALL=2

    # maximum length of a filename
    maxlen=-1  # set via phone profile
    # acceptable characters in a filename
    filenamechars=None # set via phone profile
    # lisf of available origins that can be set
    origin_list=()

    def __init__(self, mainwindow, parent, watermark=None):
        wx.Panel.__init__(self,parent,style=wx.CLIP_CHILDREN)

        if not hasattr(self, "organizemenu"):
            self.organizemenu=None
        
        # item attributes
        if self.item_selection_brush is None:
            self.item_selection_brush=wx.TheBrushList.FindOrCreateBrush("MEDIUMPURPLE2", wx.SOLID)
            self.item_selection_pen=wx.ThePenList.FindOrCreatePen("MEDIUMPURPLE2", 1, wx.SOLID)
            f1=wx.TheFontList.FindOrCreateFont(10, wx.SWISS, wx.NORMAL, wx.BOLD)
            f2=wx.TheFontList.FindOrCreateFont(10, wx.SWISS, wx.NORMAL, wx.NORMAL)
            self.item_line_font=[f1, f2, f2, f2]
            dc=wx.MemoryDC()
            dc.SelectObject(wx.EmptyBitmap(100,100))
            self.item_guardspace=dc.GetTextExtent(self.item_term)[0]
            del dc

        # no redraw ickiness
        # wx.EVT_ERASE_BACKGROUND(self, lambda evt: None)
        
        self.mainwindow=mainwindow
        self.thedir=None
        self.wildcard="I forgot to set wildcard in derived class|*"
        self.__dragging=False
        self._in_context_menu=False

        # use the aggregatedisplay to do the actual item display
        self.aggdisp=aggregatedisplay.Display(self, self, watermark) # we are our own datasource
        vbs=wx.BoxSizer(wx.VERTICAL)
        vbs.Add(self.aggdisp, 1, wx.EXPAND|wx.ALL, 2)
        self.SetSizer(vbs)
        timerid=wx.NewId()
        self.thetimer=wx.Timer(self, timerid)
        wx.EVT_TIMER(self, timerid, self.OnTooltipTimer)
        self.motionpos=None
        wx.EVT_MOUSE_EVENTS(self.aggdisp, self.OnMouseEvent)
        self.tipwindow=None
        if guihelper.IsMSWindows():
            # turn on drag-and-drag for windows
            wx.EVT_MOTION(self.aggdisp, self.OnStartDrag)

        # Menus

        self.itemmenu=wx.Menu()
        self.itemmenu.Append(guihelper.ID_FV_OPEN, "Open")
        self.itemmenu.Append(guihelper.ID_FV_SAVE, "Save ...")
        self.itemmenu.AppendSeparator()
        if guihelper.IsMSWindows():
            self.itemmenu.Append(guihelper.ID_FV_COPY, "Copy")
        self.itemmenu.Append(guihelper.ID_FV_DELETE, "Delete")
        self.itemmenu.Append(guihelper.ID_FV_RENAME, "Rename")
        self.itemmenu.AppendSeparator()
        # set origin menu
        if self.origin_list:
            _origin_menu=wx.Menu()
            for o in self.origin_list:
                _id=wx.NewId()
                _origin_menu.Append(_id, o)
                wx.EVT_MENU(self, _id, self.OnSetOrigin)
            self._origin_menu_id=wx.NewId()
            self.itemmenu.AppendMenu(self._origin_menu_id,
                                     'Set Origin', _origin_menu)
            self.itemmenu.AppendSeparator()
        else:
            self._origin_menu_id=None
        # self.itemmenu.Append(guihelper.ID_FV_RENAME, "Rename")
        self.itemmenu.Append(guihelper.ID_FV_REFRESH, "Refresh")

        self.bgmenu=wx.Menu()
        if self.organizemenu is not None:
            self.bgmenu.AppendMenu(wx.NewId(), "Organize by", self.organizemenu)
        self.bgmenu.Append(guihelper.ID_FV_ADD, "Add ...")
        self.bgmenu.Append(guihelper.ID_FV_PASTE, "Paste")
        self.bgmenu.Append(guihelper.ID_FV_REFRESH, "Refresh")

        wx.EVT_MENU(self.itemmenu, guihelper.ID_FV_OPEN, self.OnLaunch)
        wx.EVT_MENU(self.itemmenu, guihelper.ID_FV_SAVE, self.OnSave)
        if guihelper.IsMSWindows():
            wx.EVT_MENU(self.itemmenu, guihelper.ID_FV_COPY, self.OnCopy)
        wx.EVT_MENU(self.itemmenu, guihelper.ID_FV_DELETE, self.OnDelete)
        wx.EVT_MENU(self.itemmenu, guihelper.ID_FV_RENAME, self.OnRename)
        wx.EVT_MENU(self.itemmenu, guihelper.ID_FV_REFRESH, lambda evt: self.OnRefresh())
        wx.EVT_MENU(self.bgmenu, guihelper.ID_FV_ADD, self.OnAdd)
        wx.EVT_MENU(self.bgmenu, guihelper.ID_FV_PASTE, self.OnPaste)
        wx.EVT_MENU(self.bgmenu, guihelper.ID_FV_REFRESH, lambda evt: self.OnRefresh)

        wx.EVT_RIGHT_UP(self.aggdisp, self.OnRightClick)
        aggregatedisplay.EVT_ACTIVATE(self.aggdisp, self.aggdisp.GetId(), self.OnLaunch)

        self.droptarget=MyFileDropTarget(self)
        self.SetDropTarget(self.droptarget)
        wx.EVT_SIZE(self, self.OnSize)

    def OnSize(self, evt):
        # stop the tool tip from poping up when we're resizing!
        if self.thetimer.IsRunning():
            self.thetimer.Stop()
        evt.Skip()

    def OnRightClick(self, evt):
        """Popup the right click context menu

        @param widget:  which widget to popup in
        @param position:  position in widget
        @param onitem: True if the context menu is for an item
        """
        if len(self.aggdisp.GetSelection()):
            menu=self.itemmenu
            item=self.GetSelectedItems()[0]
            menu.Enable(guihelper.ID_FV_RENAME, len(self.GetSelectedItems())==1)
            # we always launch on mac
            if not guihelper.IsMac():
                menu.FindItemById(guihelper.ID_FV_OPEN).Enable(guihelper.GetOpenCommand(item.fileinfo.mimetypes, item.filename) is not None)
            # check for set origin menu item
            if self._origin_menu_id:
                menu.Enable(self._origin_menu_id,
                            bool(len(self.GetSelectedItems())==1 and \
                            item.origin is None))
        else:
            menu=self.bgmenu
            menu.Enable(guihelper.ID_FV_PASTE, self.CanPaste())
        if menu is None:
            return
        # we're putting up the context menu, quit the tool tip timer.
        self._in_context_menu=True
        self.aggdisp.PopupMenu(menu, evt.GetPosition())
        self._in_context_menu=False

    def OnLaunch(self, _):
        item=self.GetSelectedItems()[0]
        if guihelper.IsMac():
            import findertools
            findertools.launch(item.filename)
            return
        cmd=guihelper.GetOpenCommand(item.fileinfo.mimetypes, item.filename)
        if cmd is None:
            wx.Bell()
        else:
            wx.Execute(cmd, wx.EXEC_ASYNC)

    if guihelper.IsMSWindows():
        # drag-and-drop files only works in Windows
        def OnStartDrag(self, evt):
            evt.Skip()
            if not evt.LeftIsDown():
                return
            items=self.GetSelectedItems()
            if not len(items):
                return
            drag_source=wx.DropSource(self)
            file_names=wx.FileDataObject()
            for item in items:
                file_names.AddFile(item.filename)
            drag_source.SetData(file_names)
            self.__dragging=True
            res=drag_source.DoDragDrop(wx.Drag_AllowMove)
            self.__dragging=False
            # check of any of the files have been removed,
            # can't trust result returned by DoDragDrop
            for item in items:
                # this used to use os.access function, but it does not
                # support unicode filenames
                if not os.path.isfile(item.filename):
                    item.RemoveFromIndex()

    def OnMouseEvent(self, evt):
        self.motionpos=evt.GetPosition()
        evt.Skip()
        self.thetimer.Stop()
        if evt.AltDown() or evt.MetaDown() or evt.ControlDown() or \
           evt.ShiftDown() or evt.Dragging() or evt.IsButton() or \
           self._in_context_menu:
            return
        self.thetimer.Start(1750, wx.TIMER_ONE_SHOT)

    def OnTooltipTimer(self, _):
        if self._in_context_menu:
            # we're putting up a context menu, forget this
            return
        x,y=self.aggdisp.CalcUnscrolledPosition(*self.motionpos)
        res=self.aggdisp.HitTest(x,y)
        if res.item is not None:
            try:    self.tipwindow.Destroy()
            except: pass
            self.tipwindow=res.item.DisplayTooltip(self.aggdisp, res.itemrectscrolled)

    def OnRefresh(self):
        self.aggdisp.UpdateItems()

    def GetSelectedItems(self):
        return [item for _,_,_,item in self.aggdisp.GetSelection()]

    def GetAllItems(self):
        return [item for _,_,_,item in self.aggdisp.GetAllItems()]

    def OnSelectAll(self, _):
        self.aggdisp.SelectAll()

    def EndSelectedFilesContext(self, context, deleteitems=False):
        # We have a fun additional problem.  By default Windows
        # returns a code that it is copying, when in fact it is
        # moving.  Consequently we do a delete if either the
        # source file is gone, or deleteitems is true
        if not deleteitems:
            for item in context:
                if not os.path.exists(item.filename):
                    print "Forcing EndSelectedFilesContext to delete mode even though not specified"
                    deleteitems=True
                    break
        if deleteitems:
            for item in context:
                if os.path.exists(item.filename):
                    os.remove(item.filename)
            for item in context:
                item.RemoveFromIndex()
            self.OnRefresh()

    def OnSave(self, _):
        # If one item is selected we ask for a filename to save.  If
        # multiple then we ask for a directory, and users don't get
        # the choice to affect the names of files.  Note that we don't
        # allow users to select a different format for the file - we
        # just copy it as is.
        items=self.GetSelectedItems()
        if len(items)==1:
            ext=getext(items[0].name)
            if ext=="": ext="*"
            else: ext="*."+ext
            dlg=wx.FileDialog(self, "Save item", wildcard=ext, defaultFile=items[0].name, style=wx.SAVE|wx.OVERWRITE_PROMPT|wx.CHANGE_DIR)
            if dlg.ShowModal()==wx.ID_OK:
                shutil.copyfile(items[0].filename, dlg.GetPath())
            dlg.Destroy()
        else:
            dlg=wx.DirDialog(self, "Save items to", style=wx.DD_DEFAULT_STYLE|wx.DD_NEW_DIR_BUTTON)
            if dlg.ShowModal()==wx.ID_OK:
                for item in items:
                    shutil.copyfile(item.filename, os.path.join(dlg.GetPath(), basename(item.filename)))
            dlg.Destroy()

    if guihelper.IsMSWindows():
        def OnCopy(self, _):
            items=self.GetSelectedItems()
            if not len(items):
                # nothing selected
                return
            file_names=wx.FileDataObject()
            for item in items:
                file_names.AddFile(item.filename)
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(file_names)
                wx.TheClipboard.Close()
        def CanCopy(self):
            return len(self.GetSelectedItems())

    def OnPaste(self, _=None):
        if not wx.TheClipboard.Open():
            # can't access the clipboard
            return
        if wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_FILENAME)):
            file_names=wx.FileDataObject()
            has_data=wx.TheClipboard.GetData(file_names)
        else:
            has_data=False
        wx.TheClipboard.Close()
        if has_data:
            self.OnAddFiles(file_names.GetFilenames())
    def CanPaste(self):
        """ Return True if can accept clipboard data, False otherwise
        """
        if not wx.TheClipboard.Open():
            return False
        r=wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_FILENAME))
        wx.TheClipboard.Close()
        return r

    def CanDelete(self):
        if len(self.aggdisp.GetSelection()):
            return True
        return False        

    def OnDelete(self,_):
        items=self.GetSelectedItems()
        for item in items:
            os.remove(item.filename)
        for item in items:
            item.RemoveFromIndex()
        self.OnRefresh()

    def OnSetOrigin(self, evt):
        _origin=evt.GetEventObject().GetLabel(evt.GetId())
        _items=self.GetSelectedItems()
        for _item in _items:
            _item.SetOrigin(_origin)
        self.OnRefresh()

    def genericpopulatefs(self, dict, key, indexkey, version):
        try:
            os.makedirs(self.thedir)
        except:
            pass
        if not os.path.isdir(self.thedir):
            raise Exception("Bad directory for "+key+" '"+self.thedir+"'")

        # delete all files we don't know about if 'key' contains replacements
        if dict.has_key(key):
            print key,"present - updating disk"
            for f in os.listdir(self.thedir):
                # delete them all except windows magic ones which we ignore
                if f.lower() not in self.skiplist:
                    os.remove(os.path.join(self.thedir, f))

            d=dict[key]
            for i in d:
                open(os.path.join(self.thedir, i.encode(media_codec)), "wb").write(d[i])
        d={}
        d[indexkey]=dict[indexkey]
        common.writeversionindexfile(os.path.join(self.thedir, "index.idx"), d, version)
        return dict

    def genericgetfromfs(self, result, key, indexkey, currentversion):
        try:
            os.makedirs(self.thedir)
        except:
            pass
        if not os.path.isdir(self.thedir):
            raise Exception("Bad directory for "+key+" '"+self.thedir+"'")
        dict={}
        for file in os.listdir(self.thedir):
            if file=='index.idx':
                d={}
                d['result']={}
                common.readversionedindexfile(os.path.join(self.thedir, file), d, self.versionupgrade, currentversion)
                result.update(d['result'])
            elif file.lower() in self.skiplist:
                # ignore windows detritus
                continue
            elif key is not None:
                dict[file.decode(media_codec)]=open(os.path.join(self.thedir, file), "rb").read()
        if key is not None:
            result[key]=dict
        if indexkey not in result:
            result[indexkey]={}
        return result

    def OnDropFiles(self, _, dummy, filenames):
        # There is a bug in that the most recently created tab
        # in the notebook that accepts filedrop receives these
        # files, not the most visible one.  We find the currently
        # viewed tab in the notebook and send the files there
        if self.__dragging:
            # I'm the drag source, forget 'bout it !
            return
        target=self # fallback
        t=self.mainwindow.nb.GetPage(self.mainwindow.nb.GetSelection())
        if isinstance(t, FileView):
            # changing target in dragndrop
            target=t
        target.OnAddFiles(filenames)

    def CanAdd(self):
        return True

    def OnAdd(self, _=None):
        dlg=wx.FileDialog(self, "Choose files", style=wx.OPEN|wx.MULTIPLE, wildcard=self.wildcard)
        if dlg.ShowModal()==wx.ID_OK:
            self.OnAddFiles(dlg.GetPaths())
        dlg.Destroy()

    def CanRename(self):
        return len(self.GetSelectedItems())==1
    # subclass needs to define this
    media_notification_type=None
    def OnRename(self, _=None):
        items=self.GetSelectedItems()
        if len(items)!=1:
               # either none or more than 1 items selected
               return
        old_name=items[0].name
        dlg=wx.TextEntryDialog(self, "Enter a new name:", "Item Rename",
                               old_name)
        if dlg.ShowModal()==wx.ID_OK:
            new_name=dlg.GetValue()
            if len(new_name) and new_name!=old_name:
                old_file_name=items[0].filename
                new_file_name=self.getshortenedbasename(new_name)
                try:
                    os.rename(old_file_name, new_file_name)
                    items[0].RenameInIndex(os.path.basename(
                        str(new_file_name).decode(media_codec)))
                    pubsub.publish(pubsub.MEDIA_NAME_CHANGED,
                                   data={ pubsub.media_change_type: self.media_notification_type,
                                          pubsub.media_old_name: old_file_name,
                                          pubsub.media_new_name: new_file_name })
                except:
                    pass
        dlg.Destroy()
          
    def OnAddFiles(self,_):
        raise Exception("not implemented")

    def decodefilename(self, filename):
        path,filename=os.path.split(filename)
        decoded_file=str(filename).decode(media_codec)
        return os.path.join(path, decoded_file)

    def getshortenedbasename(self, filename, newext=''):
        filename=basename(filename)
        if not 'A' in self.filenamechars:
            filename=filename.lower()
        if not 'a' in self.filenamechars:
            filename=filename.upper()
        if len(newext):
            filename=stripext(filename)
        filename="".join([x for x in filename if x in self.filenamechars])
        filename=filename.replace("  "," ").replace("  ", " ")  # remove double spaces
        if len(newext):
            filename+='.'+newext
        if len(filename)>self.maxlen:
            chop=len(filename)-self.maxlen
            filename=stripext(filename)[:-chop].strip()+'.'+getext(filename)
        return os.path.join(self.thedir, filename.encode(media_codec))

    def genericgetdata(self,dict,want, mediapath, mediakey, mediaindexkey):
        # this was originally written for wallpaper hence using the 'wp' variable
        dict.update(self._data)
        items=None
        if want==self.SELECTED:
            items=self.GetSelectedItems()
            if len(items)==0:
                want=self.ALL

        if want==self.ALL:
            items=self.GetAllItems()

        if items is not None:
            wp={}
            i=0
            for item in items:
                data=open(item.filename, "rb").read()
                wp[i]={'name': item.name, 'data': data}
                v=item.origin
                if v is not None:
                    wp[i]['origin']=v
                i+=1
            dict[mediakey]=wp
                
        return dict

    def log(self, log_str):
        self.mainwindow.log(log_str)

class FileViewDisplayItem(object):

    datakey="Someone forgot to set me"
    PADDING=3

    def __init__(self, view, key, mediapath):
        self.view=view
        self.key=key
        self.thumbsize=10,10
        self.mediapath=mediapath
        self.setvals()
        self.lastw=None

    def setvals(self):
        me=self.view._data[self.datakey][self.key]
        self.name=me['name']
        self.origin=me.get('origin', None)
        self.filename=os.path.join(self.mediapath, self.name.encode(media_codec))
        self.fileinfo=self.view.GetFileInfo(self.filename)
        self.size=self.fileinfo.size
        self.short=self.fileinfo.shortdescription()
        self.long=self.fileinfo.longdescription()
        self.thumb=None
        self.selbbox=None
        self.lines=[self.name, self.short,
                    '%.1f kb' % (self.size/1024.0,)]
        if self.origin:
            self.lines.append(self.origin)

    def setthumbnailsize(self, thumbnailsize):
        self.thumbnailsize=thumbnailsize
        self.thumb=None
        self.selbox=None

    def Draw(self, dc, width, height, selected):
        if self.thumb is None:
            self.thumb=self.view.GetItemThumbnail(self.name, self.thumbnailsize[0], self.thumbnailsize[1])
        redrawbbox=False
        if selected:
            if self.lastw!=width or self.selbbox is None:
                redrawbbox=True
            else:
                oldb=dc.GetBrush()
                oldp=dc.GetPen()
                dc.SetBrush(self.view.item_selection_brush)
                dc.SetPen(self.view.item_selection_pen)
                dc.DrawRectangle(*self.selbbox)
                dc.SetBrush(oldb)
                dc.SetPen(oldp)
        dc.DrawBitmap(self.thumb, self.PADDING+self.thumbnailsize[0]/2-self.thumb.GetWidth()/2, self.PADDING, True)
        xoff=self.PADDING+self.thumbnailsize[0]+self.PADDING
        yoff=self.PADDING*2
        widthavailable=width-xoff-self.PADDING
        maxw=0
        old=dc.GetFont()
        for i,line in enumerate(self.lines):
            dc.SetFont(self.view.item_line_font[i])
            w,h=DrawTextWithLimit(dc, xoff, yoff, line, widthavailable, self.view.item_guardspace, self.view.item_term)
            maxw=max(maxw,w)
            yoff+=h
        dc.SetFont(old)
        self.lastw=width
        self.selbbox=(0,0,xoff+maxw+self.PADDING,max(yoff+self.PADDING,self.thumb.GetHeight()+self.PADDING*2))
        if redrawbbox:
            return self.Draw(dc, width, height, selected)
        return self.selbbox

    def DisplayTooltip(self, parent, rect):
        res=["Name: "+self.name, "Origin: "+(self.origin, "default")[self.origin is None],
             'File size: %.1f kb (%d bytes)' % (self.size/1024.0, self.size), "\n"+self.datatype+" information:\n", self.long]
        # tipwindow takes screen coordinates so we have to transform
        x,y=parent.ClientToScreen(rect[0:2])
        return wx.TipWindow(parent, "\n".join(res), 1024, wx.Rect(x,y,rect[2], rect[3]))

    def RemoveFromIndex(self):
        del self.view._data[self.datakey][self.key]
        self.view.modified=True
        self.view.OnRefresh()

    def RenameInIndex(self, new_name):
        self.view._data[self.datakey][self.key]['name']=new_name
        self.view.modified=True
        self.view.OnRefresh()

    def SetOrigin(self, new_origin):
        # set the origin of this item
        self.view._data[self.datakey][self.key]['origin']=new_origin
        self.view.modified=True
        self.view.OnRefresh()

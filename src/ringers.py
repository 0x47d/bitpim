### BITPIM
###
### Copyright (C) 2003-2004 Roger Binns <rogerb@rogerbinns.com>
### Copyright (C) 2003-2004 Steven Palm <n9yty@n9yty.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

import wx
import bpaudio
import guiwidgets
import guihelper
import os
import pubsub
import aggregatedisplay
import wallpaper
import common

###
###  Ringers
###

class DisplayItem(object):

    PADDING=3

    def __init__(self, view, key):
        self.view=view
        self.key=key
        self.thumbsize=10,10
        self.setvals()
        self.lastw=None

    def setvals(self):
        me=self.view._data['ringtone-index'][self.key]
        self.name=me['name']
        self.origin=me.get('origin', None)
        self.filename=os.path.join(self.view.mainwindow.ringerpath, self.name)
        try:
            self.size=os.stat(self.filename).st_size
        except OSError:
            self.size=-1
        self.thumb=None
        self.selbbox=None
        self.lines=[self.name, common.getext(self.name), '%.1f kb' % (self.size/1024.0,)]
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
        dc.DrawBitmap(self.thumb, self.PADDING, self.PADDING, True)
        xoff=self.PADDING+self.thumbnailsize[0]+self.PADDING
        yoff=self.PADDING*2
        widthavailable=width-xoff-self.PADDING
        maxw=0
        old=dc.GetFont()
        for i,line in enumerate(self.lines):
            dc.SetFont(self.view.item_line_font[i])
            w,h=guiwidgets.DrawTextWithLimit(dc, xoff, yoff, line, widthavailable, self.view.item_guardspace, self.view.item_term)
            maxw=max(maxw,w)
            yoff+=h
        dc.SetFont(old)
        self.lastw=width
        self.selbbox=(0,0,xoff+maxw+self.PADDING,max(yoff+self.PADDING,self.thumb.GetHeight()+self.PADDING*2))
        if redrawbbox:
            return self.Draw(dc, width, height, selected)
        return self.selbbox

    def RemoveFromIndex(self):
        del self.view._data['ringtone-index'][self.key]
        self.view.modified=True
        self.view.OnRefresh()

    def DisplayTooltip(self, parent, rect):
        return None

class RingerView(guiwidgets.FileView):
    CURRENTFILEVERSION=2

    # this is only used to prevent the pubsub module
    # from being GC while any instance of this class exists
    __publisher=pubsub.Publisher

    
    def __init__(self, mainwindow, parent, id=-1):
        self.mainwindow=mainwindow
        self._data={'ringtone-index': {}}
        self.updateprofilevariables(self.mainwindow.phoneprofile)
        guiwidgets.FileView.__init__(self, mainwindow, parent, "ringtone-watermark")
        self.wildcard="Audio files|*.wav;*.mid;*.qcp;*.mp3|Midi files|*.mid|Purevoice files|*.qcp|MP3 files|*.mp3|All files|*.*"

        self.modified=False
        wx.EVT_IDLE(self, self.OnIdle)
        pubsub.subscribe(self.OnListRequest, pubsub.REQUEST_RINGTONES)
        pubsub.subscribe(self.OnDictRequest, pubsub.REQUEST_RINGTONE_INDEX)

    def updateprofilevariables(self, profile):
        self.maxlen=profile.MAX_RINGTONE_BASENAME_LENGTH
        self.filenamechars=profile.RINGTONE_FILENAME_CHARS

    def OnListRequest(self, msg=None):
        l=[self._data['ringtone-index'][x]['name'] for x in self._data['ringtone-index']]
        l.sort()
        pubsub.publish(pubsub.ALL_RINGTONES, l)

    def OnDictRequest(self, msg=None):
        pubsub.publish(pubsub.ALL_RINGTONE_INDEX, self._data['ringtone-index'].copy())

    def OnIdle(self, _):
        "Save out changed data"
        if self.modified:
            self.modified=False
            self.populatefs(self._data)
            self.OnListRequest() # broadcast changes

    def getdata(self,dict,want=guiwidgets.FileView.NONE):
        return self.genericgetdata(dict, want, self.mainwindow.ringerpath, 'ringtone', 'ringtone-index')

    def GetItemThumbnail(self, item, w, h):
        assert w==self.thumbnail.GetWidth() and h==self.thumbnail.GetHeight()
        return self.thumbnail

    def GetSections(self):
        x=aggregatedisplay.SectionHeader("Ringtones")
        self.thumbnail=wx.Image(guihelper.getresourcefile('ringer.png')).ConvertToBitmap()
        x.thumbsize=(self.thumbnail.GetWidth(), self.thumbnail.GetHeight())
        dc=wx.MemoryDC()
        dc.SelectObject(wx.EmptyBitmap(100,100))
        h=dc.GetTextExtent("I")[1]
        x.itemsize=x.thumbsize[0]+120, max(x.thumbsize[1], h*4)+DisplayItem.PADDING*2
        return [x]

    def GetItemSize(self, sectionnumber, sectionheader):
        return sectionheader.itemsize

    def GetItemsFromSection(self, sectionnumber, sectionheader):
        items=[DisplayItem(self, key) for key in self._data['ringtone-index']]
        # prune out ones we don't have files for
        items=[item for item in items if os.path.exists(item.filename)]
        for item in items:
            item.setthumbnailsize(sectionheader.thumbsize)
        return items

    def RemoveFromIndex(self, names):
        for name in names:
            wp=self._data['ringtone-index']
            for k in wp.keys():
                if wp[k]['name']==name:
                    del wp[k]
                    self.modified=True
            
    def OnAddFiles(self, filenames):
        print "OnAddFiles:",filenames
        for file in filenames:
            self.thedir=self.mainwindow.ringerpath
            # we don't try to do any format conversion now
            target=self.getshortenedbasename(file)
            if target==None: return # user didn't want to
            open(target, "wb").write(open(file, "rb").read())
            self.AddToIndex(os.path.basename(target).lower())
        self.OnRefresh()

    def AddToIndex(self, file):
        for i in self._data['ringtone-index']:
            if self._data['ringtone-index'][i]['name']==file:
                return
        keys=self._data['ringtone-index'].keys()
        idx=10000
        while idx in keys:
            idx+=1
        self._data['ringtone-index'][idx]={'name': file}
        self.modified=True


    def updateindex(self, index):
        if index!=self._data['ringtone-index']:
            self._data['ringtone-index']=index.copy()
            self.modified=True

    def populatefs(self, dict):
        self.thedir=self.mainwindow.ringerpath
        return self.genericpopulatefs(dict, 'ringtone', 'ringtone-index', self.CURRENTFILEVERSION)
            
    def populate(self, dict):
        if self._data['ringtone-index']!=dict['ringtone-index']:
            self._data['ringtone-index']=dict['ringtone-index'].copy()
            self.modified=True
        self.OnRefresh()
        
    def getfromfs(self, result):
        self.thedir=self.mainwindow.ringerpath
        return self.genericgetfromfs(result, None, 'ringtone-index', self.CURRENTFILEVERSION)

    def updateindex(self, index):
        if index!=self._data['ringtone-index']:
            self._data['ringtone-index']=index.copy()
            self.modified=True

    def versionupgrade(self, dict, version):
        """Upgrade old data format read from disk

        @param dict:  The dict that was read in
        @param version: version number of the data on disk
        """

        # version 0 to 1 upgrade
        if version==0:
            version=1  # the are the same

        # 1 to 2 etc
        if version==1:
            print "converting to version 2"
            version=2
            d={}
            input=dict.get('ringtone-index', {})
            for i in input:
                d[i]={'name': input[i]}
            dict['ringtone-index']=d
        return dict

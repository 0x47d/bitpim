### BITPIM
###
### Copyright (C) 2003-2004 Roger Binns <rogerb@rogerbinns.com>
### Copyright (C) 2003-2004 Steven Palm <n9yty@n9yty.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

import os
import time
import wx


import bpaudio
import guiwidgets
import guihelper
import pubsub
import aggregatedisplay
import wallpaper
import common
import fileinfo
import conversions

###
###  Ringers
###

class DisplayItem(guiwidgets.FileViewDisplayItem):

    datakey='ringtone-index'
    datatype='Audio' # used in the tooltip


class RingerView(guiwidgets.FileView):
    CURRENTFILEVERSION=2

    # this is only used to prevent the pubsub module
    # from being GC while any instance of this class exists
    __publisher=pubsub.Publisher


    organizetypes=("Audio Type", "Origin", "File Size")
    
    def __init__(self, mainwindow, parent, id=-1):
        self.mainwindow=mainwindow
        self._data={'ringtone-index': {}}
        self.updateprofilevariables(self.mainwindow.phoneprofile)
        self.organizemenu=wx.Menu()
        guiwidgets.FileView.__init__(self, mainwindow, parent, "ringtone-watermark")
        self.wildcard="Audio files|*.wav;*.mid;*.qcp;*.mp3;*.pmd|Midi files|*.mid|Purevoice files|*.qcp|MP3 files|*.mp3|PMD/CMX files|*.pmd|All files|*.*"

        self.organizeinfo={}

        for k in self.organizetypes:
            id=wx.NewId()
            self.organizemenu.AppendRadioItem(id, k)
            wx.EVT_MENU(self, id, self.OrganizeChange)
            self.organizeinfo[id]=getattr(self, "organizeby_"+k.replace(" ",""))

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

    def OrganizeChange(self, evt):
        evt.GetEventObject().Check(evt.GetId(), True)
        self.OnRefresh()

    def GetSections(self):
        # work out section and item sizes
        self.thumbnail=wx.Image(guihelper.getresourcefile('ringer.png')).ConvertToBitmap()
        
        dc=wx.MemoryDC()
        dc.SelectObject(wx.EmptyBitmap(100,100)) # unused bitmap needed to keep wxMac happy
        h=dc.GetTextExtent("I")[1]
        itemsize=self.thumbnail.GetWidth()+160, max(self.thumbnail.GetHeight(), h*4+DisplayItem.PADDING)+DisplayItem.PADDING*2
        
        # get all the items
        items=[DisplayItem(self, key, self.mainwindow.ringerpath) for key in self._data['ringtone-index']]
        # prune out ones we don't have images for
        items=[item for item in items if os.path.exists(item.filename)]

        self.sections=[]

        if len(items)==0:
            return self.sections
        
        # get the current sorting type
        for i in range(len(self.organizetypes)):
            item=self.organizemenu.FindItemByPosition(i)
            if self.organizemenu.IsChecked(item.GetId()):
                for sectionlabel, items in self.organizeinfo[item.GetId()](items):
                    sh=aggregatedisplay.SectionHeader(sectionlabel)
                    sh.itemsize=itemsize
                    for item in items:
                        item.thumbnailsize=self.thumbnail.GetWidth(), self.thumbnail.GetHeight()
                    # sort items by name
                    items=[(item.name.lower(), item) for item in items]
                    items.sort()
                    items=[item for name,item in items]
                    self.sections.append( (sh, items) )
                return [sh for sh,items in self.sections]
        assert False, "Can't get here"

    def GetItemsFromSection(self, sectionnumber, sectionheader):
        return self.sections[sectionnumber][1]

    def organizeby_AudioType(self, items):
        types={}
        for item in items:
            t=item.fileinfo.format
            if t is None: t="<Unknown>"
            l=types.get(t, [])
            l.append(item)
            types[t]=l

        keys=types.keys()
        keys.sort()
        return [ (key, types[key]) for key in types]

    def organizeby_Origin(self, items):
        types={}
        for item in items:
            t=item.origin
            if t is None: t="Default"
            l=types.get(t, [])
            l.append(item)
            types[t]=l

        keys=types.keys()
        keys.sort()
        return [ (key, types[key]) for key in types]
        
    def organizeby_FileSize(self, items):
        
        sizes={0: ('Less than 8kb', []),
               8192: ('8 kilobytes', []),
               16384: ('16 kilobytes', []),
               32768: ('32 kilobytes', []),
               65536: ('64 kilobytes', []),
               131052: ('128 kilobytes', []),
               524208: ('512 kilobytes', []),
               1024*1024: ('One megabyte', [])}

        keys=sizes.keys()
        keys.sort()

        for item in items:
            t=item.size
            if t>=keys[-1]:
                sizes[keys[-1]][1].append(item)
                continue
            for i,k in enumerate(keys):
                if t<keys[i+1]:
                    sizes[k][1].append(item)
                    break

        return [sizes[k] for k in keys if len(sizes[k][1])]   

    def GetItemSize(self, sectionnumber, sectionheader):
        return sectionheader.itemsize

    def GetFileInfo(self, filename):
        return fileinfo.identify_audiofile(filename)

    def RemoveFromIndex(self, names):
        for name in names:
            wp=self._data['ringtone-index']
            for k in wp.keys():
                if wp[k]['name']==name:
                    del wp[k]
                    self.modified=True
            
    def OnAddFiles(self, filenames):
        for file in filenames:
            if file is None: continue  # failed dragdrop?
            # do we want to convert file?
            afi=fileinfo.identify_audiofile(file)
            if afi.size<=0: continue # zero length file or other issues
            newext,convertinfo=self.mainwindow.phoneprofile.QueryAudio(None, common.getext(file), afi)
            if convertinfo is not afi:
                filedata=None
                wx.EndBusyCursor()
                try:
                    filedata=self.ConvertFormat(file, convertinfo)
                finally:
                    # ensure they match up
                    wx.BeginBusyCursor()
                if filedata is None:
                    continue
            else:
                filedata=open(file, "rb").read()
            self.thedir=self.mainwindow.ringerpath
            target=self.getshortenedbasename(file, newext)
            open(target, "wb").write(filedata)
            self.AddToIndex(os.path.basename(target))
        self.OnRefresh()

    OnAddFiles=guihelper.BusyWrapper(OnAddFiles)

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

    def ConvertFormat(self, file, convertinfo):
        if convertinfo.format=='MP3':
            dlg=ConvertDialog(self, file, convertinfo)
        elif convertinfo.format=='QCP':
            dlg=ConvertMP3toQCP(self, file, convertinfo)
        else:
            # no can do
            return None
        if dlg.ShowModal()==wx.ID_OK:
            res=dlg.newfiledata
        else:
            res=None
        dlg.Destroy()
        return res

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

class ConvertDialog(wx.Dialog):

    ID_CONVERT=wx.NewId()
    ID_DELETE_BEFORE=wx.NewId()
    ID_DELETE_AFTER=wx.NewId()
    ID_PLAY=wx.NewId()
    ID_STOP=wx.NewId()
    ID_TIMER=wx.NewId()

    def __init__(self, parent, file, convertinfo):
        wx.Dialog.__init__(self, parent, title="Convert Audio File")
        self.file=file
        self.convertinfo=convertinfo
        self.afi=None
        self.mp3file=common.gettempfilename("mp3")
        self.workingmp3file=common.gettempfilename("mp3")
        self.wavfile=common.gettempfilename("wav")
        vbs=wx.BoxSizer(wx.VERTICAL)
        # create the covert controls
        self.create_convert_pane(vbs, file, convertinfo)
        # and the crop controls
        self.create_crop_panel(vbs)

        vbs.Add(self.CreateButtonSizer(wx.OK|wx.CANCEL|wx.HELP), 0, wx.ALL|wx.ALIGN_RIGHT, 5)

        self.SetSizer(vbs)
        vbs.Fit(self)

        # Events
        wx.EVT_BUTTON(self, wx.ID_OK, self.OnOk)
        wx.EVT_BUTTON(self, wx.ID_CANCEL, self.OnCancel)
        wx.EVT_TIMER(self, self.ID_TIMER, self.OnTimer)

        # timers and sounds
        self.sound=None
        self.timer=wx.Timer(self, self.ID_TIMER)

    def create_convert_pane(self, vbs, file, convertinfo):
        # convert bit
        bs=wx.StaticBoxSizer(wx.StaticBox(self, -1, "Convert"), wx.VERTICAL)
        bs.Add(wx.StaticText(self, -1, "Input File: "+file), 0, wx.ALL, 5)
        gs=wx.FlexGridSizer(2, 4, 5, 5)
        gs.Add(wx.StaticText(self, -1, "New Type"), 0, wx.ALL|wx.ALIGN_CENTRE_VERTICAL, 5)
        self.type=wx.ComboBox(self, style=wx.CB_DROPDOWN|wx.CB_READONLY, choices=["MP3"])
        gs.Add(self.type, 0, wx.ALL|wx.EXPAND, 5)
        gs.Add(wx.StaticText(self, -1, "Sample Rate (Hz)"), 0, wx.ALL|wx.ALIGN_CENTRE_VERTICAL, 5)
        self.samplerate=wx.ComboBox(self, style=wx.CB_DROPDOWN|wx.CB_READONLY, choices=["16000", "22050", "24000", "32000", "44100", "48000"])
        gs.Add(self.samplerate, 0, wx.ALL|wx.EXPAND, 5)
        gs.Add(wx.StaticText(self, -1, "Channels (Mono/Stereo)"), 0, wx.ALL|wx.ALIGN_CENTRE_VERTICAL, 5)
        self.channels=wx.ComboBox(self, style=wx.CB_DROPDOWN|wx.CB_READONLY, choices=["1", "2"])
        gs.Add(self.channels, 0, wx.ALL|wx.EXPAND, 5)
        gs.Add(wx.StaticText(self, -1, "Bitrate (kbits per second)"), 0, wx.ALL|wx.ALIGN_CENTRE_VERTICAL, 5)
        self.bitrate=wx.ComboBox(self, style=wx.CB_DROPDOWN|wx.CB_READONLY, choices=["8", "16", "24", "32", "40", "48", "56", "64", "80", "96", "112",
                                                                                     "128", "144", "160", "192", "224", "256", "320"])
        gs.Add(self.bitrate, 0, wx.ALL|wx.EXPAND, 5)
        gs.AddGrowableCol(1, 1)
        gs.AddGrowableCol(3, 1)
        bs.Add(gs, 0, wx.EXPAND)

        bs.Add(wx.Button(self, self.ID_CONVERT, "Convert"), 0, wx.ALIGN_RIGHT|wx.ALL, 5)

        vbs.Add(bs, 0, wx.EXPAND|wx.ALL, 5)
        # Fill out fields
        if convertinfo.format!="MP3": raise common.ConversionNotSupported("Can only convert to MP3")
        self.type.SetStringSelection(convertinfo.format)
        self.channels.SetStringSelection(`convertinfo.channels`)
        self.bitrate.SetStringSelection(`convertinfo.bitrate`)
        self.samplerate.SetStringSelection(`convertinfo.samplerate`)
        # Events
        wx.EVT_BUTTON(self, self.ID_CONVERT, self.OnConvert)

    def create_crop_panel(self, vbs):
        # crop bit
        bs=wx.StaticBoxSizer(wx.StaticBox(self, -1, "Crop"), wx.VERTICAL)
        hbs=wx.BoxSizer(wx.HORIZONTAL)
        hbs.Add(wx.StaticText(self, -1, "Position"), 0, wx.ALL|wx.ALIGN_CENTRE_VERTICAL, 5)
        self.positionlabel=wx.StaticText(self, -1, "0                 ")
        hbs.Add(self.positionlabel, 0, wx.ALL, 5)
        hbs.Add(wx.StaticText(self, -1, "Duration"), 0, wx.ALL|wx.ALIGN_CENTRE_VERTICAL, 5)
        self.durationlabel=wx.StaticText(self, -1, "0                 ")
        hbs.Add(self.durationlabel, 0, wx.ALL, 5)
        hbs.Add(wx.StaticText(self, -1, "File length"), 0, wx.ALL|wx.ALIGN_CENTRE_VERTICAL, 5)
        self.lengthlabel=wx.StaticText(self, -1, "0                   ")
        hbs.Add(self.lengthlabel, 0, wx.ALL, 5)
        bs.Add(hbs, 0, wx.ALL, 5)
        hbs=wx.BoxSizer(wx.HORIZONTAL)
        self.slider=wx.Slider(self, -1, 0, 0, 1)
        hbs.Add(self.slider, 1, wx.EXPAND|wx.ALL, 5)
        bs.Add(hbs, 1, wx.EXPAND|wx.ALL, 5)
        hbs=wx.BoxSizer(wx.HORIZONTAL)
        hbs.Add(wx.Button(self, self.ID_DELETE_BEFORE, "Del Before"), 0, wx.ALL, 5)
        hbs.Add(wx.Button(self, self.ID_DELETE_AFTER,  "Del After"), 0, wx.ALL, 5)
        hbs.Add(wx.Button(self, self.ID_STOP, "Stop"), 0, wx.ALL, 5)
        hbs.Add(wx.Button(self, self.ID_PLAY, "Play"), 0, wx.ALL, 5)
        bs.Add(hbs, 0, wx.ALL|wx.ALIGN_RIGHT, 5)

        vbs.Add(bs, 0, wx.EXPAND|wx.ALL, 5)
        wx.EVT_BUTTON(self, self.ID_PLAY, self.OnPlay)
        wx.EVT_BUTTON(self, self.ID_STOP, self.OnStop)
        wx.EVT_BUTTON(self, self.ID_DELETE_BEFORE, self.OnDeleteBefore)
        wx.EVT_BUTTON(self, self.ID_DELETE_AFTER, self.OnDeleteAfter)
        wx.EVT_SCROLL_ENDSCROLL(self, self.OnUserSlider)
        wx.EVT_SCROLL_THUMBTRACK(self, self.OnUserSlider)
        wx.EVT_SCROLL_THUMBRELEASE(self, self.OnUserSlider)

    def OnConvert(self, _):
        try:
            wx.BeginBusyCursor()
            open(self.mp3file, "wb").write(conversions.converttomp3(self.file, int(self.bitrate.GetStringSelection()), int(self.samplerate.GetStringSelection()), int(self.channels.GetStringSelection())))
            self.afi=fileinfo.getmp3fileinfo(self.mp3file)
            self.beginframe=0
            self.endframe=len(self.afi.frames)
            self.UpdateCrop()
        finally:
            wx.EndBusyCursor()


    def UpdateCrop(self):
        frames=self.afi.frames
        duration=sum([frames[frame].duration for frame in range(self.beginframe, self.endframe)])
        self.durationlabel.SetLabel("%.1f secs" % (duration,))
        length=sum([frames[frame].nextoffset-frames[frame].offset for frame in range(self.beginframe, self.endframe)])
        self.lengthlabel.SetLabel(`length`)
        self.positionlabel.SetLabel(`0`)
        self.slider.SetRange(self.beginframe, self.endframe)
        self.slider.SetValue(self.beginframe)
                                    
    def UpdatePosition(self, curval=None):
        if curval is None: curval=self.slider.GetValue()
        frames=self.afi.frames
        duration=sum([frames[frame].duration for frame in range(self.beginframe, curval)])
        self.positionlabel.SetLabel("%.1f secs" % (duration,))

    def OnPlay(self,_):
        if self.afi is None:
            # not converted yet
            return
        self.OnStop()
        frames=self.afi.frames
        self.startpos=self.slider.GetValue()
        offset=frames[self.startpos].offset
        length=frames[self.endframe-1].nextoffset-offset
        duration=sum([frames[frame].duration for frame in range(self.startpos, self.endframe)])
        f=open(self.mp3file, "rb", 0)
        f.seek(offset)
        open(self.workingmp3file, "wb").write(f.read(length))
        f.close()
        conversions.convertmp3towav(self.workingmp3file, self.wavfile)
        self.sound=wx.Sound(self.wavfile)
        assert self.sound.IsOk()
        res=self.sound.Play(wx.SOUND_ASYNC)
        assert res
        self.starttime=time.time()
        self.endtime=self.starttime+duration
        self.timer.Start(100, wx.TIMER_CONTINUOUS)
        
    def OnTimer(self,_):
        now=time.time()
        if now>self.endtime:
            self.timer.Stop()
            # assert wx.Sound.IsPlaying()==False
            self.slider.SetValue(self.endframe)
            self.UpdatePosition(self.endframe)
            return
        # work out where the slider should go
        newval=self.startpos+(now-self.starttime)/self.afi.frames[self.startpos].duration
        self.slider.SetValue(newval)
        self.UpdatePosition(newval)            


    def OnStop(self, _=None):
        self.timer.Stop()
        if self.sound is not None:
            self.sound.Stop()
            self.sound=None
        
    def OnUserSlider(self, _):
        self.OnStop()
        wx.CallAfter(self.UpdatePosition)

    def OnDeleteBefore(self, _):
        if self.afi is None:
            return
        self.OnStop()
        self.beginframe=self.slider.GetValue()
        self.UpdateCrop()

    def OnDeleteAfter(self, _):
        if self.afi is None:
            return
        self.OnStop()
        self.endframe=self.slider.GetValue()
        self.UpdateCrop()

    def _removetempfiles(self):
        for file in self.mp3file, self.workingmp3file, self.wavfile:
            if os.path.exists(file):
                os.remove(file)
        
    def OnOk(self, evt):
        self.OnStop()
        # make new data
        self.newfiledata=None
        if self.afi is not None:
            frames=self.afi.frames
            offset=frames[self.beginframe].offset
            length=frames[self.endframe-1].nextoffset-offset
            try:
                f=open(self.mp3file, "rb", 0)
                f.seek(offset)
                self.newfiledata=f.read(length)
                f.close()
            except:
                pass
        # now remove files
        self._removetempfiles()
        # use normal handler to quit dialog
        evt.Skip()

    def OnCancel(self, evt):
        self.OnStop()
        self._removetempfiles()
        evt.Skip()

class ConvertMP3toQCP(ConvertDialog):
    def __init__(self, parent, file, convertinfo):
        ConvertDialog.__init__(self, parent, file, convertinfo)
        self.beginframe=self.endframe=0
        tempfilename=common.gettempfilename('')
        self.wavfile=tempfilename+'wav'
        self.qcpfile=tempfilename+'qcp'
        self.workingwavfile=common.gettempfilename('wav')
        
    def create_convert_pane(self, vbs, file, convertinfo):
        bs=wx.StaticBoxSizer(wx.StaticBox(self, -1, "Convert MP3 to QCP"), wx.VERTICAL)
        bs.Add(wx.StaticText(self, -1, "Input File: "+file), 0, wx.ALL, 5)
        self.__status=wx.StaticText(self, -1, 'Status: None')
        bs.Add(self.__status, 0, wx.ALL|wx.EXPAND, 5)
        bs.Add(wx.Button(self, self.ID_CONVERT, "Convert"), 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        vbs.Add(bs, 0, wx.EXPAND|wx.ALL, 5)
        # Events
        wx.EVT_BUTTON(self, self.ID_CONVERT, self.OnConvert)

    def OnConvert(self, _):
        try:
            wx.BeginBusyCursor()
            self.__status.SetLabel('Status: conversion in progress, please wait ...')
            kargc={ 'samplerate': 8000, 'channels': 1}
            if self.endframe:
                kargc['start']=self.beginframe
                kargc['duration']=self.endframe-self.beginframe
            conversions.convertmp3towav(self.file, self.wavfile, **kargc)
            conversions.convertwavtoqcp(self.wavfile)
            self.lengthlabel.SetLabel(str(os.stat(self.qcpfile).st_size))
            self.afi=fileinfo.getpcmfileinfo(self.wavfile)
            self.beginframe=0
            self.endframe=self.afi.duration
            self.UpdateCrop()
        finally:
            wx.EndBusyCursor()
            self.__status.SetLabel('Status: Completed')

    def UpdateCrop(self):
        self.durationlabel.SetLabel("%.1f secs" % (self.endframe-self.beginframe,))
        self.positionlabel.SetLabel(`0`)
        self.slider.SetRange(self.beginframe, self.endframe)
        self.slider.SetValue(self.beginframe)

    def OnPlay(self,_):
        if self.afi is None:
            return
        self.OnStop()
        self.startpos=self.slider.GetValue()
        duration=self.endframe-self.startpos
        conversions.convertmp3towav(self.wavfile, self.workingwavfile,
                                    start=self.startpos)
        self.sound=wx.Sound(self.workingwavfile)
        assert self.sound.IsOk()
        res=self.sound.Play(wx.SOUND_ASYNC)
        assert res
        print 'duration:', duration
        self.starttime=time.time()
        self.endtime=self.starttime+duration
        self.timer.Start(100, wx.TIMER_CONTINUOUS)

    def UpdatePosition(self, curval=None):
        if curval is None: curval=self.slider.GetValue()
        self.positionlabel.SetLabel("%.1f secs" % (curval,))

    def OnTimer(self,_):
        now=time.time()
        if now>self.endtime:
            self.OnStop()
            # assert wx.Sound.IsPlaying()==False
            self.slider.SetValue(self.endframe)
            self.UpdatePosition(self.endframe)
            return
        # work out where the slider should go
        newval=self.startpos+(now-self.starttime)
        self.slider.SetValue(newval)
        self.UpdatePosition(newval)

    def _removetempfiles(self):
        ConvertDialog._removetempfiles(self)
        for file in self.qcpfile, self.workingwavfile:
            if os.path.exists(file):
                os.remove(file)

    def OnOk(self, evt):
        self.OnStop()
        # make new data
        try:
            self.newfiledata=open(self.qcpfile, 'rb').read()
        except:
            self.newfiledata=None
        # now remove files
        self._removetempfiles()

        # use normal handler to quit dialog
        evt.Skip()

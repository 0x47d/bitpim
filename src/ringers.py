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

import wallpaper

###
###  Midi
###

class RingerView(guiwidgets.FileView):
    CURRENTFILEVERSION=2

    # this is only used to prevent the pubsub module
    # from being GC while any instance of this class exists
    __publisher=pubsub.Publisher

    
    def __init__(self, mainwindow, parent, id=-1):
        guiwidgets.FileView.__init__(self, mainwindow, parent, guihelper.getresourcefile("ringtone.xy"),
                                        guihelper.getresourcefile("ringtone-style.xy"), bottomsplit=400,
                                        rightsplit=200)
        self.SetColumns(["Name", "Length", "Origin", "Description"])
        self._data={'ringtone-index': {}}
        self.wildcard="Ringtone Files|*.mid;*.qcp"

        self.updateprofilevariables(self.mainwindow.phoneprofile)
        self.modified=False
        wx.EVT_IDLE(self, self.OnIdle)
        pubsub.subscribe(pubsub.REQUEST_RINGTONES, self, "OnListRequest")

    def GetIconSize(self):
        return (24,24)

    def updateprofilevariables(self, profile):
        self.maxlen=profile.MAX_RINGTONE_BASENAME_LENGTH
        self.filenamechars=profile.RINGTONE_FILENAME_CHARS

    def OnListRequest(self, msg=None):
        l=[self._data['ringtone-index'][x]['name'] for x in self._data['ringtone-index']]
        l.sort()
        pubsub.publish(pubsub.ALL_RINGTONES, l)

    def OnIdle(self, _):
        "Save out changed data"
        if self.modified:
            self.modified=False
            self.populatefs(self._data)
            self.OnListRequest() # broadcast changes

    def getdata(self,dict,want=guiwidgets.FileView.NONE):
        return self.genericgetdata(dict, want, self.mainwindow.ringerpath, 'ringtone', 'ringtone-index')

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
            self.thedir=self.mainwindow.ringerpath
            if os.path.splitext(file)[1]=='.mid':
                target=self.getshortenedbasename(file, 'mid')
                if target==None: return # user didn't want to
                f=open(file, "rb")
                contents=f.read()
                f.close()
                f=open(target, "wb")
                f.write(contents)
                f.close()
            else:
                # ::TODO:: warn if not on Windows
                target=self.getshortenedbasename(file, 'qcp')
                if target==None: return # user didn't want to
                qcpdata=bpaudio.converttoqcp(file)
                f=open(target, "wb")
                f.write(qcpdata)
                f.close()
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

    def GetItemImage(self, item):
        image=wx.Image(guihelper.getresourcefile('ringer.png'))
        return image

    def GetItemSizedBitmap(self, item, width, height):
        img=self.GetItemImage(item)
        if width!=img.GetWidth() or height!=img.GetHeight():
            if guihelper.IsMSWindows():
                bg=None # transparent
            elif guihelper.IsGtk():
                # we can't use transparent as the list control gets very confused on Linux
                # it also returns background as grey and foreground as black even though
                # the window is drawn with a white background.  So we give up and hard code
                # white
                bg="ffffff"
            elif guihelper.IsMac():
                # use background colour
                bg=self.GetBackgroundColour()
                bg="%02x%02x%02x" % (bg.Red(), bg.Green(), bg.Blue())
            bitmap=wallpaper.ScaleImageIntoBitmap(img, width, height, bgcolor=bg)
        else:
            bitmap=img.ConvertToBitmap()
        return bitmap

    def GetItemValue(self, item, col):
        if col=='Name':
            return item['name']
        elif col=='Length':
            return item['filelen']
        elif col=='Origin':
            return item.get('origin', "")
        elif col=='Description':
            return item['description']
        assert False, "unknown column"

    def GetImage(self, file):
        """Gets the named image

        @return: (wxImage, filesize)
        """
        image=wx.Image(guihelper.getresourcefile('ringer.png'))
        return image, int(os.stat(guihelper.getresourcefile('ringer.png')).st_size)

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
        newitems=[]
        existing=self.GetAllItems()
        keys=dict['ringtone-index'].keys()
        keys.sort()
        for i in keys:
            # ignore ones we don't have a file for
            entry=dict['ringtone-index'][i]
            filename=os.path.join(self.mainwindow.ringerpath, entry['name'])
            if not os.path.isfile(filename):
                print "no file for",entry['name']
                continue
            filelen=int(os.stat(filename).st_size)
            newentry={}
            # Look through existing to see if we already have an entry for this
            for k in existing:
                if entry['name']==k['name']:
                    newentry.update(k)
                    break
            # fill in new entry
            newentry.update(newentry)
            newentry['rt-index']=i
            newentry['name']=entry['name']
            newentry['filelen']=filelen
            newentry['file']=filename
            if os.path.splitext(entry['name'])[1]=='.qcp':
                newentry['length']="2 seconds :-)"
                newentry['description']="PureVoice file"
            else:
                newentry['length']="1 second :-)"
                newentry['description']="Midi file"
            newentry['origin']=entry.get('origin','ringers')
            newitems.append(newentry)
        self.SetItems(newitems)

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

### BITPIM
###
### Copyright (C) 2003-2004 Roger Binns <rogerb@rogerbinns.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"Deals with wallpaper and related views"

# standard modules
import os
import sys
import cStringIO

# wx modules
import wx

# my modules
import guiwidgets
import brewcompressedimage
import guihelper
import common
import helpids
import pubsub

###
###  Wallpaper pane
###

class WallpaperView(guiwidgets.FileView):
    CURRENTFILEVERSION=2
    ID_DELETEFILE=2
    ID_IGNOREFILE=3

    # this is only used to prevent the pubsub module
    # from being GC while any instance of this class exists
    __publisher=pubsub.Publisher

    _bitmaptypemapping={
        # the extensions we use and corresponding wx types
        'bmp': wx.BITMAP_TYPE_BMP,
        'jpg': wx.BITMAP_TYPE_JPEG,
        'png': wx.BITMAP_TYPE_PNG,
        }
    def __init__(self, mainwindow, parent):
        guiwidgets.FileView.__init__(self, mainwindow, parent, guihelper.getresourcefile("wallpaper.xy"),
                                        guihelper.getresourcefile("wallpaper-style.xy"), bottomsplit=200,
                                        rightsplit=200)
        self.SetColumns(["Name", "Size", "Bytes", "Origin"])
        wx.FileSystem_AddHandler(BPFSHandler(self))
        self._data={'wallpaper-index': {}}
        self.wildcard="Image files|*.bmp;*.jpg;*.jpeg;*.png;*.gif;*.pnm;*.tiff;*.ico;*.bci"
        self.updateprofilevariables(self.mainwindow.phoneprofile)

        self.addfilemenu.Insert(1,guihelper.ID_FV_PASTE, "Paste")
        wx.EVT_MENU(self.addfilemenu, guihelper.ID_FV_PASTE, self.OnPaste)
        self.modified=False
        wx.EVT_IDLE(self, self.OnIdle)
        pubsub.subscribe(self.OnListRequest, pubsub.REQUEST_WALLPAPERS)
        pubsub.subscribe(self.OnPhoneModelChanged, pubsub.PHONE_MODEL_CHANGED)

    def OnPhoneModelChanged(self, msg):
        phonemodule=msg.data
        self.updateprofilevariables(phonemodule.Profile)
        self.OnRefresh()

    def updateprofilevariables(self, profile):
        self.usewidth=profile.WALLPAPER_WIDTH
        self.useheight=profile.WALLPAPER_HEIGHT
        self.maxlen=profile.MAX_WALLPAPER_BASENAME_LENGTH
        self.filenamechars=profile.WALLPAPER_FILENAME_CHARS
        self.convertextension=profile.WALLPAPER_CONVERT_FORMAT
        self.convertwxbitmaptype=self._bitmaptypemapping[self.convertextension.lower()]
        if hasattr(profile,"OVERSIZE_PERCENTAGE"):
            self.woversize_percentage=profile.OVERSIZE_PERCENTAGE
            self.hoversize_percentage=profile.OVERSIZE_PERCENTAGE
        else:
            self.woversize_percentage=120
            self.hoversize_percentage=120
        
    def OnListRequest(self, msg=None):
        l=[self._data['wallpaper-index'][x]['name'] for x in self._data['wallpaper-index']]
        l.sort()
        pubsub.publish(pubsub.ALL_WALLPAPERS, l)

    def OnIdle(self, _):
        "Save out changed data"
        if self.modified:
            self.modified=False
            self.populatefs(self._data)
            self.OnListRequest() # broadcast changes

    def isBCI(self, filename):
        """Returns True if the file is a Brew Compressed Image"""
        # is it a bci file?
        f=open(filename, "rb")
        four=f.read(4)
        f.close()
        if four=="BCI\x00":
            return True
        return False


    def getdata(self,dict,want=guiwidgets.FileView.NONE):
        return self.genericgetdata(dict, want, self.mainwindow.wallpaperpath, 'wallpapers', 'wallpaper-index')

    def RemoveFromIndex(self, names):
        for name in names:
            wp=self._data['wallpaper-index']
            for k in wp.keys():
                if wp[k]['name']==name:
                    del wp[k]
                    self.modified=True

    def GetItemImage(self, item):
        file=item['file']
        if self.isBCI(file):
            image=brewcompressedimage.getimage(brewcompressedimage.FileInputStream(file))
        else:
            if file.endswith(".mp4"):
                image=wx.Image(guihelper.getresourcefile('wallpaper.png'))
                # Need to find a more appropriate graphic
            else:
                image=wx.Image(file)
        return image

    def GetItemSizedBitmap(self, item, width, height):
        if __debug__: print item
        img=self.GetItemImage(item)
        if __debug__: print width, height
        if __debug__: print img.GetWidth(), img.GetHeight()
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
            bitmap=ScaleImageIntoBitmap(img, width, height, bgcolor=bg)
        else:
            bitmap=img.ConvertToBitmap()
        return bitmap

    def GetItemValue(self, item, col):
        if col=='Name':
            return item['name']
        elif col=='Size':
            img=self.GetItemImage(item)
            item['size']=img.GetWidth(), img.GetHeight()
            return '%d x %d' % item['size']
        elif col=='Bytes':
            return int(os.stat(item['file']).st_size)
        elif col=='Origin':
            return item.get('origin', "")
        assert False, "unknown column"

    def GetItemValueForSorting(self, item, col):
        if col=='Size':
            w,h=item['size']
            return w*h
        return self.GetItemValue(item, col) 

    def GetImage(self, file):
        """Gets the named image

        @return: (wxImage, filesize)
        """
        file,cons = self.GetImageConstructionInformation(file)
        
        return cons(file), int(os.stat(file).st_size)

    # This function exists because of the constraints of the HTML
    # filesystem stuff.  The previous code was reading in the file to
    # a wx.Image, saving it as a PNG to disk (wx.Bitmap.SaveFile
    # doesn't have save to memory implemented), reading it back from
    # disk and supplying it to the HTML code.  Needless to say that
    # involves unnecessary conversions and gets slower with larger
    # images. We supply the info so that callers can make the minimum
    # number of conversions possible
    
    def GetImageConstructionInformation(self, file):
        """Gets information for constructing an Image from the file

        @return: (filename to use, function to call that returns wxImage)
        """
        file=os.path.join(self.mainwindow.wallpaperpath, file)

        if file.endswith(".mp4") or not os.path.isfile(file):
            return guihelper.getresourcefile('wallpaper.png'), wx.Image
        if self.isBCI(file):
            return file, lambda name: brewcompressedimage.getimage(brewcompressedimage.FileInputStream(file))
        return file, wx.Image
        
    def updateindex(self, index):
        if index!=self._data['wallpaper-index']:
            self._data['wallpaper-index']=index.copy()
            self.modified=True
        
    def populate(self, dict):
        if self._data['wallpaper-index']!=dict['wallpaper-index']:
            self._data['wallpaper-index']=dict['wallpaper-index'].copy()
            self.modified=True
        newitems=[]
        existing=self.GetAllItems()
        keys=dict['wallpaper-index'].keys()
        keys.sort()
        for k in keys:
            entry=dict['wallpaper-index'][k]
            filename=os.path.join(self.mainwindow.wallpaperpath, entry['name'])
            if not os.path.exists(filename):
                if __debug__: print "no file for wallpaper",entry['name']
                continue
            newentry={}
            # look through existing to see if we already have a match
            for i in existing:
                if entry['name']==i['name']:
                    newentry.update(i)
                    break
            # fill in newentry
            newentry.update(entry)
            newentry['wp-index']=k
            newentry['file']=filename
            newitems.append(newentry)
        self.SetItems(newitems)
                    
    def OnPaste(self, _=None):
        do=wx.BitmapDataObject()
        wx.TheClipboard.Open()
        success=wx.TheClipboard.GetData(do)
        wx.TheClipboard.Close()
        if not success:
            wx.MessageBox("There isn't an image in the clipboard", "Error")
            return
        # work out a name for it
        self.thedir=self.mainwindow.wallpaperpath
        for i in range(255):
            name="clipboard"+`i`+".bmp"
            if not os.path.exists(os.path.join(self.thedir, name)):
                break
        self.OnAddImage(wx.ImageFromBitmap(do.GetBitmap()), name)

    def AddToIndex(self, file):
        for i in self._data['wallpaper-index']:
            if self._data['wallpaper-index'][i]['name']==file:
                return
        keys=self._data['wallpaper-index'].keys()
        idx=10000
        while idx in keys:
            idx+=1
        self._data['wallpaper-index'][idx]={'name': file}
        self.modified=True

    def OnAddFiles(self, filenames):
        for file in filenames:
            self.thedir=self.mainwindow.wallpaperpath
            # special handling for BCI files
            if self.isBCI(file):
                target=os.path.join(self.thedir, os.path.basename(file).lower())
                src=open(file, "rb")
                dest=open(target, "wb")
                dest.write(src.read())
                dest.close()
                src.close()
                self.AddToIndex(os.path.basename(file).lower())
                continue
            img=wx.Image(file)
            if not img.Ok():
                dlg=wx.MessageDialog(self, "Failed to understand the image in '"+file+"'",
                                    "Image not understood", style=wx.OK|wx.ICON_ERROR)
                dlg.ShowModal()
                continue
            self.OnAddImage(img,file,refresh=False)
        self.OnRefresh()


    def OnAddImage(self, img, file, refresh=True):
        target=self.getshortenedbasename(file, self.convertextension)
        if target==None: return # user didn't want to
        obj=img
        # if image is more than 20% bigger or 60% smaller than screen, resize
        if img.GetWidth()>self.usewidth*self.woversize_percentage/100 or \
           img.GetHeight()>self.useheight*self.hoversize_percentage/100 or \
           img.GetWidth()<self.usewidth*60/100 or \
           img.GetHeight()<self.useheight*60/100:
            obj=ScaleImageIntoBitmap(obj, self.usewidth, self.useheight, "FFFFFF") # white background ::TODO:: something more intelligent

        # ensure in wxImage, not wxBitmap
        try:
            theimg=wx.ImageFromBitmap(obj)
        except TypeError:
            theimg=obj
        # ensure highest quality if saving as jpeg
        theimg.SetOptionInt("quality", 100)
        if not theimg.SaveFile(target, self.convertwxbitmaptype):
            os.remove(target)
            dlg=wx.MessageDialog(self, "Failed to convert the image in '"+file+"'",
                                "Image not converted", style=wx.OK|wx.ICON_ERROR)
            dlg.ShowModal()
            return

        self.AddToIndex(os.path.basename(target))
        if refresh:
            self.OnRefresh()

    def populatefs(self, dict):
        self.thedir=self.mainwindow.wallpaperpath
        return self.genericpopulatefs(dict, 'wallpapers', 'wallpaper-index', self.CURRENTFILEVERSION)

    def getfromfs(self, result):
        self.thedir=self.mainwindow.wallpaperpath
        return self.genericgetfromfs(result, None, 'wallpaper-index', self.CURRENTFILEVERSION)

    def versionupgrade(self, dict, version):
        """Upgrade old data format read from disk

        @param dict:  The dict that was read in
        @param version: version number of the data on disk
        """

        # version 0 to 1 upgrade
        if version==0:
            version=1  # they are the same

        # 1 to 2 etc
        if version==1:
            print "converting to version 2"
            version=2
            d={}
            input=dict.get('wallpaper-index', {})
            for i in input:
                d[i]={'name': input[i]}
            dict['wallpaper-index']=d
        return dict


def ScaleImageIntoBitmap(img, usewidth, useheight, bgcolor=None):
    """Scales the image and returns a bitmap

    @param usewidth: the width of the new image
    @param useheight: the height of the new image
    @param bgcolor: the background colour as a string ("ff0000" is red etc).  If this
                    is none then the background is made transparent"""
    bitmap=wx.EmptyBitmap(usewidth, useheight)
    mdc=wx.MemoryDC()
    mdc.SelectObject(bitmap)
    # scale the source. 
    sfactorw=usewidth*1.0/img.GetWidth()
    sfactorh=useheight*1.0/img.GetHeight()
    sfactor=min(sfactorw,sfactorh) # preserve aspect ratio
    newwidth=int(img.GetWidth()*sfactor/1.0)
    newheight=int(img.GetHeight()*sfactor/1.0)

    img.Rescale(newwidth, newheight)
    # deal with bgcolor/transparency
    if bgcolor is not None:
        transparent=None
        assert len(bgcolor)==6
        red=int(bgcolor[0:2],16)
        green=int(bgcolor[2:4],16)
        blue=int(bgcolor[4:6],16)
        mdc.SetBackground(wx.TheBrushList.FindOrCreateBrush(wx.Colour(red,green,blue), wx.SOLID))
    else:
        transparent=wx.Colour(*(img.FindFirstUnusedColour()[1:]))
        mdc.SetBackground(wx.TheBrushList.FindOrCreateBrush(transparent, wx.SOLID))
    mdc.Clear()
    mdc.SelectObject(bitmap)
    # figure where to place image to centre it
    posx=usewidth-(usewidth+newwidth)/2
    posy=useheight-(useheight+newheight)/2
    # draw the image
    mdc.DrawBitmap(img.ConvertToBitmap(), posx, posy, True)
    # clean up
    mdc.SelectObject(wx.NullBitmap)
    # deal with transparency
    if transparent is not None:
            mask=wx.MaskColour(bitmap, transparent)
            bitmap.SetMask(mask)
    return bitmap

###
### Virtual filesystem where the images etc come from for the HTML stuff
###

class BPFSHandler(wx.FileSystemHandler):

    def __init__(self, wallpapermanager):
        wx.FileSystemHandler.__init__(self)
        self.wpm=wallpapermanager

    def CanOpen(self, location):
        proto=self.GetProtocol(location)
        if proto=="bpimage" or proto=="bpuserimage":
            print "handling url",location
            return True
        return False

    def OpenFile(self,filesystem,location):
        res=self._OpenFile(filesystem,location)
        if res is not None:
            res.thisown=False # work around bug in wxPython 2.5.2.7
        return res

    def _OpenFile(self, filesystem, location):
        proto=self.GetProtocol(location)
        r=self.GetRightLocation(location)
        params=r.split(';')
        r=params[0]
        params=params[1:]
        p={}
        for param in params:
            x=param.find('=')
            key=param[:x]
            value=param[x+1:]
            if key=='width' or key=='height':
                p[key]=int(value)
            else:
                p[key]=value
        if proto=="bpimage":
            return self.OpenBPImageFile(location, r, **p)
        elif proto=="bpuserimage":
            return self.OpenBPUserImageFile(location, r, **p)
        return None

    def OpenBPUserImageFile(self, location, name, **kwargs):
        file,cons=self.wpm.GetImageConstructionInformation(name)
        if cons == wx.Image:
            return BPFSImageFile(self, location, file, **kwargs)
        return BPFSImageFile(self, location, img=cons(file), **kwargs)

    def OpenBPImageFile(self, location, name, **kwargs):
        f=guihelper.getresourcefile(name)
        if not os.path.isfile(f):
            print f,"doesn't exist"
            return None
        return BPFSImageFile(self, location, name=f, **kwargs)

class BPFSImageFile(wx.FSFile):
    """Handles image files

    All files are internally converted to PNG
    """

    def __init__(self, fshandler, location, name=None, img=None, width=-1, height=-1, bgcolor=None):
        self.fshandler=fshandler
        self.location=location

        # special fast path if we aren't resizing or converting image
        if img is None and width<0 and height<0 and \
               (name.endswith(".bmp") or name.endswith(".jpg") or name.endswith(".png")):
            wx.FSFile.__init__(self, wx.InputStream(open(name, "rb")), location, "image/"+name[-3:], "", wx.DateTime_Now())
            return
            
        if img is None:
            img=wx.Image(name)

        if width>0 and height>0:
            b=ScaleImageIntoBitmap(img, width, height, bgcolor)
        else:
            b=img.ConvertToBitmap()
        
        f=common.gettempfilename("png")
        if not b.SaveFile(f, wx.BITMAP_TYPE_PNG):
            raise Exception, "Saving to png failed"

        file=open(f, "rb")
        data=file.read()
        file.close()
        del file
        os.remove(f)

        s=wx.InputStream(cStringIO.StringIO(data))
        
        wx.FSFile.__init__(self, s, location, "image/png", "", wx.DateTime_Now())


class StringInputStream(wx.InputStream):

    def __init__(self, data):
        f=cStringIO.StringIO(data)
        wx.InputStream.__init__(self,f)

    
        

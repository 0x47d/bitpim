### BITPIM
###
### Copyright (C) 2003 Roger Binns <rogerb@rogerbinns.com>
###
### This software is under the Artistic license.
### Please see the accompanying LICENSE file
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

class WallpaperView(guiwidgets.FileViewNew):
    CURRENTFILEVERSION=2
    ID_DELETEFILE=2
    ID_IGNOREFILE=3

    # this is only used to prevent the pubsub module
    # from being GC while any instance of this class exists
    __publisher=pubsub.Publisher
    
    def __init__(self, mainwindow, parent):
        guiwidgets.FileViewNew.__init__(self, mainwindow, parent, guihelper.getresourcefile("wallpaper.xy"),
                                        guihelper.getresourcefile("wallpaper-style.xy"), bottomsplit=200,
                                        rightsplit=200)
        self.SetColumns(["Name", "Size", "Bytes", "Origin"])
        wx.FileSystem_AddHandler(BPFSHandler(self))
        self._data={'wallpaper-index': {}}
        self.wildcard="Image files|*.bmp;*.jpg;*.jpeg;*.png;*.gif;*.pnm;*.tiff;*.ico;*.bci"
        self.usewidth=self.mainwindow.phoneprofile.WALLPAPER_WIDTH
        self.useheight=self.mainwindow.phoneprofile.WALLPAPER_HEIGHT

        self.addfilemenu.Insert(1,guihelper.ID_FV_PASTE, "Paste")
        wx.EVT_MENU(self.addfilemenu, guihelper.ID_FV_PASTE, self.OnPaste)
        self.modified=False
        wx.EVT_IDLE(self, self.OnIdle)
        pubsub.subscribe(pubsub.REQUEST_WALLPAPERS, self, "OnListRequest")
        pubsub.subscribe(pubsub.PHONE_MODEL_CHANGED, self, "OnPhoneModelChanged")

    def OnPhoneModelChanged(self, msg):
        phonemodule=msg.data
        self.usewidth=phonemodule.Profile.WALLPAPER_WIDTH
        self.useheight=phonemodule.Profile.WALLPAPER_HEIGHT
        self.OnRefresh()
        
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
            image=wx.Image(file)
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
            return item['origin']
        assert False, "unknown column"
            

    def GetImage(self, file):
        """Gets the named image

        @return: (wxImage, filesize)
        """
        file=os.path.join(self.mainwindow.wallpaperpath, file)
        if self.isBCI(file):
            image=brewcompressedimage.getimage(brewcompressedimage.FileInputStream(file))
        else:
            image=wx.Image(file)
        # we use int to force the long to an int (longs print out with a trailing L which looks ugly)
        return image, int(os.stat(file).st_size)

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
                print "no file for wallpaper",entry['name']
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

    def OnAddFile(self, file):
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
            self.OnRefresh()
            return
        img=wx.Image(file)
        if not img.Ok():
            dlg=wx.MessageDialog(self, "Failed to understand the image in '"+file+"'",
                                "Image not understood", style=wx.OK|wx.ICON_ERROR)
            dlg.ShowModal()
            return
        self.OnAddImage(img,file)



    def OnAddImage(self, img, file):
        # Everything else is converted to BMP
        target=self.getshortenedbasename(file, 'bmp')
        if target==None: return # user didn't want to
        obj=img
        # if image is more than 20% bigger or 60% smaller than screen, resize
        if img.GetWidth()>self.usewidth*120/100 or \
           img.GetHeight()>self.useheight*120/100 or \
           img.GetWidth()<self.usewidth*60/100 or \
           img.GetHeight()<self.useheight*60/100:
            obj=ScaleImageIntoBitmap(obj, self.usewidth, self.useheight, "FFFFFF") # white background ::TODO:: something more intelligent
            
        if not obj.SaveFile(target, wx.BITMAP_TYPE_BMP):
            os.remove(target)
            dlg=wx.MessageDialog(self, "Failed to convert the image in '"+file+"'",
                                "Image not converted", style=wx.OK|wx.ICON_ERROR)
            dlg.ShowModal()
            return

        self.AddToIndex(os.path.basename(target))
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
        return common.exceptionwrap(self._OpenFile)(filesystem,location)

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
        try:
            image,_=self.wpm.GetImage(name)
        except IOError:
            return self.OpenBPImageFile(location, "wallpaper.png", **kwargs)
        return BPFSImageFile(self, location, img=image, **kwargs)

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

    
        

### BITPIM
###
### Copyright (C) 2003-2005 Roger Binns <rogerb@rogerbinns.com>
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
import random

# wx modules
import wx

# my modules
import guiwidgets
import brewcompressedimage
import guihelper
import common
import helpids
import pubsub
import aggregatedisplay
import fileinfo

###
###  Wallpaper pane
###

class DisplayItem(guiwidgets.FileViewDisplayItem):

    datakey="wallpaper-index"
    datatype="Image"  # this is used in the tooltip
        
thewallpapermanager=None

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

    organizetypes=("Image Type", "Origin", "File Size") # Image Size
    

    def __init__(self, mainwindow, parent):
        global thewallpapermanager
        thewallpapermanager=self
        self.mainwindow=mainwindow
        self.usewidth=10
        self.useheight=10
        wx.FileSystem_AddHandler(BPFSHandler(self))
        self._data={'wallpaper-index': {}}
        self.updateprofilevariables(self.mainwindow.phoneprofile)

        self.organizemenu=wx.Menu()
        guiwidgets.FileView.__init__(self, mainwindow, parent, "wallpaper-watermark")

        self.wildcard="Image files|*.bmp;*.jpg;*.jpeg;*.png;*.gif;*.pnm;*.tiff;*.ico;*.bci"


        self.bgmenu.Insert(1,guihelper.ID_FV_PASTE, "Paste")
        wx.EVT_MENU(self.bgmenu, guihelper.ID_FV_PASTE, self.OnPaste)

        self.organizeinfo={}

        for k in self.organizetypes:
            id=wx.NewId()
            self.organizemenu.AppendRadioItem(id, k)
            wx.EVT_MENU(self, id, self.OrganizeChange)
            self.organizeinfo[id]=getattr(self, "organizeby_"+k.replace(" ",""))
            
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

    def OrganizeChange(self, evt):
        evt.GetEventObject().Check(evt.GetId(), True)
        self.OnRefresh()

    def GetSections(self):
        # get all the items
        items=[DisplayItem(self, key, self.mainwindow.wallpaperpath) for key in self._data['wallpaper-index']]
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
                    sh.itemsize=(self.usewidth+120, self.useheight+DisplayItem.PADDING*2)
                    for item in items:
                        item.thumbnailsize=self.usewidth, self.useheight
                    # sort items by name
                    items=[(item.name.lower(), item) for item in items]
                    items.sort()
                    items=[item for name,item in items]
                    self.sections.append( (sh, items) )
                return [sh for sh,items in self.sections]
        assert False, "Can't get here"

    def GetItemSize(self, sectionnumber, sectionheader):
        return sectionheader.itemsize

    def GetItemsFromSection(self, sectionnumber, sectionheader):
        return self.sections[sectionnumber][1]

    def organizeby_ImageType(self, items):
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
            

    def isBCI(self, filename):
        """Returns True if the file is a Brew Compressed Image"""
        # is it a bci file?
        return open(filename, "rb").read(4)=="BCI\x00"

    def getdata(self,dict,want=guiwidgets.FileView.NONE):
        return self.genericgetdata(dict, want, self.mainwindow.wallpaperpath, 'wallpapers', 'wallpaper-index')

    def RemoveFromIndex(self, names):
        for name in names:
            wp=self._data['wallpaper-index']
            for k in wp.keys():
                if wp[k]['name']==name:
                    del wp[k]
                    self.modified=True

    def GetItemThumbnail(self, name, width, height):
        img,_=self.GetImage(name)
        if width!=img.GetWidth() or height!=img.GetHeight():
            # scale the image. 
            sfactorw=float(width)/img.GetWidth()
            sfactorh=float(height)/img.GetHeight()
            sfactor=min(sfactorw,sfactorh) # preserve aspect ratio
            newwidth=int(img.GetWidth()*sfactor)
            newheight=int(img.GetHeight()*sfactor)
            img.Rescale(newwidth, newheight)
        bitmap=img.ConvertToBitmap()
        return bitmap

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

    def GetFileInfo(self, filename):
        return fileinfo.identify_imagefile(filename)

    def GetImageStatInformation(self, file):
        """Returns the statinfo for file"""
        file=os.path.join(self.mainwindow.wallpaperpath, file)
        return statinfo(file)
        
    def updateindex(self, index):
        if index!=self._data['wallpaper-index']:
            self._data['wallpaper-index']=index.copy()
            self.modified=True
        
    def populate(self, dict):
        if self._data['wallpaper-index']!=dict['wallpaper-index']:
            self._data['wallpaper-index']=dict['wallpaper-index'].copy()
            self.modified=True
        self.OnRefresh()
                    
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
                open(target, "wb").write(open(file, "rb").read())
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

    OnAddFiles=guihelper.BusyWrapper(OnAddFiles)

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
        # if a bmp, use 8 bit+palette if necessary
        if self.convertwxbitmaptype:
            if theimg.ComputeHistogram(wx.ImageHistogram())<=236: # quantize only does 236 or less
                theimg.SetOptionInt(wx.IMAGE_OPTION_BMP_FORMAT, wx.BMP_8BPP)
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

class WallpaperPreview(wx.PyWindow):

    def __init__(self, parent, image=None, id=1, size=wx.DefaultSize, pos=wx.DefaultPosition, style=0):
        wx.PyWindow.__init__(self, parent, id=id, size=size, pos=pos, style=style|wx.FULL_REPAINT_ON_RESIZE)
        self.bg=wx.Brush(parent.GetBackgroundColour())
        self._bufbmp=None
        
        wx.EVT_ERASE_BACKGROUND(self, lambda evt: None)
        wx.EVT_PAINT(self, self.OnPaint)

        self.SetImage(image)

    def SetImage(self, name):
        if name is None:
            self.theimage=None
        else:
            self.theimage, _=thewallpapermanager.GetImage(name)
        self.thesizedbitmap=None
        self.Refresh(False)

    def OnPaint(self, _):
        sz=self.GetClientSize()
        if self._bufbmp is None or sz.width>self._bufbmp.GetWidth() or sz.height>self._bufbmp.GetHeight():
            self._bufbmp=wx.EmptyBitmap((sz.width+64)&~8, (sz.height+64)&~8)
        dc=wx.BufferedPaintDC(self, self._bufbmp)
        dc.SetBackground(self.bg)
        dc.Clear()
        if self.theimage is None: return
        # work out what size the scaled bitmap should be to retain its aspect ratio and fit within sz
        sfactorw=float(sz.width)/self.theimage.GetWidth()
        sfactorh=float(sz.height)/self.theimage.GetHeight()
        sfactor=min(sfactorw,sfactorh)
        newwidth=int(self.theimage.GetWidth()*sfactor)
        newheight=int(self.theimage.GetHeight()*sfactor)
        if self.thesizedbitmap is None or self.thesizedbitmap.GetWidth()!=newwidth or \
           self.thesizedbitmap.GetHeight()!=newheight:
            self.thesizedbitmap=self.theimage.Scale(newwidth, newheight).ConvertToBitmap()
        dc.DrawBitmap(self.thesizedbitmap, sz.width/2-newwidth/2, sz.height/2-newheight/2, True)
        
    


def ScaleImageIntoBitmap(img, usewidth, useheight, bgcolor=None, valign="center"):
    """Scales the image and returns a bitmap

    @param usewidth: the width of the new image
    @param useheight: the height of the new image
    @param bgcolor: the background colour as a string ("ff0000" is red etc).  If this
                    is none then the background is made transparent"""
    if bgcolor is None:
        bitmap=wx.EmptyBitmap(usewidth, useheight, 24) # have to use 24 bit for transparent background
    else:
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
    if valign in ("top", "clip"):
        posy=0
    elif valign=="center":
        posy=useheight-(useheight+newheight)/2
    else:
        assert False, "bad valign "+valign
        posy=0
    # draw the image
    mdc.DrawBitmap(img.ConvertToBitmap(), posx, posy, True)
    # clean up
    mdc.SelectObject(wx.NullBitmap)
    # deal with transparency
    if transparent is not None:
            mask=wx.Mask(bitmap, transparent)
            bitmap.SetMask(mask)
    if valign=="clip" and newheight!=useheight:
        return bitmap.GetSubBitmap( (0,0,usewidth,newheight) )
    return bitmap

###
### Virtual filesystem where the images etc come from for the HTML stuff
###

statinfo=common.statinfo

class BPFSHandler(wx.FileSystemHandler):

    CACHELOWWATER=80
    CACHEHIGHWATER=100

    def __init__(self, wallpapermanager):
        wx.FileSystemHandler.__init__(self)
        self.wpm=wallpapermanager
        self.cache={}

    def _GetCache(self, location, statinfo):
        """Return the cached item, or None

        Note that the location value includes the filename and the parameters such as width/height
        """
        if statinfo is None:
            print "bad location",location
            return None
        return self.cache.get( (location, statinfo), None)

    def _AddCache(self, location, statinfo, value):
        "Add the item to the cache"
        # we also prune it down in size if necessary
        if len(self.cache)>=self.CACHEHIGHWATER:
            print "BPFSHandler cache flush"
            # random replacement - almost as good as LRU ...
            while len(self.cache)>self.CACHELOWWATER:
                del self.cache[random.choice(self.cache.keys())]
        self.cache[(location, statinfo)]=value

    def CanOpen(self, location):

        # The call to self.GetProtocol causes an exception if the
        # location starts with a pathname!  This typically happens
        # when the help file is opened.  So we work around that bug
        # with this quick check.
        
        if location.startswith("/"):
            return False
        proto=self.GetProtocol(location)
        if proto=="bpimage" or proto=="bpuserimage":
            return True
        return False

    def OpenFile(self,filesystem,location):
        try:
            res=self._OpenFile(filesystem,location)
        except:
            res=None
            print "Exception in getting image file - you can't do that!"
            print common.formatexception()
        if res is not None:
            # we have to seek the file object back to the begining and make a new
            # wx.FSFile each time as wxPython doesn't do the reference counting
            # correctly
            res[0].seek(0)
            args=(wx.InputStream(res[0]),)+res[1:]
            res=wx.FSFile(*args)
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
            key=str(param[:x])
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
        si=self.wpm.GetImageStatInformation(name)
        res=self._GetCache(location, si)
        if res is not None: return res
        file,cons=self.wpm.GetImageConstructionInformation(name)
        if cons == wx.Image:
            res=BPFSImageFile(self, location, file, **kwargs)
        else:
            res=BPFSImageFile(self, location, img=cons(file), **kwargs)
        self._AddCache(location, si, res)
        return res

    def OpenBPImageFile(self, location, name, **kwargs):
        f=guihelper.getresourcefile(name)
        if not os.path.isfile(f):
            print f,"doesn't exist"
            return None
        si=statinfo(f)
        res=self._GetCache(location, si)
        if res is not None: return res
        res=BPFSImageFile(self, location, name=f, **kwargs)
        self._AddCache(location, si, res)
        return res

def BPFSImageFile(fshandler, location, name=None, img=None, width=-1, height=-1, valign="center", bgcolor=None):
    """Handles image files

    If we have to do any conversion on the file then we return PNG
    data.  This used to be a class derived from wx.FSFile, but due to
    various wxPython bugs it instead returns the parameters to make a
    wx.FSFile since a new one has to be made every time.
    """
        # special fast path if we aren't resizing or converting image
    if img is None and width<0 and height<0:
        mime=guihelper.getwxmimetype(name)
        # wxPython 2.5.3 has a new bug and fails to read bmp files returned as a stream
        if mime not in (None, "image/x-bmp"):
            return (open(name, "rb"), location, mime, "", wx.DateTime_Now())

    if img is None:
        img=wx.Image(name)

    if width>0 and height>0:
        b=ScaleImageIntoBitmap(img, width, height, bgcolor, valign)
    else:
        b=img.ConvertToBitmap()

    f=common.gettempfilename("png")
    if not b.SaveFile(f, wx.BITMAP_TYPE_PNG):
        raise Exception, "Saving to png failed"

    data=open(f, "rb").read()
    os.remove(f)

    return (cStringIO.StringIO(data), location, "image/png", "", wx.DateTime_Now())

    
class ImageCropSelect(wx.ScrolledWindow):

    def __init__(self, parent, image, previewwindow=None, id=1, resultsize=(100,100), size=wx.DefaultSize, pos=wx.DefaultPosition, style=0):
        wx.ScrolledWindow.__init__(self, parent, id=id, size=size, pos=pos, style=style|wx.FULL_REPAINT_ON_RESIZE)
        self.previewwindow=previewwindow
        self.bg=wx.Brush(parent.GetBackgroundColour())
        self._bufbmp=None

        self.anchors=None
        
        wx.EVT_ERASE_BACKGROUND(self, lambda evt: None)
        wx.EVT_PAINT(self, self.OnPaint)

        self.image=image
        self.setresultsize(resultsize)

        # cursors for outside, inside, on selection, pressing bad mouse button
        self.cursors=[wx.StockCursor(c) for c in (wx.CURSOR_ARROW, wx.CURSOR_HAND, wx.CURSOR_SIZING, wx.CURSOR_NO_ENTRY)]
        self.clickpoint=None 
        wx.EVT_MOTION(self, self.OnMotion)
        wx.EVT_LEFT_DOWN(self, self.OnLeftDown)
        wx.EVT_LEFT_UP(self, self.OnLeftUp)

    def SetPreviewWindow(self, previewwindow):
        self.previewwindow=previewwindow

    def OnPaint(self, _):
        sz=self.thebmp.GetWidth(), self.thebmp.GetHeight()
        sz2=self.GetClientSize()
        sz=max(sz[0],sz2[0])+32,max(sz[1],sz2[1])+32
        if self._bufbmp is None or self._bufbmp.GetWidth()<sz[0] or self._bufbmp.GetHeight()<sz[1]:
            self._bufbmp=wx.EmptyBitmap((sz[0]+64)&~8, (sz[1]+64)&~8)
        dc=wx.BufferedPaintDC(self, self._bufbmp)
        dc.DrawBitmap(self.thebmp, 0, 0, False)
        # draw bounding box next
        l,t,r,b=self.anchors
        points=(l,t), (r,t), (r,b), (l,b)
        dc.DrawLines( points+(points[0],) )
        for x,y in points:
            dc.DrawRectangle(x-5, y-5, 10, 10)

    OUTSIDE=0
    INSIDE=1
    HANDLE_LT=2
    HANDLE_RT=3
    HANDLE_RB=4
    HANDLE_LB=5
            
    def _hittest(self, evt):
        l,t,r,b=self.anchors
        within=lambda x,y,l,t,r,b:  l<=x<=r and t<=y<=b
        x,y=self.CalcUnscrolledPosition(evt.GetX(), evt.GetY())
        for i,(ptx,pty) in enumerate(((l,t), (r,t), (r,b), (l,b))):
            if within(x,y,ptx-5, pty-5, ptx+5,pty+5):
                return self.HANDLE_LT+i
        if within(x,y,l,t,r,b):
            return self.INSIDE
        return self.OUTSIDE
            
    def OnMotion(self, evt):
        if evt.Dragging():
            return self.OnMotionDragging(evt)
        self.UpdateCursor(evt)

    def UpdateCursor(self, evt):
        ht=self._hittest(evt)
        self.SetCursor(self.cursors[min(2,ht)])

    def OnMotionDragging(self, evt):
        if not evt.LeftIsDown() or self.clickpoint is None:
            self.SetCursor(self.cursors[3])
            return
        xx,yy=self.CalcUnscrolledPosition(evt.GetX(), evt.GetY())
        deltax=xx-self.origevtpos[0]
        deltay=yy-self.origevtpos[1]

        if self.clickpoint==self.INSIDE:
            newanchors=self.origanchors[0]+deltax, self.origanchors[1]+deltay, \
                        self.origanchors[2]+deltax, self.origanchors[3]+deltay
            iw=self.dimensions[0]
            ih=self.dimensions[1]
            # would box be out of bounds?
            if newanchors[0]<0:
                newanchors=0,newanchors[1], self.origanchors[2]-self.origanchors[0], newanchors[3]
            if newanchors[1]<0:
                newanchors=newanchors[0], 0, newanchors[2], self.origanchors[3]-self.origanchors[1]
            if newanchors[2]>iw:
                newanchors=iw-(self.origanchors[2]-self.origanchors[0]),newanchors[1],iw, newanchors[3]
            if newanchors[3]>ih:
                newanchors=newanchors[0],ih-(self.origanchors[3]-self.origanchors[1]), newanchors[2],ih
            self.anchors=newanchors
            self.Refresh(False)
            self.updatepreview()
            return
        # work out how to do this with left top and then expand code
        if self.clickpoint==self.HANDLE_LT:
            aa=0,1,-1,-1
        elif self.clickpoint==self.HANDLE_RT:
            aa=2,1,+1,-1
        elif self.clickpoint==self.HANDLE_RB:
            aa=2,3,+1,+1
        elif self.clickpoint==self.LB:
            aa=0,3,-1,+1
        else:
            assert False, "can't get here"
            
        na=[self.origanchors[0],self.origanchors[1],self.origanchors[2],self.origanchors[3]]
        na[aa[0]]=na[aa[0]]+deltax
        na[aa[1]]=na[aa[1]]+deltay
        neww=na[2]-na[0]
        newh=na[3]-na[1]
        ar=float(neww)/newh
        if ar<self.aspectratio:
            na[aa[0]]=na[aa[0]]+(self.aspectratio*newh-neww)*aa[2]
        elif ar>self.aspectratio:
            na[aa[1]]=na[aa[1]]+(neww/self.aspectratio-newh)*aa[3]
            
        # ignore if image would be smaller than 10 pixels in any direction
        if neww<10 or newh<10:
            return
        # if any point is off screen, we need to fix things up
        if na[0]<0 or na[1]<0 or na[2]>self.dimensions[0] or na[3]>self.dimensions[1]:
            print "offscreen fixup not written yet"
            return

        # work out aspect ratio
        self.anchors=na
        self.Refresh(False)
        self.updatepreview()
        return
            
        
    def OnLeftDown(self, evt):
        ht=self._hittest(evt)
        if ht==self.OUTSIDE:
            self.SetCursor(self.cursors[3])
            return
        self.clickpoint=ht
        xx,yy=self.CalcUnscrolledPosition(evt.GetX(), evt.GetY())
        self.origevtpos=xx,yy
        self.origanchors=self.anchors
        
    def OnLeftUp(self, evt):
        self.clickpoint=None
        self.UpdateCursor(evt)

    def setresultsize(self, (w,h)):
        self.resultsize=w,h
        self.aspectratio=ratio=float(w)/h
        imgratio=float(self.image.GetWidth())/self.image.GetHeight()

        neww=self.image.GetWidth()
        newh=self.image.GetHeight()
        if imgratio<ratio:
            neww*=ratio/imgratio
        elif imgratio>ratio:
            newh*=imgratio/ratio

        # ensure a minimum size
        neww=max(neww, 50)
        newh=max(newh, 50)

        # update anchors if never set
        if self.anchors==None:
            self.anchors=0.1 * neww, 0.1 * newh, 0.9 * neww, 0.9 * newh

        self.dimensions=neww,newh

        dc=wx.MemoryDC()
        self.thebmp=wx.EmptyBitmap(neww, newh)
        dc.SelectObject(self.thebmp)
        dc.SetBackground(self.bg)
        dc.Clear()
        dc.DrawBitmap(self.image.ConvertToBitmap(), neww/2-self.image.GetWidth()/2, newh/2-self.image.GetHeight()/2, True)
        dc.SelectObject(wx.NullBitmap)
        self.SetVirtualSize( (neww, newh) )
        self.SetScrollRate(1,1)

        # fixup anchors
        l,t,r,b=self.anchors
        l=min(neww-40, l)
        r=min(neww-10, r)
        if r-l<20: r=40
        t=min(newh-40, t)
        b=min(newh-10, b)
        if b-t<20: b=40
        aratio=float(r-l)/(b-t)
        if aratio<ratio:
            b=t+(r-l)/ratio
        elif aratio>ratio:
            r=l+(b-t)*ratio
        self.anchors=l,t,r,b

        self.updatepreview()
        self.Refresh(False)

    # updating the preview is expensive so it is done on demand.  We
    # tell the preview window there has been an update and it calls
    # back from its paint method
    def updatepreview(self):
        if self.previewwindow:
            self.previewwindow.SetUpdated(self.GetPreview)

    def GetPreview(self):
        l,t,r,b=self.anchors
        sub=self.thebmp.GetSubBitmap( (l,t,(r-l),(b-t)) )
        sub=sub.ConvertToImage()
        sub.Rescale(*self.resultsize)
        return sub.ConvertToBitmap()

class ImagePreview(wx.PyWindow):

    def __init__(self, parent):
        wx.PyWindow.__init__(self, parent)
        wx.EVT_ERASE_BACKGROUND(self, lambda evt: None)
        wx.EVT_PAINT(self, self.OnPaint)
        self.bmp=wx.EmptyBitmap(1,1)
        self.updater=None

    def SetUpdated(self, updater):
        self.updater=updater
        self.Refresh(True)

    def OnPaint(self, _):
        if self.updater is not None:
            self.bmp=self.updater()
            self.updater=None
        dc=wx.PaintDC(self)
        dc.DrawBitmap(self.bmp, 0, 0, False)


class ImagePreviewDialog(wx.Dialog):

    def __init__(self, parent, image, filename, phoneprofile):
        wx.Dialog.__init__(self, parent, -1, "Image Preview", style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER|wx.SYSTEM_MENU|wx.MAXIMIZE_BOX|wx.MINIMIZE_BOX)
        self.phoneprofile=phoneprofile
        self.filename=filename
        self.image=image

        vbsouter=wx.BoxSizer(wx.VERTICAL)

        hbs=wx.BoxSizer(wx.HORIZONTAL)
        self.cropselect=ImageCropSelect(self, image)
        hbs.Add(self.cropselect, 1, wx.ALL|wx.EXPAND, 5)

        vbs=wx.BoxSizer(wx.VERTICAL)
        vbs.Add(wx.StaticText(self, -1, "Preview"), 0, wx.ALL, 5)
        self.imagepreview=ImagePreview(self)
        self.cropselect.SetPreviewWindow(self.imagepreview)
        vbs.Add(self.imagepreview, 0, wx.ALL, 5)
        vbs.Add(wx.StaticText(self, -1, "Origin"), 0, wx.ALL, 5)
        self.originbox=wx.ListBox(self)
        vbs.Add(self.originbox, 0, wx.ALL|wx.EXPAND, 5)
        vbs.Add(wx.StaticText(self, -1, "Target"), 0, wx.ALL, 5)
        self.targetbox=wx.ListBox(self)
        vbs.Add(self.targetbox, 0, wx.ALL|wx.ALL, 5)
        hbs.Add(vbs, 0, wx.ALL, 5)

        vbsouter.Add(hbs, 1, wx.EXPAND|wx.ALL, 5)
        
        vbsouter.Add(wx.StaticLine(self, -1, style=wx.LI_HORIZONTAL), 0, wx.EXPAND|wx.ALL, 5)
        vbsouter.Add(self.CreateButtonSizer(wx.OK|wx.CANCEL|wx.HELP), 0, wx.ALIGN_CENTRE|wx.ALL, 5)

        wx.EVT_LISTBOX(self, self.originbox.GetId(), self.OnOriginSelect)
        wx.EVT_LISTBOX_DCLICK(self, self.originbox.GetId(), self.OnOriginSelect)

        wx.EVT_LISTBOX(self, self.targetbox.GetId(), self.OnTargetSelect)
        wx.EVT_LISTBOX_DCLICK(self, self.targetbox.GetId(), self.OnTargetSelect)

        self.originbox.Set(phoneprofile.GetImageOrigins().keys())
        self.originbox.SetSelection(0)
        self.OnOriginSelect(None)
        
        self.SetSizer(vbsouter)
        vbsouter.Fit(self)

    def OnOriginSelect(self, _):
        v=self.originbox.GetStringSelection()
        assert v is not None
        t=self.targetbox.GetStringSelection()
        self.targets=self.phoneprofile.GetTargetsForImageOrigin(v)
        keys=self.targets.keys()
        keys.sort()
        self.targetbox.Set(keys)
        if t in keys:
            self.targetbox.SetSelection(keys.index(t))
        else:
            self.targetbox.SetSelection(0)
        self.OnTargetSelect(None)

    def OnTargetSelect(self, _):
        v=self.targetbox.GetStringSelection()
        print "target is",v
        w,h=self.targets[v]['dimensions']
        self.imagepreview.SetSize( (w,h) )
        self.cropselect.setresultsize( (w, h) )
        sz=self.GetSizer()
        if sz is not None:
            # sizer doesn't autmatically size when we change preview size
            # so this forces that, as well as the repaint due to screen corruption
            sz.Layout()
            self.Refresh(True)
        


if __name__=='__main__':

    class FakeProfile:

        def GetImageOrigins(self):
            return {"images": None, "mms": None, "camera": None}

        def GetTargetsForImageOrigin(self, origin):
            return {"wallpaper": {'dimensions': (100,200)},
                    "photoid": {'dimensions': (100, 150)},
                    "outsidelcd": {'dimensions': (90,80)}}
    
    app=wx.PySimpleApp()
    dlg=ImagePreviewDialog(None, wx.Image("test.jpg"), "foobar.png", FakeProfile())
    dlg.ShowModal()
    
        
        

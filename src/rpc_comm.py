### BITPIM
###
### Copyright (C) 2006 Joe Pham <djpham@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Handle notification of comm ports availability using XMLRPC"""

import thread
import SimpleXMLRPCServer
import xmlrpclib

import wx

bpCOMM_NOTIFICATION_EVENT = wx.NewEventType()
COMM_NOTIFICATION_EVENT = wx.PyEventBinder(bpCOMM_NOTIFICATION_EVENT, 0)
default_port=5002

class CommNotificationEvent(wx.PyEvent):
    add=0
    remove=1
    def __init__(self):
        super(CommNotificationEvent, self).__init__()
        self.SetEventType=bpCOMM_NOTIFICATION_EVENT
        self.type=None
        self.comm=None

class CommNotification(object):
    def __init__(self, mainwindow):
        self.mw=mainwindow
        self.evt=CommNotificationEvent()

    def add(self, comm):
        # a new comm has just been added
        self.evt.type=CommNotificationEvent.add
        if comm.startswith('/proc/bus/usb/'):
            # this is a Linux hotplug USB port, which may have many interfaces.
            # can't figure which one so scan for all ports.
            self.evt.comm=None
        else:
            self.evt.comm=comm
        self.mw.OnCommNotification(self.evt)
        return True

    def remove(self, comm):
        # a new comm has just been deleted
        if comm.startswith('/proc/bus/usb/'):
            # This is a Linux hotplug USB port, just ignore it
            return False
        self.evt.type=CommNotificationEvent.remove
        self.evt.comm=comm
        self.mw.OnCommNotification(self.evt)
        return True

def run_server(mainwindow, port):
    _comm_notification=CommNotification(mainwindow)
    SimpleXMLRPCServer.SimpleXMLRPCServer.allow_reuse_address=True
    _server=SimpleXMLRPCServer.SimpleXMLRPCServer(('localhost', port),
                                                  logRequests=False)
    _server.register_introspection_functions()
    _server.register_instance(_comm_notification)
    _server.serve_forever()

def start_server(mainwindow, port):
    thread.start_new_thread(run_server, (mainwindow, port))

def notify_comm_status(status, comm, config):
    try:
        global default_port
        _client=xmlrpclib.ServerProxy('http://localhost:%d'%config.ReadInt('rpcport',
                                                                           default_port))
        if status=='add':
            _client.add(comm)
        else:
            _client.remove(comm)
    except:
        if __debug__:
            raise

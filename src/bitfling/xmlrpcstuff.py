#!/usr/bin/env python

# This file is triple licensed as the BitPim License, and the Python
# and BSD licenses.  It incorporates code from both the standard
# Python library and M2Crypto, which was then modified to work
# properly.

# My own implementation of xmlrpc (both server and client)

# It has a silly name so it doesn't class with standard Python
# and library module names

# The standard Python implementation lacks any support for serving
# over SSL, dealing with authentication on the server side, having
# context for calls (and tying them in with the authentication),
# bounding the number of threads in use, checking certificates, not
# making a connection per call and who knows how many other
# deficiencies.


# Server design
#
# Main thread (which could be a daemon thread for the rest of the program)
# creates the listening socket, and starts the connection handler threads.
# They all sit in a loop.  They call accept, work on the lifetime of
# a connection, and when it closes go back to accept.  When they get a
# request, it is dumped into a queue for the main thread to deal with,
# who then dumps the results back into a queue for the connection thread.
# Consequently we get the benefits of threading for dealing with event
# stuff, but the actual request handling still seems single threaded.


TRACE=False


# standard modules
import threading
import Queue
import time
import sys
import BaseHTTPServer
import xmlrpclib
import base64
import httplib
import string
import urllib

# required add ons
import M2Crypto

# my modules
if TRACE: import guihelper # to format exceptions


class AuthenticationBad(Exception):
    pass

class XMLRPCRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):

    protocol_version="HTTP/1.1"

    def do_POST(self):
        """Handles the HTTP POST request.

        Attempts to interpret all HTTP POST requests as XML-RPC calls
        """

        try:
            # get arguments
            data = self.rfile.read(int(self.headers["content-length"]))
            # check the authentication
            cred=username=password=None
            try:
                cred=self.headers["Authorization"]
            except KeyError:
                pass
            if cred is not None:
                cred=cred.split(None, 1)
                if len(cred)!=2 or cred[0].lower()!="basic":
                    raise AuthenticationBad("Unknown authentication scheme "+`cred[0]`)
                username,password=base64.decodestring(cred[1]).split(":", 1)
                print "parsed auth to %s %s from %s" % (`username`, `password`, self.headers["Authorization"])
            response=self.server.processxmlrpcrequest(data, self.client_address, username, password)
        except AuthenticationBad:
            self.close_connection=True
            self.send_response(401, "Authentication required")
            self.send_header("WWW-Authenticate", "Basic realm=\"XMLRPC\"")
            self.end_headers()
            self.wfile.flush()
        except: # This should only happen if the module is buggy
            # internal error, report as HTTP server error
            if __debug__ and TRACE:
                print "error in handling xmlrpcrequest"
                print guihelper.formatexception()
            self.close_connection=True
            self.send_response(500, "Internal Error")
            self.end_headers()
            self.wfile.flush()
        else:
            # got a valid XML RPC response
            self.send_response(200)
            self.send_header("Content-type", "text/xml")
            self.send_header("Content-length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)
            self.wfile.flush()

    def finish(self):
        # do proper SSL shutdown sequence
        self.wfile.flush()
        self.request.set_shutdown(M2Crypto.SSL.SSL_RECEIVED_SHUTDOWN | M2Crypto.SSL.SSL_SENT_SHUTDOWN)
        self.request.close()


class MySSLConnection(M2Crypto.SSL.Connection):
    # add in our special sauce
    def flush(self):
        res=M2Crypto.m2.bio_flush(self.sockbio)
        # print "flush res is",res,"  bio pending bytes is",M2Crypto.m2.bio_ctrl_pending(self.sockbio)

    def makefile(self, mode="rb", bufsize="ignored"):
        if __debug__ and TRACE: print "%d: makefile %s" % (id(self), mode)
        if not hasattr(self, "_prior_makefile"):
            self._prior_makefile=M2Crypto.SSL.Connection.makefile(self, mode, bufsize)
        return self._prior_makefile
        


# TODOs for the server side
#
#  - use a derived SSL.Connection class where we can check whether we want the other end
#    before starting the SSL negotiations (to prevent a denial of service by the remote
#    end creating connections and not sending any data)
#  - include the peer certificate in the CMD_XMLRPC_REQUEST

class Server(threading.Thread):

    class Message:
        """A message between a connection thread and the server object, or vice versa"""
        # These are in the order things happen.  Logging happens all the time, and we
        # cycle XMLRPC requests and responses for the lifetime of a connection
        CMD_LOG=0                            # data is log message
        CMD_LOG_EXCEPTION=1                   # data is sys.exc_info()
        CMD_NEW_ACCEPT_REQUEST=2
        CMD_NEW_ACCEPT_RESPONSE=3
        CMD_NEW_CONNECTION_REQUEST=4
        CMD_NEW_CONNECTION_RESPONSE=5
        CMD_XMLRPC_REQUEST=6
        CMD_XMLRPC_RESPONSE=7
        CMD_CONNECTION_CLOSE=8

        
        def __init__(self, cmd, respondqueue=None, clientaddr=None, peercert=None, data=None):
            self.cmd=cmd
            self.respondqueue=respondqueue
            self.clientaddr=clientaddr
            self.peercert=peercert
            self.data=data

        def __repr__(self):
            d=`self.data`
            if len(d)>40:
                d=d[:40]
            str=`self.cmd`
            for i in dir(self):
                if i.startswith("CMD_") and getattr(self, i)==self.cmd:
                    str=i
                    break
            return "Message: cmd=%s data=%s" % (str, d)
    
    class ConnectionThread(threading.Thread):

        def __init__(self, server, listen, queue, name):
            """Constructor
            
            @param server: reference to server object
            @param listen: SSLConnection object that is in listening state
            @param queue:  the queue object to send messages to
            @param name: name of this thread"""
            threading.Thread.__init__(self)
            self.setDaemon(True)
            self.setName(name)
            self.responsequeue=Queue.Queue()
            self.server=server
            self.requestqueue=queue
            self.listen=listen
            self.reqhandlerclass=XMLRPCRequestHandler

        def log(self, str):
            now=time.time()
            t=time.localtime(now)
            timestr="&%d:%02d:%02d.%03d"  % ( t[3], t[4], t[5],  int((now-int(now))*1000))
            msg=Server.Message(Server.Message.CMD_LOG, data="%s: %s: %s" % (timestr, self.getName(), str))
            self.requestqueue.put(msg)

        def logexception(self, str, excinfo):
            self.log(str)
            msg=Server.Message(Server.Message.CMD_LOG_EXCEPTION, data=excinfo)
            self.requestqueue.put(msg)
                            
        def run(self):
            while not self.server.wantshutdown:
                if __debug__ and TRACE: print self.getName()+": About to call accept"
                try:
                    sock, peeraddr = self.listen.socket.accept()
                    msg=Server.Message(Server.Message.CMD_NEW_ACCEPT_REQUEST, self.responsequeue, peeraddr)
                    self.requestqueue.put(msg)
                    resp=self.responsequeue.get()
                    assert resp.cmd==resp.CMD_NEW_ACCEPT_RESPONSE
                    ok=resp.data
                    if not ok:
                        self.log("Connection from "+`peeraddr`+" not accepted")
                        sock.close()
                        continue
                    self.log("Connection from "+`peeraddr`+" accepted")
                    ssl = M2Crypto.SSL.Connection(self.server.sslcontext, sock)
                    ssl.addr = peeraddr
                    ssl.setup_ssl()
                    ssl.set_accept_state()
                    ssl.accept_ssl()
                    conn=ssl
                except:
                    self.logexception("Exception in accept", sys.exc_info())
                    continue
                if __debug__ and TRACE: print self.getName()+": SSL connection from "+`peeraddr`
                peercert=conn.get_peer_cert()
                msg=Server.Message(Server.Message.CMD_NEW_CONNECTION_REQUEST, self.responsequeue, peeraddr, peercert)
                self.requestqueue.put(msg)
                resp=self.responsequeue.get()
                assert resp.cmd==resp.CMD_NEW_CONNECTION_RESPONSE
                ok=resp.data
                if not ok:
                    self.log("SSL connection from "+`peeraddr`+" rejected")
                    conn.close()
                    continue
                self.log("SSL connection from "+`peeraddr`+" accepted")
                if __debug__ and TRACE: print self.getName()+": Setting timeout to "+`self.server.connectionidlebreak`
                conn.set_socket_read_timeout(M2Crypto.SSL.timeout(self.server.connectionidlebreak))
                self.reqhandlerclass(conn, peeraddr, self)
                if __debug__ and TRACE: print self.getName()+": Reqhandler returns - closing connection"
                msg=Server.Message(Server.Message.CMD_CONNECTION_CLOSE,  None, peeraddr, peercert)
                self.requestqueue.put(msg)
                self.log("Connection from "+`peeraddr`+" closed")
                try:
                    conn.close()
                except: # ignore exceptions as peer may have shut connection or who knows what else
                    pass
                conn=None

        def processxmlrpcrequest(self, data, client_addr, username, password):
            msg=Server.Message(Server.Message.CMD_XMLRPC_REQUEST, self.responsequeue, client_addr, data=(data, username, password))
            self.log("%s:%s req %s" % (username, password, `data`))
            self.requestqueue.put(msg)
            resp=self.responsequeue.get()
            assert resp.cmd==resp.CMD_XMLRPC_RESPONSE
            if hasattr(resp, "exception"):
                raise resp.exception
            return resp.data
            

    def __init__(self, host, port, sslcontext, connectionthreadcount=5, timecheck=60, connectionidlebreak=240):
        """Creates the listening thread and infrastructure.  Don't forget to call start() if you
        want anything to be processed!  You probably also want to call setDaemon().  Remember to
        load a certificate into the sslcontext.

        @param connectionthreadcount:  How many threads are being used.  If new connections
                            arrive while the existing threads are busy in connections, then they will be ignored
        @param timecheck:  How often shutdown requests are checked for in the main thread (only valid on Python 2.3+)
        @param connectionidlebreak: If an SSL connection is idle for this amount of time then it is closed
        """
        threading.Thread.__init__(self)
        self.setName("Threading SSL server controller for %s:%d" % (host, port))
        connection=MySSLConnection(sslcontext)
        if __debug__ and TRACE: print "Binding to host %s port %d" % (host, port)
        connection.bind( (host, port) )
        connection.listen(connectionthreadcount+5)
        self.sslcontext=sslcontext
        self.timecheck=timecheck
        self.connectionidlebreak=connectionidlebreak
        self.wantshutdown=False
        self.workqueue=Queue.Queue()
        self.threadlist=[]
        for count in range(connectionthreadcount):
            conthread=self.ConnectionThread(self, connection, self.workqueue, "SSL worker thread %d/%d" % (count+1, connectionthreadcount))
            conthread.start()
            self.threadlist.append(conthread)

    def shutdown(self):
        """Requests a shutdown of all threads"""
        self.wantshutdown=True

    def run23(self):
        while not self.wantshutdown:
            try:
                msg=self.workqueue.get(True, self.timecheck)
            except Queue.Empty:
                continue
            try:
                self.processmessage(msg)
            except:
                sys.excepthook(*sys.exc_info())
        
    def run22(self):
        while not self.wantshutdown:
            try:
                msg=self.workqueue.get(True)
            except Queue.Empty:
                continue
            try:
                self.processmessage(msg)
            except:
                sys.excepthook(*sys.exc_info())
                

    if sys.version_info>=(2,3):
        run=run23
    else:
        run=run22

    def processmessage(self, msg):
        if not isinstance(msg, Server.Message):
            self.OnUserMessage(msg)
            return
        if __debug__ and TRACE:
            if not msg.cmd in (msg.CMD_LOG, msg.CMD_LOG_EXCEPTION):
                print "Processing message "+`msg`
        resp=None
        if msg.cmd==msg.CMD_LOG:
            self.OnLog(msg.data)
            return
        elif msg.cmd==msg.CMD_LOG_EXCEPTION:
            self.OnLogException(msg.data)
            return
        elif msg.cmd==msg.CMD_NEW_ACCEPT_REQUEST:
            ok=self.OnNewAccept(msg.clientaddr)
            resp=Server.Message(Server.Message.CMD_NEW_ACCEPT_RESPONSE, data=ok)
        elif msg.cmd==msg.CMD_NEW_CONNECTION_REQUEST:
            ok=self.OnNewConnection(msg.clientaddr, msg.peercert)
            resp=Server.Message(Server.Message.CMD_NEW_CONNECTION_RESPONSE, data=ok)
        elif msg.cmd==msg.CMD_XMLRPC_REQUEST:
            data=self.OnXmlRpcRequest(* (msg.data+(msg.clientaddr, msg.peercert)))
            resp=Server.Message(Server.Message.CMD_XMLRPC_RESPONSE, data=data)
        elif msg.cmd==msg.CMD_CONNECTION_CLOSE:
            self.OnConnectionClose(msg.clientaddr, msg.peercert)
        else:
            assert False, "Unknown message command "+`msg.cmd`
            raise Exception("Internal processing error")
        if resp is not None:
            msg.respondqueue.put(resp)

    def OnLog(self, str):
        """Process a log message"""
        print str

    def OnLogException(self, exc):
        """Process an exception message"""
        print exc[:2]


    def OnNewAccept(self, clientaddr):
        """Decide if we accept a new new connection"""
        return True

    def OnNewConnection(self, clientaddr, clientcert):
        """Decide if a new connection is allowed once SSL is established"""
        return True

    def OnConnectionClose(self, clientaddr, clientcert):
        """Called when a connection closes"""
        if __debug__ and TRACE: print "Closed connection from "+`clientaddr`

    def OnUserMessage(self, msg):
        """Called when a message arrives in the workqueue"""

    def OnXmlRpcRequest(self, xmldata, username, password, clientaddr, clientcert):
        """Called when an XML-RPC requests arrives, but before the XML is parsed"""
        params, method = xmlrpclib.loads(xmldata)
        # call method
        try:
            response=self.OnMethodDispatch(method, params, username, password, clientaddr, clientcert)
            # wrap response in a singleton tuple
            response = (response,)
            response = xmlrpclib.dumps(response, methodresponse=1)
        except xmlrpclib.Fault, fault:
            response = xmlrpclib.dumps(fault)
        except:
            self.OnLog("Exception processing method "+`method`)
            self.OnLogException(sys.exc_info())
            # report exception back to server
            response = xmlrpclib.dumps(
                xmlrpclib.Fault(1, "%s:%s" % sys.exc_info()[:2])
                )

        return response            

    def OnMethodDispatch(self, method, params, username, password, clientaddr, clientcert):
        """Called once the XML-RPC request is parsed"""
        if __debug__ and TRACE: print "%s %s (user=%s, password=%s, client=%s)" % (method, `tuple(params)`, username, password, `clientaddr`)
        return True


class SSLConnection(httplib.HTTPConnection):

    def __init__(self, sslctx, host, port=None, strict=None, certverifier=None):
        httplib.HTTPConnection.__init__(self, host, port, strict)
        self.sslc_sslctx=sslctx
        self.certverifier=certverifier
        self.addrforverifier=(host, port)

    def connect(self):
        if __debug__ and TRACE: print "Connecting to %s:%s" % (self.host, self.port)
        httplib.HTTPConnection.connect(self)
        self.sock=MySSLConnection(self.sslc_sslctx, self.sock)
        self.sock.setblocking(True)
        self.sock.setup_ssl()
        self.sock.set_connect_state()
        self.sock.connect_ssl()
        if self.certverifier is not None:
            res=self.certverifier(self.addrforverifier, self.sock.get_peer_cert())
            if not res:
                self.realclose()
                raise Exception("Certificate not accepted")

    def close(self):
        if __debug__ and TRACE: print "close() ignored"

    def realclose(self):
        if __debug__ and TRACE: print "Closing connection to %s:%s" % (self.host, self.port)
        self.sock.close()
        self.sock=None

class SSLTransport(xmlrpclib.Transport):

    def __init__(self, uri, sslctx, certverifier):
        # xmlrpclib.Transport.__init__(self)
        self.sslt_sslctx=sslctx
        self.sslt_uri=uri
        _, rest=urllib.splittype(uri)
        host, _=urllib.splithost(rest)
        self.sslt_user_passwd, hpart=urllib.splituser(host)
        self.sslt_host, self.sslt_port = urllib.splitport(hpart)
        self.connection=None
        self.certverifier=certverifier

    def getconnection(self):
        if self.connection is not None:
            return self.connection
        self.connection=SSLConnection(self.sslt_sslctx, self.sslt_host, self.sslt_port, certverifier=self.certverifier)
        return self.connection

    def request(self, host, handler, request_body, verbose=0, retries=1):
        user_passwd=self.sslt_user_passwd
        _host=self.sslt_host

        h=self.getconnection()
        
        # What follows is as in xmlrpclib.Transport. (Except the authz bit.)
        h.putrequest("POST", "/RPC2", skip_host=True)

        # required by HTTP/1.1
        h.putheader("Host", _host)

        # required by XML-RPC
        h.putheader("User-Agent", self.user_agent)
        h.putheader("Content-Type", "text/xml")
        h.putheader("Content-Length", str(len(request_body)))

        # Authorisation.
        if user_passwd is not None:
            auth=string.strip(base64.encodestring(user_passwd))
            h.putheader('Authorization', 'Basic %s' % auth)

        h.endheaders()

        h.sock.flush()
        # body hasn't been sent, so we can retry without having problems
        # print "state is",h.sock.get_state()

        if request_body:
            h.send(request_body)

        response = h.getresponse()

        errcode, errmsg, headers = response.status, response.reason, response.msg

        if errcode != 200:
            self.connection.close()
            self.connection=None
            raise xmlrpclib.ProtocolError(
                host + handler,
                errcode, errmsg,
                headers
                )

        self.verbose = verbose
        return self.parse_response(response)
    

    def parse_response(self, response):
        p, u =self.getparser() # parser and unmarshaller
        # response.length could be None but only if there is no Content-Length header
        # which is a violation of the XML-RPC protocol
        p.feed(response.read(response.length))
        p.close()

        if response.will_close:
            self.connection.realclose()
            self.connection=None
        # ensure the response is closed by unsetting its fp.  We don't want to call
        # explicit close as that will close the socket down which we don't want
        response.fp=None
        

        return u.close()


class ServerProxy(xmlrpclib.ServerProxy):

    def __init__(self, uri, certverifier=None):
        sslcontext=M2Crypto.SSL.Context("sslv23")
        xmlrpclib.ServerProxy.__init__(self, uri, SSLTransport(uri, sslcontext, certverifier))
        

# ensure we are correctly set up for threading
import M2Crypto.threading
M2Crypto.threading.init()

        
if __name__=='__main__':
    if len(sys.argv)<2:
        print "You must supply arguments - one of"
        print "  server"
        print "  client"
        sys.exit(1)

    if sys.argv[1]=="server":
        ctx=M2Crypto.SSL.Context("sslv23")
        ctx.load_cert("file.pem")
        server=Server('localhost', 4433, ctx)
        server.setDaemon(True)
        server.start()

        time.sleep(1120)

    if sys.argv[1]=="client":
        server=ServerProxy("http://username:passwud@localhost:4433")

        print server.add(3,4)
        print server.add("one", "two")

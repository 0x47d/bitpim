#!/usr/bin/env python

# My own implementation of xmlrpc (both server and client)

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

# required add ons
import M2Crypto


TRACE=True

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
                username,password=base64.decodestring(cred[1].strip()).split(":", 1)
            response=self.server.processxmlrpcrequest(data, self.client_addr, username, password)
        except AuthenticationBad:
            self.close_connection=True
            self.send_response(401, "Authentication required")
            self.send_header("WWW-Authenticate", "Basic realm=\"XMLRPC\"")
            self.end_headers()
            self.wfile.flush()
        except: # This should only happen if the module is buggy
            # internal error, report as HTTP server error
            if __debug__ and TRACE: print "error in handling xmlrpcrequest"
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


# TODOs for the server side
#
#  - use a derived SSL.Connection class where we can check whether we want the other end
#    before starting the SSL negotiations (to prevent a denial of service by the remote
#    end creating connections and not sending any data)
#  - include the peer certificate in the CMD_XMLRPC_REQUEST

class Server(threading.Thread):

    class Message:
        CMD_NEW_CONNECTION_REQUEST=0
        CMD_NEW_CONNECTION_RESPONSE=1
        CMD_CONNECTION_CLOSE=5
        CMD_LOG=2
        CMD_XMLRPC_REQUEST=3
        CMD_XMLRPC_RESPONSE=4
        
        def __init__(self, cmd, respondqueue=None, clientaddr=None, peercert=None, data=None):
            self.cmd=cmd
            self.respondqueue=respondqueue
            self.clientaddr=clientaddr
            self.peercert=peercert
            self.data=data
    
    class ConnectionThread(threading.Thread):

        def __init__(self, server, listen, queue, name):
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
            timestr="%d:%02d:%02d.%03d"  % ( t[3], t[4], t[5],  int((now-int(now))*1000))
            msg=Server.Message(Server.Message.CMD_LOG, data="%s: %s: %s" % (timestr, self.getName(), str))
            self.requestqueue.put(msg)
                            
        def run(self):
            while not self.server.wantshutdown:
                if __debug__ and TRACE: print self.getName()+": About to call accept"
                try:
                    conn, peeraddr = self.listen.accept()
                except:
                    self.log("Exception in accept: %s:%s" % sys.exc_info()[:2])
                    continue
                if __debug__ and TRACE: print self.getName()+": Connection from "+`peeraddr`
                peercert=conn.get_peer_cert()
                msg=Server.Message(Server.Message.CMD_NEW_CONNECTION_REQUEST, self.responsequeue, peeraddr, peercert)
                self.requestqueue.put(msg)
                resp=self.responsequeue.get()
                assert resp.cmd==resp.CMD_NEW_CONNECTION_RESPONSE
                ok=resp.data
                if not ok:
                    self.log("Connection rejected")
                    conn.close()
                    continue
                self.log("Connection accepted")
                if __debug__ and TRACE: print self.getName()+": Setting timeout to "+`self.server.connectionidlebreak`
                conn.set_socket_read_timeout(M2Crypto.SSL.timeout(self.server.connectionidlebreak))
                self.reqhandlerclass(conn, peeraddr, self)
                msg=Server.Message(Server.Message.CMD_CONNECTION_CLOSE,  None, peeraddr, peercert)
                self.requestqueue.put(msg)
                conn=None

        def processxmlrpcrequest(self, data, client_addr, username, password):
            msg=Server.Message(Server.Message.CMD_XMLRPC_REQUEST, self.responsequeue, client_addr, data=(data, username, password))
            self.log("%s:%s req %80s" % (username, password, `data`))
            self.requestqueue.put(msg)
            resp=self.responsequeue.get()
            assert resp.cmd==resp.CMD_XMLRPC_RESPONSE
            if hasattr(resp, exception):
                raise resp.exception
            return resp.data
            

    def __init__(self, host, port, sslcontext=None, connectionthreadcount=5, timecheck=60, connectionidlebreak=240):
        """Creates the listening thread and infrastructure.  Don't forget to call start() if you
        want anything to be processed!  You probably also want to call setDaemon()

        @param connectionthreadcount:  How many threads are being used.  If new connections
                            arrive while the existing threads are busy in connections, then they will be ignored
        @param timecheck:  How often shutdown requests are checked for in the main thread (only valid on Python 2.3+)
        @param connectionidlebreak: If an SSL connection is idle for this amount of time then it is closed
        """
        threading.Thread.__init__(self)
        self.setName("Threading SSL server controller for %s:%d" % (host, port))
        if sslcontext is None:
            sslcontext=M2Crypto.SSL.Context("sslv3")
        connection=M2Crypto.SSL.Connection(sslcontext)
        if __debug__ and TRACE: print "Binding to host %s port %d" % (host, port)
        connection.bind( (host, port) )
        connection.listen(connectionthreadcount+5)
        self.timecheck=timecheck
        self.connectionidlebreak=connectionidlebreak
        self.wantshutdown=False
        self.workqueue=Queue.Queue()

        for count in range(connectionthreadcount):
            conthread=self.ConnectionThread(self, connection, self.workqueue, "SSL worker thread %d/%d" % (count+1, connectionthreadcount))
            conthread.start()

    def shutdown(self):
        """Requests a shutdown of all threads"""
        self.wantshutdown=True

    def run23(self):
        while not self.wantshutdown:
            try:
                msg=self.workqueue.get(True, self.timecheck)
            except Queue.Empty:
                continue
            self.processmessage(msg)
        
    def run22(self):
        while not self.wantshutdown:
            try:
                msg=self.workqueue.get(True)
            except Queue.Empty:
                continue
            self.processmessage(msg)

    if sys.version_info>=(2,3):
        run=run23
    else:
        run=run22

    def processmessage(self, msg):
        if __debug__ and TRACE:
            print "Processing message "+`msg`
        resp=None
        if msg.cmd==msg.CMD_LOG:
            self.OnLog(msg.data)
            return
        elif msg.cmd==msg.CMD_NEW_CONNECTION_REQUEST:
            ok=self.OnNewConnection(msg.clientaddr, msg.peercert)
            resp=Server.Message(Server.Message.CMD_NEW_CONNECTION_RESPONSE, data=ok)
        elif msg.cmd==msg.CMD_XMLRPC_REQUEST:
            data=self.OnXmlRpcRequest(* (msg.data+(msg.clientaddr, msg.peercert)))
            resp=Server.Message(Server.Message.CMD_XMLRPC_RESPONSE, data=data)
        else:
            assert False, "Unknown message command "+`msg.cmd`
            raise Exception("Internal processing error")
        if resp is not None:
            msg.responsequeue.put(resp)

    def OnLog(self, str):
        """Process a log message"""
        print str

    def OnNewConnection(self, clientaddr, clientcert):
        """Decide if a new connection is allowed"""
        return True

    def OnXmlRpcRequest(self, xmldata, username, password, clientaddr, clientcert):
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
            # report exception back to server
            response = xmlrpclib.dumps(
                xmlrpclib.Fault(1, "%s:%s" % sys.exc_info()[:2])
                )

        return response            

    def OnMethodDispatch(self, method, params, username, password, clientaddr, clientcert):
        if __debug__ and TRACE: print "%s %s (user=%s, password=%s, client=%s)" % (method, `tuple(params)`, username, password, `clientaddr`)
        return True


class SSLConnection(httplib.HTTPConnection):

    def __init__(self, sslctx, host, port=None, strict=None):
        httplib.HTTPConnection.__init__(self, host, port, strict)
        self.sslc_sslctx=sslctx

    def connect(self):
        if __debug__ and TRACE: print "Connecting to %s:%s" % (self.host, self.port)
        httplib.HTTPConnection.connect(self)
        self.sock=M2Crypto.SSL.Connection(self.sslc_sslctx, self.sock)
        self.sock.setup_ssl()
        self.sock.set_connect_state()
        self.sock.connect_ssl()
        

class SSLTransport(xmlrpclib.Transport):

    def __init__(self, uri, sslctx):
        # xmlrpclib.Transport.__init__(self)
        self.sslt_sslctx=sslctx
        self.sslt_uri=uri
        self.sslt_user_passwd, self.sslt_host_port = M2Crypto.m2urllib.splituser(uri)
        self.sslt_host, self.sslt_port = M2Crypto.m2urllib.splitport(self.sslt_host_port)
        self.connection=None

    def getconnection(self):
        if self.connection is not None:
            return self.connection
        self.connection=SSLConnection(self.sslt_sslctx, self.sslt_host, self.sslt_port)
        return self.connection

    def request(self, host, handler, request_body, verbose=0):
        user_passwd=self.sslt_user_passwd
        _host=self.sslt_host

        h=self.getconnection()
        
        # What follows is as in xmlrpclib.Transport. (Except the authz bit.)
        h.putrequest("POST", handler)

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

        if request_body:
            h.send(request_body)

        errcode, errmsg, headers = h.getreply()

        if errcode != 200:
            raise xmlrpclib.ProtocolError(
                host + handler,
                errcode, errmsg,
                headers
                )

        self.verbose = verbose
        return self.parse_response(h.getfile())


class ServerProxy(xmlrpclib.ServerProxy):

    def __init__(self, uri, allow_none=True):
        sslcontext=M2Crypto.SSL.Context("sslv3")
        xmlrpclib.ServerProxy.__init__(self, uri, SSLTransport(uri, sslcontext), allow_none=allow_none)
        
        
if __name__=='__main__':
    import M2Crypto.threading
    M2Crypto.threading.init()
    if len(sys.argv)<2:
        print "You must supply arguments - one of"
        print "  server"
        print "  client"
        sys.exit(1)

    if sys.argv[1]=="server":
        server=Server('localhost', 4433)
        server.setDaemon(True)
        server.start()

        time.sleep(120)

    if sys.argv[1]=="client":
        server=ServerProxy("http://username:passwud@localhost:4433")

        print server.add(3,4)
        print server.add("one", "two")

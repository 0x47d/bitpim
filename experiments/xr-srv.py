# M2Crypto
from M2Crypto import DH, SSL
import SimpleXMLRPCServer
import sys

class SSLSimpleXMLRPCRequestHandler(SimpleXMLRPCServer.SimpleXMLRPCRequestHandler):

    def finish(self):
        # do proper SSL shutdown sequence
        self.request.set_shutdown(SSL.SSL_RECEIVED_SHUTDOWN | SSL.SSL_SENT_SHUTDOWN)
        self.request.close()


if sys.version>="2.3":
    class SSLSimpleXMLRPCServer(SSL.SSLServer, SimpleXMLRPCServer.SimpleXMLRPCDispatcher):
        def __init__(self, addr, ssl_context ):
            self.logRequests=True
            SimpleXMLRPCServer.SimpleXMLRPCDispatcher.__init__(self)
            SSL.SSLServer.__init__(self, addr, SimpleXMLRPCServer.SimpleXMLRPCRequestHandler, ssl_context)
else:
    class SSLSimpleXMLRPCServer(SSL.SSLServer):
        def __init__(self, addr, ssl_context ):
            self.logRequests=True
            self.instance=None
            self.funcs={}
            SSL.SSLServer.__init__(self, addr, SimpleXMLRPCServer.SimpleXMLRPCRequestHandler, ssl_context)
        def register_instance(self, instance):
            self.instance = instance

        def register_function(self, function, name = None):
            if name is None:
                name = function.__name__
            self.funcs[name] = function


context=SSL.Context("sslv23")
context.load_cert("host.pem", "privkey.pem")

server = SSLSimpleXMLRPCServer(("localhost", 1234), context)

def add(a,b): return a+b

server.register_function(add)

server.serve_forever()

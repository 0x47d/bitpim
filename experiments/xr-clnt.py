from M2Crypto.m2xmlrpclib import Server, SSL_Transport

# have to edit M2Crypto.httpslib.py, line 100, change to this
#         if (sys.version[:3] == '2.2' and sys.version_info[2] > 1) or sys.version>"2.2":
# (put existing if in parentheses, add sys.version>"2.2"

server=Server("https://username:password@localhost:1234", SSL_Transport())


print server.add(1,2)
print type(server.add(1,2))
print dir(server)
print server.add("one", "two")

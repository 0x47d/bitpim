PYTHONVER=python2.3
INCLUDEDIR=/System/Library/Frameworks/Python.framework/Versions/2.3/include/$PYTHONVER

swig -version 2>&1 | grep Version

swig -python -I/usr/local/include libusb.i

gcc -Wall -O2  -bundle -undefined suppress -flat_namespace -I $INCLUDEDIR -I /usr/local/include -o _libusb.so libusb_wrap.c -L/usr/local/lib -lusb -framework Python


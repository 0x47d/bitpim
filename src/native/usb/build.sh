PYTHONVER=python2.2
INCLUDEDIR=/usr/include/$PYTHONVER
LIBDIR=/usr/lib/$PYTHONVER/config

swig -python -I/usr/include libusb.i

gcc -Wall -g -shared  -I $INCLUDEDIR -L $LIBDIR -o _libusb.so libusb_wrap.c -lusb -l$PYTHONVER

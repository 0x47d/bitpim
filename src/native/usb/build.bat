set USBDIR=c:\projects\libusb-win32-bin-0.1.7.9
set SWIG="c:\program files\swig-1.3.19\swig.exe"
set PYTHONDIR=c:\python23

%SWIG% -I%USBDIR%\include -python -no_default libusb.i

gcc -Wall -g -shared -I %USBDIR%\include -L %USBDIR%\lib\gcc -I %PYTHONDIR%\include -L %PYTHONDIR%\libs -o _libusb.dll libusb_wrap.c -lusb -lpython23

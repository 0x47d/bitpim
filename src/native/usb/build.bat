set USBDIR=c:\progra~1\libusb-win32-0.1.8.0
set SWIG="c:\program files\swig-1.3.20\swig.exe"
set PYTHONDIR=c:\python23
set PYTHONLIB=python23

@rem Create MinGW compatible Python library if appropriate
@if exist %PYTHONDIR%\lib%PYTHONLIB%.a goto libok
@REM this only works on NT/XP
pexports %systemroot%\system32\%PYTHONLIB%.dll > %PYTHONLIB%.def
dlltool --dllname %PYTHONLIB%.dll --def %PYTHONLIB%.def --output-lib %PYTHONDIR%\libs\lib%PYTHONLIB%.a
del %PYTHONLIB%.def

:libok

%SWIG% -I%USBDIR%\include -python -modern -no_default libusb.i

gcc -Wall -g -shared -I %USBDIR%\include -L %USBDIR%\lib\gcc -I %PYTHONDIR%\include -L %PYTHONDIR%\libs -o _libusb.dll libusb_wrap.c -lusb -l%PYTHONLIB%

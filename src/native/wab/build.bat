@rem standalone binary
@rem g++ -g -Wall -I c:\projects\fixedwab -o wab.exe wab.cpp
@rem swig version
"c:\program files\swig-1.3.19\swig.exe" -python -c++ -o pywabimpl.cpp pywab.swg
g++ -g -Wall -Wl,--enable-auto-import -shared -L c:\python23\libs -I c:\python23\include -I c:\projects\fixedwab -o _pywabimpl.dll pywabimpl.cpp wab.cpp -lpython23
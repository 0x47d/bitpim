# Microsoft Developer Studio Generated NMAKE File, Based on vx8500.dsp
!IF "$(CFG)" == ""
CFG=vx8500 - Win32 Release
!ENDIF 

!IF "$(CFG)" != "vx8500 - Win32 Release" && "$(CFG)" != "vx8500 - Win32 Debug"
!MESSAGE Invalid configuration "$(CFG)" specified.
!MESSAGE You can specify a configuration when running NMAKE
!MESSAGE by defining the macro CFG on the command line. For example:
!MESSAGE 
!MESSAGE NMAKE /f "vx8500.mak" CFG="vx8500 - Win32 Debug"
!MESSAGE 
!MESSAGE Possible choices for configuration are:
!MESSAGE 
!MESSAGE "vx8500 - Win32 Release" (based on "Win32 (x86) Dynamic-Link Library")
!MESSAGE "vx8500 - Win32 Debug" (based on "Win32 (x86) Dynamic-Link Library")
!MESSAGE 
!ERROR An invalid configuration is specified.
!ENDIF 

!IF "$(OS)" == "Windows_NT"
NULL=
!ELSE 
NULL=nul
!ENDIF 

!IF  "$(CFG)" == "vx8500 - Win32 Release"

OUTDIR=.\Release
INTDIR=.\Release
# Begin Custom Macros
OutDir=.\Release
# End Custom Macros

ALL : "$(OUTDIR)\pyvx8500.dll"


CLEAN :
	-@erase "$(INTDIR)\vc60.idb"
	-@erase "$(INTDIR)\vx8500.obj"
	-@erase "$(OUTDIR)\pyvx8500.dll"
	-@erase "$(OUTDIR)\pyvx8500.exp"
	-@erase "$(OUTDIR)\pyvx8500.lib"

"$(OUTDIR)" :
    if not exist "$(OUTDIR)/$(NULL)" mkdir "$(OUTDIR)"

CPP=cl.exe
CPP_PROJ=/nologo /MD /W3 /GX /O2 /I "c:\Python23\include" /D "WIN32" /D "NDEBUG" /D "_WINDOWS" /D "_MBCS" /D "_USRDLL" /D "VX8500_EXPORTS" /Fp"$(INTDIR)\vx8500.pch" /YX /Fo"$(INTDIR)\\" /Fd"$(INTDIR)\\" /FD /c 

.c{$(INTDIR)}.obj::
   $(CPP) @<<
   $(CPP_PROJ) $< 
<<

.cpp{$(INTDIR)}.obj::
   $(CPP) @<<
   $(CPP_PROJ) $< 
<<

.cxx{$(INTDIR)}.obj::
   $(CPP) @<<
   $(CPP_PROJ) $< 
<<

.c{$(INTDIR)}.sbr::
   $(CPP) @<<
   $(CPP_PROJ) $< 
<<

.cpp{$(INTDIR)}.sbr::
   $(CPP) @<<
   $(CPP_PROJ) $< 
<<

.cxx{$(INTDIR)}.sbr::
   $(CPP) @<<
   $(CPP_PROJ) $< 
<<

MTL=midl.exe
MTL_PROJ=/nologo /D "NDEBUG" /mktyplib203 /win32 
RSC=rc.exe
BSC32=bscmake.exe
BSC32_FLAGS=/nologo /o"$(OUTDIR)\vx8500.bsc" 
BSC32_SBRS= \
	
LINK32=link.exe
LINK32_FLAGS=kernel32.lib user32.lib gdi32.lib winspool.lib comdlg32.lib advapi32.lib shell32.lib ole32.lib oleaut32.lib uuid.lib odbc32.lib odbccp32.lib python23.lib /nologo /dll /incremental:no /pdb:"$(OUTDIR)\pyvx8500.pdb" /machine:I386 /def:".\vx8500.def" /out:"$(OUTDIR)\pyvx8500.dll" /implib:"$(OUTDIR)\pyvx8500.lib" /libpath:"c:\Python23\Libs" 
DEF_FILE= \
	".\vx8500.def"
LINK32_OBJS= \
	"$(INTDIR)\vx8500.obj" \
	".\mencode.obj"

"$(OUTDIR)\pyvx8500.dll" : "$(OUTDIR)" $(DEF_FILE) $(LINK32_OBJS)
    $(LINK32) @<<
  $(LINK32_FLAGS) $(LINK32_OBJS)
<<

!ELSEIF  "$(CFG)" == "vx8500 - Win32 Debug"

OUTDIR=.\Debug
INTDIR=.\Debug
# Begin Custom Macros
OutDir=.\Debug
# End Custom Macros

ALL : "$(OUTDIR)\pyvx8500.dll"


CLEAN :
	-@erase "$(INTDIR)\vc60.idb"
	-@erase "$(INTDIR)\vc60.pdb"
	-@erase "$(INTDIR)\vx8500.obj"
	-@erase "$(OUTDIR)\pyvx8500.dll"
	-@erase "$(OUTDIR)\pyvx8500.exp"
	-@erase "$(OUTDIR)\pyvx8500.ilk"
	-@erase "$(OUTDIR)\pyvx8500.lib"
	-@erase "$(OUTDIR)\pyvx8500.pdb"

"$(OUTDIR)" :
    if not exist "$(OUTDIR)/$(NULL)" mkdir "$(OUTDIR)"

CPP=cl.exe
CPP_PROJ=/nologo /MTd /W3 /Gm /GX /ZI /Od /D "WIN32" /D "_DEBUG" /D "_WINDOWS" /D "_MBCS" /D "_USRDLL" /D "VX8500_EXPORTS" /Fp"$(INTDIR)\vx8500.pch" /YX /Fo"$(INTDIR)\\" /Fd"$(INTDIR)\\" /FD /GZ /c 

.c{$(INTDIR)}.obj::
   $(CPP) @<<
   $(CPP_PROJ) $< 
<<

.cpp{$(INTDIR)}.obj::
   $(CPP) @<<
   $(CPP_PROJ) $< 
<<

.cxx{$(INTDIR)}.obj::
   $(CPP) @<<
   $(CPP_PROJ) $< 
<<

.c{$(INTDIR)}.sbr::
   $(CPP) @<<
   $(CPP_PROJ) $< 
<<

.cpp{$(INTDIR)}.sbr::
   $(CPP) @<<
   $(CPP_PROJ) $< 
<<

.cxx{$(INTDIR)}.sbr::
   $(CPP) @<<
   $(CPP_PROJ) $< 
<<

MTL=midl.exe
MTL_PROJ=/nologo /D "_DEBUG" /mktyplib203 /win32 
RSC=rc.exe
BSC32=bscmake.exe
BSC32_FLAGS=/nologo /o"$(OUTDIR)\vx8500.bsc" 
BSC32_SBRS= \
	
LINK32=link.exe
LINK32_FLAGS=kernel32.lib user32.lib gdi32.lib winspool.lib comdlg32.lib advapi32.lib shell32.lib ole32.lib oleaut32.lib uuid.lib odbc32.lib odbccp32.lib python23.lib /nologo /dll /incremental:yes /pdb:"$(OUTDIR)\pyvx8500.pdb" /debug /machine:I386 /def:".\vx8500.def" /out:"$(OUTDIR)\pyvx8500.dll" /implib:"$(OUTDIR)\pyvx8500.lib" /pdbtype:sept /libpath:"c:\Python23\Libs" 
DEF_FILE= \
	".\vx8500.def"
LINK32_OBJS= \
	"$(INTDIR)\vx8500.obj" \
	".\mencode.obj"

"$(OUTDIR)\pyvx8500.dll" : "$(OUTDIR)" $(DEF_FILE) $(LINK32_OBJS)
    $(LINK32) @<<
  $(LINK32_FLAGS) $(LINK32_OBJS)
<<

!ENDIF 


!IF "$(NO_EXTERNAL_DEPS)" != "1"
!IF EXISTS("vx8500.dep")
!INCLUDE "vx8500.dep"
!ELSE 
!MESSAGE Warning: cannot find "vx8500.dep"
!ENDIF 
!ENDIF 


!IF "$(CFG)" == "vx8500 - Win32 Release" || "$(CFG)" == "vx8500 - Win32 Debug"
SOURCE=.\mencode.asm

!IF  "$(CFG)" == "vx8500 - Win32 Release"

InputPath=.\mencode.asm

".\mencode.obj" : $(SOURCE) "$(INTDIR)" "$(OUTDIR)"
	<<tempfile.bat 
	@echo off 
	c:\masm32\bin\ml.exe /c /Cx /coff "$(InputPath)"
<< 
	

!ELSEIF  "$(CFG)" == "vx8500 - Win32 Debug"

InputPath=.\mencode.asm

".\mencode.obj" : $(SOURCE) "$(INTDIR)" "$(OUTDIR)"
	<<tempfile.bat 
	@echo off 
	c:\masm32\bin\ml.exe /c /Cx /coff "$(InputPath)"
<< 
	

!ENDIF 

SOURCE=.\vx8500.c

"$(INTDIR)\vx8500.obj" : $(SOURCE) "$(INTDIR)"



!ENDIF 


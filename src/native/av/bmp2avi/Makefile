### BITPIM
###
### Copyright (C) 2005 Joe Pham <djpham@netzero.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

ifeq ($(PLATFORM),)
$(error PLATFORM not defined.  Valid PLATFORM are windows, linux, mac)
endif

CXXFLAGS=
LDFLAGS=

ifeq ($(PLATFORM), windows)
EXT=exe
# define this for cygwin/mingw
CXXFLAGS+=-mno-cygwin
LDFLAGS+=-mno-cygwin
endif

ifeq ($(PLATFORM), linux)
EXT=lbin
endif

ifeq ($(PLATFORM), mac)
EXT=mbin
# define this for non-Intel(Big Endian) plaforms
CXXFLAGS+=-D__BIG_ENDIAN__
endif

ifeq ($(EXT),)
$(error PLATFORM $(PLATFORM) is invalid.  Valid PLATFORM are windows, linux, mac)
endif

SRC=avi_file.cxx bmp_file.cxx b2a.cxx
OBJ=$(SRC:.cxx=.o)
EXE=bmp2avi.$(EXT)
CXX=g++

all: $(EXE)

$(EXE): $(OBJ)
	@echo Building for PLATFORM $(PLATFORM)
	$(CXX) $(LDFLAGS) -o $@ $(OBJ) $(LOADLIBES) $(LDLIBS)

%.o: %.cxx
	$(CXX) $(CPPFLAGS) -c $< $(CXXFLAGS)

o:	$(OBJ)

clean:
	rm -f $(EXE) $(OBJ) depend

depend:
	$(CXX) -MM $(CXXFLAGS) $(SRC) > depend

-include depend

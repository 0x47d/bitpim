# $Id$

# NOTE: This file is preprocessed and some substitutions made by makedist.py

# Leave out all the stripping nonsense which strips the python bytecode out
# of the main exe!
%define __os_install_post /usr/lib/rpm/brp-compress
# the debug stuff is left in since it strips all the shared libraries which
# is ok.  here is how to turn off debuginfo packages (and increase the rpm
# size by 33%)
# %define debug_package %{nil}

Summary: Interfaces with the phonebook, calendar, wallpaper of many CDMA phones
Name: %%RPMNAME%%
Version: %%RPMVERSION%%
Release: %%RELEASE%%
License: GNU GPL
Group: Utilities/Phone
URL: http://www.bitpim.org
Source0: %{name}-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-buildroot
AutoReqProv: no

%description
BitPim is a program that allows you to view and manipulate data on
many CDMA phones from LG, Samsung, Sanyo and other manufacturers. This
includes the PhoneBook, Calendar, WallPapers, RingTones (functionality
varies by phone) and the Filesystem for most Qualcomm CDMA chipset
based phones.

%prep
%setup -q

%build

%install
rm -rf $RPM_BUILD_ROOT
mkdir -p $RPM_BUILD_ROOT
tar xvf dist.tar -C $RPM_BUILD_ROOT

%clean
rm -rf $RPM_BUILD_ROOT

%files -f FILELIST
%defattr(-,root,root,-)

%doc



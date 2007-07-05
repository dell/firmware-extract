###################################################################
#
# WARNING
#
# These are all automatically replaced by the release script.
# START = Do not edit manually
%define major 1
%define minor 1
%define sub 3
%define extralevel %{nil}
%define rpm_release 3
%define release_name dell-repo-tools
%define release_version %{major}.%{minor}.%{sub}%{extralevel}
#
# END = Do not edit manually
#
###################################################################

# per fedora python packaging guidelines
%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

#disable empty debuginfo package
%define debug_package %{nil}

# SUSE 10 has a crazy distutils.cfg that specifies prefix=/usr/local
# have to override that.
%define suse_prefix %{nil}
%if %(test -e /etc/SuSE-release && echo 1 || echo 0)
%define suse_prefix --prefix=/usr
%endif

# Compat for RHEL3 build
%if %(test "%{dist}" == ".el3" && echo 1 || echo 0)
# needed for RHEL3 build, python-devel doesnt seem to Require: python in RHEL3
BuildRequires:  python
# override sitelib because this messes up on x86_64
%define python_sitelib %{_exec_prefix}/lib/python2.2/site-packages/
%endif

Name:           dell-repo-tools
Version:        %{release_version} 
Release:        %{rpm_release}%{?dist}
Summary:        Scripts to extract BIOS/Firmware from Dell Update Packages

Group:          Applications/System
# License is actually GPL/OSL dual license (GPL Compatible), but rpmlint complains
License:        GPL style
URL:            http://linux.dell.com/libsmbios/download/ 
Source0:        http://linux.dell.com/libsmbios/download/%{name}/%{name}-%{version}/%{name}-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

# This package is noarch for everything except RHEL3. Have to build arch
# specific pkgs for RHEL3
%if %(test "%{dist}" != ".el3" && echo 1 || echo 0)
BuildArch:      noarch
%endif

BuildRequires:  python-devel
Requires: libsmbios-bin unshield firmware-tools firmware-addon-dell

%description
placeholder


%prep
%setup -q


%build
%{__python} setup.py build


%install
rm -rf $RPM_BUILD_ROOT
%{__python} setup.py install -O1 --skip-build --root $RPM_BUILD_ROOT %{suse_prefix}

 
%clean
rm -rf $RPM_BUILD_ROOT


%files
%defattr(-,root,root,-)
%doc COPYING-GPL COPYING-OSL README
%{python_sitelib}/*
%{_datadir}/firmware/spec
%attr(0755,root,root) %{_bindir}/*


%changelog
* Mon Mar 12 2007 Michael E Brown <michael_e_brown at dell.com> - 1.2.0-1
- Fedora-compliant packaging changes.

# vim:noexpandtab:autoindent:tabstop=8:shiftwidth=8:filetype=make:nocindent:tw=0:

include Makefile-std

pkgconfdir = $(sysconfdir)/firmware/firmware.d/
pkgconf_DATA = pkg/dell-repo.conf

EXTRA_DIST += doc test COPYING-GPL COPYING-OSL

pkgpython_PYTHON = \
	dell_repo_tools/__init__.py 

REPLACE_VARS_ON_INSTALL= 

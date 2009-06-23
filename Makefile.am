# vim:noexpandtab:autoindent:tabstop=8:shiftwidth=8:filetype=make:nocindent:tw=0:

include Makefile-std

firmware_extract/__init__.py: firmware_extract/__init__.py.in
    cp -a $< $@ ;\
    perl -p -i -e 's|^__VERSION__\s*=.*|__VERSION__="$(RELEASE_VERSION)"|' $@ ;

pkgconfdir = $(sysconfdir)/firmware/firmware.d/
dist_pkgconf_DATA = pkg/firmware-extract.conf

EXTRA_DIST += COPYING-GPL COPYING-OSL
DISTCLEANFILES += firmware_extract/__init__.py  AUTHORS ChangeLog

pkgpython_PYTHON = \
	firmware_extract/__init__.py 	\
	firmware_extract/buildrpm.py	\
	firmware_extract/mockextract.py 

clidir = $(datadir)/firmware-tools/plugins/
cli_PYTHON = \
	ft-cli-plugin/extract_cmd.py	\
	ft-cli-plugin/buildpkg_cmd.py

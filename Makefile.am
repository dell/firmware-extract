# vim:noexpandtab:autoindent:tabstop=8:shiftwidth=8:filetype=make:nocindent:tw=0:

include Makefile-std

pkgconfdir = $(sysconfdir)/firmware/firmware.d/
dist_pkgconf_DATA = pkg/firmware-extract.conf

EXTRA_DIST += COPYING-GPL COPYING-OSL
DISTCLEANFILES += firmware_extract/__init__.py  AUTHORS ChangeLog

pkgpython_PYTHON = \
	firmware_extract/generated/__init__.py 	\
	firmware_extract/buildrpm.py	\
	firmware_extract/mockextract.py 

clidir = $(datadir)/firmware-tools/plugins/
cli_PYTHON = \
	ft-cli-plugin/extract_cmd.py	\
	ft-cli-plugin/buildpkg_cmd.py


__VERSION__=$(VERSION)
REPLACE_VARS+= __VERSION__
EXTRA_DIST += firmware_extract/__init__.py
DISTCLEANFILES +=   firmware_extract/generated/__init__.py
firmware_extract/generated/__init__.py: firmware_extract/__init__.py configure Makefile config.status
	mkdir -p $$(dirname $@) ||:
	cp $< $@
	for var in $(REPLACE_VARS)	;\
	do	\
		perl -p -i -e "s|^$$var\s*=.*|$$var=\"$${!var}\"|"  $@;\
	done

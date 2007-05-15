#!/usr/bin/make 
# vim:noet:ai:ts=8:sw=8:filetype=make:nocindent:textwidth=0:
#
# Copyright (C) 2005 fwupdate.com
#  by Admin <admin@fwupdate.com>
# Licensed under the Open Software License version 2.1 
# 
# Alternatively, you can redistribute it and/or modify 
# it under the terms of the GNU General Public License as published 
# by the Free Software Foundation; either version 2 of the License, 
# or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but 
# WITHOUT ANY WARRANTY; without even the implied warranty of 
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. 
# See the GNU General Public License for more details.
#
# Note that all 'module.mk' files are "include"-ed in this file and
# fall under the same license.
# 
# This is a standard non-recursive make system.
#

  include version.mk
  RELEASE_VERSION := $(RELEASE_MAJOR).$(RELEASE_MINOR).$(RELEASE_SUBLEVEL)$(RELEASE_EXTRALEVEL)
  RELEASE_STRING := $(RELEASE_NAME)-$(RELEASE_VERSION)
  RPM_RELEASE := 0

  BUILD_DATE := $(shell date "+%Y-%m-%d %H:%M:%S")

#--------------------------------------------
# Generic Makefile stuff is below. You
#  should not have to modify any of the stuff
#  below.
#--------------------------------------------

  MODULES :=
  default: all

#Included makefiles will add their deps for each stage in these vars:
  CLEAN_LIST :=
  CLEAN_DEPS :=

  DISTCLEAN_LIST :=
  DISTCLEAN_DEPS :=

  ALL_DEPS :=

#Define the top-level build directory
  BUILDDIR := $(shell pwd)

#Include the docs in the build
#  doc_FILES += COPYING INSTALL README

  all:  $(ALL_DEPS) 

  clean: clean_list $(CLEAN_DEPS) 
  clean_list:
	rm -rf $(CLEAN_LIST)

  distclean: clean distclean_list $(DISTCLEAN_DEPS) 
  distclean_list:
	rm -rf $(DISTCLEAN_LIST)

  CLEAN_LIST += dist rpm build MANIFEST*
  CLEAN_LIST += $(RELEASE_NAME)*.rpm $(RELEASE_NAME)*.tar.gz  $(RELEASE_NAME)*.zip
  CLEAN_LIST += $(shell find . -name .\#\* )
  CLEAN_LIST += $(shell find . -name core )
  CLEAN_LIST += $(shell find . -name .\*.swp )
  CLEAN_LIST += $(shell find . -name \*.pyc )

  .PHONY: all clean clean_list distclean distclean_list \
  		rpm unit_test tarball

rpm:
	-rm -rf build/ dist/ MANIFEST
	python ./setup.py bdist_rpm --python=python --dist-dir=$$(pwd) 
	mv dist/*.tar.gz $(BUILDDIR)
	-rm -rf build/ dist/ MANIFEST

srpm tarball:
	-rm -rf build/ dist/ MANIFEST
	python ./setup.py bdist_rpm --python=python --dist-dir=$$(pwd) --source-only
	mv dist/*.tar.gz $(BUILDDIR)
	-rm -rf build/ dist/ MANIFEST

unit_test:
	@#do the following so that we don't end up running "build_libs" multiple times
	@# the first invocation will end up compiling everything, and subsequent 
	@# invocations will do nothing because everything is up to date.
	@echo "-------------------------"
	@echo " Running python tests..."
	@echo "-------------------------"
	@if [ -z "$(py_test)" ]; then 	\
		py_test=All		;\
	fi				;\
	if [ -e ./test/test$${py_test}.py ]; then \
		PYTHONPATH=$$PYTHONPATH:$$(pwd):$$(pwd)/pymod ./test/test$${py_test}.py		;\
	fi

# Here is a list of variables that are assumed Local to each Makefile. You can
#   safely stomp on these values without affecting the build.
# 	MODULES
#	FILES
#	TARGETS
#	SOURCES

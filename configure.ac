#                                               -*- Autoconf -*-
# vim:tw=0:et:ts=4:sw=4
# Process this file with autoconf to produce a configure script.

####################################
# change version here.
m4_define([release_major_version], [2])
m4_define([release_minor_version], [0])
m4_define([release_micro_version], [8])
# if you define any "extra" version info, include a leading dot (".")
m4_define([release_extra_version], [])

AC_INIT([firmware-extract],
          [release_major_version().release_minor_version().release_micro_version()release_extra_version()])

AC_PREREQ(2.61)
AC_CONFIG_AUX_DIR([pkg])
AM_INIT_AUTOMAKE([1.10 subdir-objects tar-ustar dist-bzip2 dist-lzma no-define])

# Checks for programs.
AC_PROG_INSTALL

# automake macros
AM_PATH_PYTHON

# Checks for header files.

# Checks for typedefs, structures, and compiler characteristics.

# Checks for library functions.


# variables
AC_SUBST([RELEASE_MAJOR], [release_major_version()])
AC_SUBST([RELEASE_MINOR], [release_minor_version()])
AC_SUBST([RELEASE_MICRO], [release_micro_version()])
AC_SUBST([RELEASE_EXTRA], [release_extra_version()])

AC_SUBST([RELEASE_RPM_EXTRA], [$RELEASE_EXTRA])
if test -z "$RELEASE_EXTRA"; then
    RELEASE_RPM_EXTRA=%{nil}
fi

# historical pkg oddity: package name cannot contain '-', so we have to fix it
pkgpythondir=\${pythondir}/firmware_extract
pkgpyexecdir=\${pyexecdir}/firmware_extract

# generate files and exit
AC_CONFIG_FILES([ Makefile pkg/${PACKAGE_NAME}.spec firmware_extract/__init__.py ])
AC_OUTPUT


#!/bin/sh

# run this script to create all the autotools fluff

set -e
[ -e pkg/ ] || mkdir pkg
aclocal
automake --force --foreign --add-missing -c
autoconf --force

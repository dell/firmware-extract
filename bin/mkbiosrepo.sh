#!/bin/bash
# vim:et:ts=4:sw=4:tw=0

function usage ()
{
    echo "usage: $0 [options]"
    echo "  -m <directory>   mirror of ftp.dell.com"
    echo "  -o <directory>   output directory"
    exit 1
}

MIRROR_DIR=
OUTDIR=

while getopts "o:m:dt:" Option
do
  case $Option in
      o)
        OUTDIR=$OPTARG
        ;;
      m)
        MIRROR_DIR=$OPTARG
        ;;
      d)
        DEBUG=1
        ;;
      t)
        ADDITIONAL_TYPES="-t $OPTARG $ADDITIONAL_TYPES"
        ;;
      *) 
        usage
        ;;
  esac
done
shift $(($OPTIND - 1))
# Move argument pointer to next.

if [ -z "$OUTDIR" -o -z "$MIRROR_DIR" ]; then
    echo "required param missing."
    exit 1
fi

[ -e "$OUTDIR" ] ||  mkdir -p $OUTDIR

echo "Start run: $(date)"

set -e
umask 002

if [ -n "$DEBUG" ];then 
    set -x
fi

if ! lockfile -2 -r 2 $OUTDIR/runtime.lock; then
	echo "Could not lock repository"
	exit 1
fi
trap "rm -f $OUTDIR/runtime.lock; trap '' HUP TERM QUIT INT EXIT" HUP TERM QUIT INT EXIT


if [ -z "$NO_MIRROR" ]; then
    echo "Mirroring ftp site"
    make_dell_mirror -m $MIRROR_DIR
fi


if [ -z "$NO_EXTRACT" ]; then
  echo "Extracting HDR files."
  mkdir -p $OUTDIR/SPECS
  mkdir -p $OUTDIR/out/log
  cp -f /usr/share/firmware/spec/systemid.conf $OUTDIR/SPECS/systemid.conf
  extract_hdr -d $MIRROR_DIR -o $OUTDIR/out -s $OUTDIR/SPECS/\*.conf $ADDITIONAL_TYPES
fi


if [ -z "$NO_RPM" ]; then
  mkdir -p $OUTDIR/SPECS
  mkdir -p $OUTDIR/SOURCES
  mkdir -p $OUTDIR/BUILD
  cp /usr/share/firmware/spec/*_spec.in $OUTDIR/SPECS/
  cp -f /usr/share/firmware/spec/systemid.conf $OUTDIR/SPECS/systemid.conf
  cp /usr/share/firmware/spec/dell-std-license.txt $OUTDIR/SOURCES/
  echo "Building RPMS."
  build_rpm -i $OUTDIR/out -b $OUTDIR -s $OUTDIR/SPECS
  rm -rf $OUTDIR/BUILD
  rm -rf $OUTDIR/SOURCES
fi

if [ -z "$NO_DEB" ]; then
  echo "Building DEBS."
  build_deb -i $OUTDIR/out -b $OUTDIR -s /usr/share/firmware/spec
fi


echo "Run complete: $(date)"

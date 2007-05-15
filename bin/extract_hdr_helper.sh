#!/bin/sh

set -e
#set -x

if [ -z "$1" ]; then
    echo "You must supply the exe to extract"
    exit 1
fi

if [ -z "$2" ]; then
    echo "You must supply the output file to write"
    exit 1
fi

hdr=$1
output=$2

DIR=$(cd $(dirname $0); pwd)
PROGNAME=$(basename $0)
DATA=$DIR/$(basename $0 .sh).dat

if [ ! -e $DATA ]; then
    echo "Could not find required DATA file: $DATA"
    echo "Cannot continue, exiting..."
    exit 1
fi

[ -n "$WORKINGDIR" ] || trap 'chmod -R u+rwx $WORKINGDIR; rm -rf $WORKINGDIR' EXIT QUIT TERM HUP INT
[ -n "$WORKINGDIR" ] || WORKINGDIR=$(mktemp -d /tmp/${PROGNAME}-XXXXXX) 
if [ $? -ne 0 ]; then
    echo "Could not create working directory. Exiting..." 
    exit 1
fi

tar xjf $DATA -C $WORKINGDIR 

mv $WORKINGDIR/freedos $WORKINGDIR/freedos-both
if [ "$(uname -m)" = "x86_64" ]; then
    ln -s $WORKINGDIR/freedos-both/64  $WORKINGDIR/freedos
else
    ln -s $WORKINGDIR/freedos-both/32  $WORKINGDIR/freedos
fi

cp $hdr $WORKINGDIR/freedos/

cmd="$(basename $hdr) -writehdrfile"

perl -p -e "s|CURRENT_DIRECTORY|${WORKINGDIR}/freedos|" $WORKINGDIR/freedos/conf/dosemurc.in > $WORKINGDIR/freedos/conf/dosemurc

mkdir -p $HOME/.dosemu
touch $HOME/.dosemu/disclaimer

$WORKINGDIR/freedos/dosemu.bin -I video{none} -n -F $WORKINGDIR/freedos/conf/global.conf -f $WORKINGDIR/freedos/conf/dosemurc -E "$cmd" < /dev/null

mv $WORKINGDIR/freedos/*.[hH][dD][rR] $output > /dev/null 2>&1 || true
if [ -e $output ]; then
	echo "Extracted HDR file to: $output"
	exit 0
fi

dd if=/dev/zero of=$WORKINGDIR/floppy.img bs=18k count=80
/sbin/mkdosfs $WORKINGDIR/floppy.img
perl -p -i -e "s|_vbootfloppy = .*|_vbootfloppy = \"$WORKINGDIR/floppy.img\"|" $WORKINGDIR/freedos/conf/dosemurc 

mkdir $WORKINGDIR/freedos/new/ || true
unzip -o -d $WORKINGDIR/freedos/new/ $hdr

if [ -e $WORKINGDIR/freedos/new/MAKEDISK.BAT ]; then
	file=$(basename $(ls $WORKINGDIR/freedos/new/*.[eE][xX][eE]))
	mv $WORKINGDIR/freedos/new/*.[eE][xX][eE] $WORKINGDIR/freedos

	echo -n -e "$file /s a:\n\r"  > $WORKINGDIR/freedos/runme.bat
	echo -n -e "dir a:*.exe /b > newexe.txt\n\r"  >> $WORKINGDIR/freedos/runme.bat
	echo -n -e "copy a:*.exe c:\n\r"  >> $WORKINGDIR/freedos/runme.bat

	$WORKINGDIR/freedos/dosemu.bin -I video{none} -n -F $WORKINGDIR/freedos/conf/global.conf -f $WORKINGDIR/freedos/conf/dosemurc -E "runme.bat" < /dev/null
	if [ ! -e $WORKINGDIR/freedos/newexe.txt ]; then
		echo "couldnt find a: executable"
		exit 1
	fi
	dos2unix $WORKINGDIR/freedos/newexe.txt
    for BIN in $(cat $WORKINGDIR/freedos/newexe.txt )
    do
	    echo -n -e "$BIN -writehdrfile\n\r"  > $WORKINGDIR/freedos/runme.bat
    done

	$WORKINGDIR/freedos/dosemu.bin -I video{none} -n -F $WORKINGDIR/freedos/conf/global.conf -f $WORKINGDIR/freedos/conf/dosemurc -E "runme.bat" < /dev/null
fi

mv $WORKINGDIR/freedos/*.[hH][dD][rR] $output > /dev/null 2>&1 || true
if [ -e $output ]; then
	echo "Extracted HDR file to: $output"
	exit 0
fi



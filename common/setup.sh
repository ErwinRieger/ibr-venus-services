


rp="$(realpath -s $0)"
srcdir="$(dirname $rp)"
svcname="$(basename $srcdir)"

prefix=""
if [ ! -d /opt/victronenergy ]; then
        echo "Note: /opt/victronenergy not found, assuming debug-mode, will install to /tmp/victronenergy..."
        prefix="/tmp/setup_test"
fi

echo
echo "srcdir: $srcdir"
echo "svcname: $svcname"
echo

if [ -z "$1" ]; then
    echo "usage: $(basename $0) (install, remove) [ttydev]"
    echo "error no cmd (install, remove) given, exiting."
    exit 1
fi
cmd="$1"
shift


copyandlog() {
    local src="$1"
    local dstdir="$2"
    local dstfile="$3"

    local dst="$dstdir/$dstfile"
    local _dstdir="$(dirname $dst)"

    if ! test -d $_dstdir; then
        echo "mkdir $_dstdir"
        mkdir -p $_dstdir
    fi

    if test -d $dst; then
        echo "copy directory not implemented, exiting"
        exit 1
    fi

    echo "copy $src -> $dst"
    cp -p $src $dst
}

sedandcopy() {
    local src="$1"
    local dstdir="$2"
    local dstfile="$3"
    local ttydev="$4"


    sed "s/TTY/$ttydev/" $src > /tmp/run.venustmp
    doifchangedormissing copyandlog /tmp/run.venustmp $dstdir $dstfile
}

doifchangedormissing() {
    local callback="$1"
    shift

    local src="$1"
    local dstdir="$2"
    local dstfile="$3"

    local dst="$dstdir/$dstfile"
    if ! test -e $dst; then
        $callback $*
    else
        if ! cmp $src $dst; then
            $callback $*
        fi
    fi
}

ss=""
ttydev="$1"
svcsrcdir="./service"
svcdestdir="$prefix/opt/victronenergy/service/$svcname"
if [ -d $srcdir/service-templates ]; then
    svcsrcdir="./service-templates"
    svcdestdir="$prefix/opt/victronenergy/service-templates/$svcname"
    ss="1"
    if [ -z "$ttydev" ]; then
        echo "!!! Warning: This is a serial-starter service, but no ttydev given, runtime !!!"
        echo "!!! service files will not be installed! !!!"
    fi
fi

if [ "$cmd" = "install" ]; then

    cd $srcdir

    if [ ! -f setup/filelist ]; then
        echo "setup/filelist not found, exiting."
        exit 1
    fi

    dstdir="$prefix/opt/victronenergy/$svcname"
    echo ""
    echo "*** Install application files to $dstdir ***"
    for f in $(eval ls $(cat setup/filelist)); do
        if [ "$f" = "setup.sh" ]; then
            continue
        fi 
        # echo "copy $f to $dstdir;"
        doifchangedormissing copyandlog $f $dstdir $f
    done
    if [ -f "config_local.py" ]; then
        doifchangedormissing copyandlog config_local.py $dstdir config_local.py
    fi

    echo ""
    echo "*** Install service files to $svcdestdir ***"
    for f in $(cd $svcsrcdir; find . -type f); do
        doifchangedormissing copyandlog $svcsrcdir/$f $svcdestdir $f
    done

    if [ -z "$ss" ]; then
            # simple service, install to /service
	        dstdir="$prefix/service/$svcname"
            echo ""
            echo "*** Install serialstarter service files to $dstdir"
            for f in $(cd $svcsrcdir; find . -type f); do
                doifchangedormissing copyandlog $svcsrcdir/$f $dstdir $f
            done
    else
      if [ -n "$ttydev" ]; then
        # serialstarter, install to /var/volatile and link to /service
	    dstdir="$prefix/var/volatile/services/$svcname.$ttydev"
        echo ""
        echo "*** Install serialstarter service files to $dstdir ***"
        for f in $(cd $svcsrcdir; find . -type f); do
            sedandcopy $svcsrcdir/$f $dstdir $f $ttydev
        done
	    dstdir2="$prefix/service/$svcname.$ttydev"
        echo ""
        echo "*** Link serialstarter service files from $dstdir to $dstdir2 ***"
        mkdir -p $prefix/service
        if [ -L $dstdir2 ]; then
            echo "rm $dstdir2"
            rm $dstdir2
        elif [ -e $dstdir2 ]; then
            echo "rm -rf $dstdir2"
            rm -rf $dstdir2
        fi
        echo " ln -s $dstdir $dstdir2"
        ln -s $dstdir $dstdir2
      fi
    fi
else
    echo "Error, cmd $cmd not implemented."
fi



















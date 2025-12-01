


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
    echo "usage: $(basename $0) (install, remove, installall) [ttydev]"
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

patchedFileName() {
    patchfile="$1"
    head -n2 "$patchfile"|cut -d" " -f2|cut -d"	" -f1|sort|head -1
}

# Find all patch files in the setup directory for the current service.
# Echos a list of files, one per line.
getPatchFiles() {
    ls setup/*.patch 2>/dev/null
}

# Function to revert patches for the current service
revertPatches() {
    if [ ! -d "setup" ]; then
        echo "Error: This script must be run from a service directory containing a 'setup' folder."
        return 1
    fi

    # Use the new function to get patch files and loop through them
    getPatchFiles | while read -r patch_file; do
        # echo "doing patch: $patch_file"
        origfile="$(patchedFileName $patch_file)"
        backupfile="${origfile}.ibrorig"
        if [ -f "$origfile" ] && [ -f "$backupfile" ] && ! cmp "$origfile" "$backupfile" ; then
                echo "Reverting: $backupfile -> $origfile"
                cp "$backupfile" "$origfile"
        fi
    done
}

ss=""
ttydev="$1"
svcsrcdir="./service"
svcdestdir="$prefix/opt/victronenergy/service/$svcname"
if [ "$cmd" = "install" ]; then

    cd $srcdir

    if [ -d service ]; then
        ss="simple"
    elif [ -d service-templates ]; then
        ss="serialstarter"
        svcsrcdir="./service-templates"
        svcdestdir="$prefix/opt/victronenergy/service-templates/$svcname"
        if [ -z "$ttydev" ]; then
            echo "!!! Warning: This is a serial-starter service, but no ttydev given, runtime !!!"
            echo "!!! service files will not be installed! !!!"
        fi
    fi

    if [ ! -f setup/filelist ]; then
        echo "setup/filelist not found, exiting."
        exit 1
    fi

    patches="$(getPatchFiles)"
    if [ -n "$patches" ]; then
        echo ""
        echo "*** Apply patch(es) ***"
        for pf in $patches; do
            echo "patch: $pf"
            origfile="$(patchedFileName $pf)"
            backup="${origfile}.ibrorig"
            if [ ! -e "$backup" ]; then
                    echo "creating backup: $backup"
                    cp "$origfile" "$backup"
            # else
                    # echo "backup $backup existing"
            fi
            echo "patch -N -p0  - $pf"
            patch -N -p0  < $pf
        done    
    fi

    dstdir_base="$prefix/opt/victronenergy"
    echo ""
    echo "*** Install application files to $dstdir_base ***"
    # Read filelist and separate source files from the optional destination
    cat setup/filelist | while read src_part dest_dir_part; do
        # Ignore comments and empty lines
        case "$src_part" in
            ''|'#'*)
                continue
                ;;
        esac

        # echo "src_part: $src_part, dest: $dest_dir_part"

        if [ -z "$dest_dir_part" ]; then
            # No destination specified, use default
            dstdir="$dstdir_base/$svcname"
        else
            # Destination specified, remove leading/trailing whitespace
            dstdir="$dstdir_base/$dest_dir_part"
        fi

        # Use eval to expand glob patterns
        for f in $(eval ls $src_part); do
            if [ "$f" = "setup.sh" ]; then
                continue
            fi
            doifchangedormissing copyandlog "$f" "$dstdir" "$(basename $f)"
        done
    done

    if [ -f "config_local.py" ]; then
        doifchangedormissing copyandlog config_local.py "$dstdir_base/$svcname" config_local.py
    fi

    if [ -n "$ss" ]; then
        echo ""
        echo "*** Install service files to $svcdestdir ***"
        for f in $(cd $svcsrcdir; find . -type f); do
            doifchangedormissing copyandlog $svcsrcdir/$f $svcdestdir $f
        done

        if [ "$ss" = "simple" ]; then
            # simple service, install to /service
	        dstdir="$prefix/service/$svcname"
            echo ""
            echo "*** Install serialstarter service files to $dstdir"
            for f in $(cd $svcsrcdir; find . -type f); do
                doifchangedormissing copyandlog $svcsrcdir/$f $dstdir $f
            done
        elif [ "$ss" = "serialstarter" ]; then
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
    fi
elif [ "$cmd" = "revert" ]; then
    # echo "reverting patches"
    revertPatches
elif [ "$cmd" = "installall" ]; then
    dn="$(dirname $srcdir)"
    for service in $(cat $prefix//data/conf/installed-ibr-services); do
        echo "calling $dn/$service/setup.sh install"
        $dn/$service/setup.sh install
    done
else
    echo "Error, cmd $cmd not implemented."
fi






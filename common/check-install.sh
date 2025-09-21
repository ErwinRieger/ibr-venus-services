

svcsrc=""
svcdev=""
ss=""
if [ -d "service-templates" ]; then
    svcsrc="service-templates"
    svcdst="service-templates"
    if [ -z "$1" ]; then
        echo "error, give device name (ttyUSBx) as argument"
        exit 1
    fi
    svcdev="${1}"
    ss=".${1}"
elif [ -d "service" ]; then
    svcsrc="service"
    svcdst="service"
else
    echo "error, service[-templates] not found"
    exit 1
fi

svcbase="$(pwd)"
svcname="$(basename $svcbase)"

echo "checking $svcbase,  svcname: $svcname"

dstdir="/opt/victronenergy/$svcname"
echo "check app-install in $dstdir:"
if [ -d "$dstdir" ]; then
    for i in $(ls $dstdir/*.sh $dstdir/*.py 2>/dev/null); do
	    bn=$(basename $i)
	    echo "    check: $bn $i"
	    if ! test -f $i; then
		    echo "Warning file does not exist: $i"
		    continue
	    fi
	    if ! cmp $bn $i; then
		    echo "Warning files differ: $bn <-> $i"
	    fi
    done
else
    echo "error: $dstdir does not exist!"
fi

if [ -z "$ss" ]; then
	dstdir="/opt/victronenergy/service/$svcname"
else
	dstdir="/opt/victronenergy/service-templates/$svcname"
fi
echo "check service-install in $dstdir:"
if [ -d "$dstdir" ]; then
    for i in $(cd $svcsrc; find . -type f); do
	    bn=$(basename $i)
	    echo "    check: $i $bn"
	    if ! test -f $dstdir/$i; then
		     echo "Warning files does not exst: $dstdir/$i"
		     continue
	    fi
	    if ! cmp $svcsrc/$i $dstdir/$i; then
		     echo "Warning files differ: $svcsrc/$i <-> $dstdir/$i"
	    fi
    done
else
    echo "error: $dstdir does not exist!"
fi

if [ -n "$ss" ]; then
	dstdir="/var/volatile/services/$svcname.$svcdev"
	echo "check service-install in $dstdir:"
	if [ -d "$dstdir" ]; then
    	    for i in $(cd $svcsrc; find . -type f); do
	    	bn=$(basename $i)
	    	echo "    check: $i $bn"
		if [ "$bn" == "run" ]; then
			sed "s/TTY/$svcdev/" $svcsrc/$i > /tmp/run
		else
		     	echo "Warning unknown file: $i"
		fi
	    	if ! test -f $dstdir/$i; then
		     	echo "Warning file does not exst: $dstdir/$i"
		     	continue
	    	fi
	    	if ! cmp /tmp/run $dstdir/$i; then
		     	echo "Warning files differ: /tmp/run <-> $dstdir/$i"
	    	fi
    	    done
	else
	    echo "error: $dstdir does not exist!"
	fi
fi

dstdir="/service/$svcname${ss}"
echo "check service-install in $dstdir:"
if [ -d "$dstdir" ]; then
    	    for i in $(cd $svcsrc; find . -type f); do
	    	bn=$(basename $i)
	    	echo "    check: $i $bn"
		if [ "$bn" == "run" ]; then
			sed "s/TTY/$svcdev/" $svcsrc/$i > /tmp/run
		else
		     	echo "Warning unknown file: $i"
		fi
	    	if ! test -f $dstdir/$i; then
		     	echo "Warning file does not exst: $dstdir/$i"
		     	continue
	    	fi
	    	if ! cmp /tmp/run $dstdir/$i; then
		     	echo "Warning files differ: /tmp/run <-> $dstdir/$i"
	    	fi
    	    done
else
    echo "error: $dstdir does not exist!"
fi


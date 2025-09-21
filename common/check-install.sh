

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
elif [ -d "services" ]; then
    svcsrc="services"
    svcdst="service"
else
    echo "error, service[-templates] not found"
    exit 1
fi

svcpath=$(ls "$svcsrc"|head -n1)
svcbase=$(basename "$svcpath")
svcname="${svcbase}${ss}"

echo "checking $svcbase,  svcname: $svcname"

dstdir="/opt/victronenergy/$svcbase"
echo "check app-install in $dstdir:"
if [ -d "$dstdir" ]; then
    for i in $(ls $dstdir/*.sh $dstdir/*.py); do
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
	dstdir="/opt/victronenergy/service"
else
	dstdir="/opt/victronenergy/service-templates"
fi
echo "check service-install in $dstdir:"
if [ -d "$dstdir" ]; then
    for i in $(cd $svcsrc; find $svcbase -type f); do
	    bn=$(basename $i)
	    echo "    check: $i $bn"
	    if ! test -f $dstdir/$i; then
		     echo "Warning files does not exst: $dstdir/$i"
		     continue
	    fi
	    if ! diff $svcsrc/$i $dstdir/$i; then
		     echo "Warning files differ: $svcsrc/$i <-> $dstdir/$i"
	    fi
    done
else
    echo "error: $dstdir does not exist!"
fi

if [ -n "$ss" ]; then
	dstdir="/var/volatile/services/$svcname"
	echo "check service-install in $dstdir:"
	if [ -d "$dstdir" ]; then
    	    for i in $(cd $svcsrc/$svcbase; find . -type f); do
	    	bn=$(basename $i)
	    	echo "    check: $i $bn"
		if [ "$bn" == "run" ]; then
			sed "s/TTY/$svcdev/" $svcsrc/$svcbase/$i > /tmp/run
		else
		     	echo "Warning unknown file: $i"
		fi
	    	if ! test -f $dstdir/$i; then
		     	echo "Warning file does not exst: $dstdir/$i"
		     	continue
	    	fi
	    	if ! diff /tmp/run $dstdir/$i; then
		     	echo "Warning files differ: /tmp/run <-> $dstdir/$i"
	    	fi
    	    done
	else
	    echo "error: $dstdir does not exist!"
	fi
fi

dstdir="/service/$svcname"
echo "check service-install in $dstdir:"
if [ -d "$dstdir" ]; then
    	    for i in $(cd $svcsrc/$svcbase; find . -type f); do
	    	bn=$(basename $i)
	    	echo "    check: $i $bn"
		if [ "$bn" == "run" ]; then
			sed "s/TTY/$svcdev/" $svcsrc/$svcbase/$i > /tmp/run
		else
		     	echo "Warning unknown file: $i"
		fi
	    	if ! test -f $dstdir/$i; then
		     	echo "Warning file does not exst: $dstdir/$i"
		     	continue
	    	fi
	    	if ! diff /tmp/run $dstdir/$i; then
		     	echo "Warning files differ: /tmp/run <-> $dstdir/$i"
	    	fi
    	    done
else
    echo "error: $dstdir does not exist!"
fi


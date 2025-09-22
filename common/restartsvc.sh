
srcdir="$(pwd)"
svcname="$(basename $srcdir)"
echo "svc -d /service/$svcname"
svc -d /service/$svcname
sleep 1;
echo "svc -u /service/$svcname"
svc -u /service/$svcname

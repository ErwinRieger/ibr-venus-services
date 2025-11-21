#!/bin/bash
#

. /opt/victronenergy/serial-starter/run-service.sh

app="python3 /data/etc/venus-os_dbus-pvcontrol/dbus-pvcontrol.py"
start 

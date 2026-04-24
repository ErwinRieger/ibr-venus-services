#!/bin/bash
. /opt/victronenergy/serial-starter/run-service.sh
app="python3 /opt/victronenergy/dbus-ibr-memwatch/dbus-ibr-memwatch.py"
start

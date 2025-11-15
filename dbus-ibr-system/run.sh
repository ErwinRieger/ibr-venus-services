#!/bin/bash

. /opt/victronenergy/serial-starter/run-service.sh

/opt/victronenergy/dbus-ibr-system/map-serialdev-to-id.sh
app="python3 /opt/victronenergy/dbus-ibr-system/dbus-ibr-system.py"

start 

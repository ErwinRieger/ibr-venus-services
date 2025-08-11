#!/bin/bash

. /opt/victronenergy/serial-starter/run-service.sh

/data/ibr-venus-services/dbus-ibr-neeycontrol/map-serialdev-to-id.sh
app="python3 /data/ibr-venus-services/dbus-ibr-neeycontrol/dbus-neeycontrol.py"

start 

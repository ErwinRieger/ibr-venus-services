#!/bin/bash

. /opt/victronenergy/serial-starter/run-service.sh

/opt/victronenergy/dbus-ibr-neeycontrol/map-serialdev-to-id.sh
app="python3 /opt/victronenergy/dbus-ibr-neeycontrol/dbus-neeycontrol.py"

start 

#!/bin/bash

. /opt/victronenergy/serial-starter/run-service.sh

app="python3 /opt/victronenergy/dbus-ibr-bms/dbus-ibr-bms.py"
start 

#!/bin/bash

. /opt/victronenergy/serial-starter/run-service.sh

app="python3 /opt/victronenergy/dbus-ibr-serialbat/dbus-ibr-serialbat.py"
args="/dev/$tty"
start $args

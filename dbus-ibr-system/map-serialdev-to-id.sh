#!/bin/bash

mapfile="/data/var/lib/map_serialdev_to_id.py"
mkdir -p "$(dirname "$mapfile")"
echo "# Map serial devices to their udev ID_SERIAL_SHORT" > $mapfile
echo "SerialToId = {" >> $mapfile

for dev in $(ls /dev/ttyUSB*); do
    serialshort="$(udevadm info -q property ${dev}|grep ID_SERIAL_SHORT|cut -d'=' -f2)"
    # Use ID_SERIAL if ID_SERIAL_SHORT is not available
    if [ -z "$serialshort" ]; then
        serialshort="$(udevadm info -q property ${dev}|grep ID_SERIAL|cut -d'=' -f2)"
    fi
    echo "    \"${dev}\": \"${serialshort}\"," >> $mapfile
done

echo "}" >> $mapfile


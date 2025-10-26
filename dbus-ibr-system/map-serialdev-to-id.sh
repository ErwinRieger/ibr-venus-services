#!/bin/bash

mapfile="/data/var/lib/map_serialdev_to_id.py"
mkdir -p "$(dirname "$mapfile")"
echo "# Map serial devices to their udev ID_SERIAL_SHORT" > $mapfile
echo "SerialToId = {" >> $mapfile

for dev in $(ls /dev/ttyUSB*); do
    # serialshort="$(udevadm info -q property --property ID_SERIAL_SHORT ${dev}|cut -d'=' -f2)"
    serialshort="$(udevadm info -q property ${dev}|grep ID_SERIAL_SHORT|cut -d'=' -f2)"
    echo "    \"${dev}\": \"${serialshort}\"," >> $mapfile
done

echo "}" >> $mapfile


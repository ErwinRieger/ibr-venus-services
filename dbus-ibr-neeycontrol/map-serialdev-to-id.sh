#!/bin/bash

mapfile="/data/db/map_serialdev_to_id.py"
echo "# Map serial devices to their udev ID_SERIAL_SHORT" > $mapfile
echo "SerialToId = {" >> $mapfile

for dev in $(ls /dev/ttyUSB*); do
    serialshort="$(udevadm info -q property --property ID_SERIAL_SHORT ${dev}|cut -d'=' -f2)"
    echo "    \"${dev}\": \"${serialshort}\"," >> $mapfile
done

echo "}" >> $mapfile


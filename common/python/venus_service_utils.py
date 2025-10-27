
import logging
import os

from settingsdevice import SettingsDevice

def get_device_instance(bus, prefix, default_instance):
    """
    Gets the device instance from DBus settings.
    e.g. /Settings/Devices/ibrserialbatt_ttyUSB0/ClassAndVrmInstance -> battery:6
    """
    path = '/Settings/Devices/' + prefix
    settings = {'instance': [path + '/ClassAndVrmInstance', default_instance, 0, 0]}
    
    settings_device = SettingsDevice(bus, settings)
    
    devinst_str = settings_device['instance'].split(':')
    if len(devinst_str) < 2:
        logging.error(f"Could not parse device instance: {settings_device['instance']}")
        return -1

    devinst = int(devinst_str[1])
    logging.info(f"DeviceInstance = {devinst}")
    return devinst

def parse_batt_info(batt_info):
    """
    Parses the flat list of battery info from /Info/BattInfo on DBus.
    Returns a dictionary with device name as key and a tuple (devname, btmac) as value.
    """
    batts = {}
    if not batt_info:
        return batts

    logging.info(f"Parsing BattInfo: {batt_info}")
    for i in range(0, len(batt_info), 3):
        # batt_info is a flat list of [dev, devname, btmac, ...]
        if i + 2 < len(batt_info):
            dev, devname, btmac = batt_info[i:i+3]
            batts[dev] = (devname, btmac)
        else:
            logging.warning(f"Incomplete entry in BattInfo: {batt_info[i:]}")

    return batts


def bound(low, v, high):
    return max(low, min(v, high))

def saveAvg(l):

    if l:
        return sum(l) / len(l)
    return 0

#!/usr/bin/env python3

"""
Service to turn on/off neey balancers using bluetooth.

To restart bluetooth:
    hciconfig hci0 down
    hciconfig hci0 up
    
    (or bluetoothctl power off; bluetoothctl power on ?)

"""

from gi.repository import GLib
from dbus.mainloop.glib import DBusGMainLoop

import logging
import sys, os
import dbus
import time
from datetime import datetime as dt  # for UTC time stamps for logging

sys.path.append(os.path.join(os.path.dirname(__file__), './ext/velib_python'))
from vedbus import VeDbusService
from dbusmonitor import DbusMonitor
from ve_utils import exit_on_error

sys.path.append(os.path.join("/data/db"))
from map_serialdev_to_id import *
from  map_id_to_btmac import *

from libbt import NeeyBalancer

VERSION = "0.1"

# uuid of "command characteristic"
cmd_uid = "0000ffe1"

class NeeyControl(object):

    def __init__(self, servicename="com.victronenergy.neeycontrol"):
        super(NeeyControl, self).__init__()

        dummy = {"code": None, "whenToLog": "configChange", "accessLevel": None}
        self.dbusmon = DbusMonitor({ "com.victronenergy.battery" : { "/Ess/Balancing": dummy } },
                valueChangedCallback=self.value_changed_wrapper)

        self._dbusservice = VeDbusService(servicename)

        # Create the mandatory objects
        self._dbusservice.add_mandatory_paths(
            processname=__file__,
            processversion="0.0",
            connection="Virtual",
            deviceinstance=1,
            productid=0,
            productname="NeeyControl",
            firmwareversion=VERSION,
            hardwareversion="0.0",
            connected=1,
        )

        self.balancers = {}
        self.balancerStates = {}
        self.stateChanges = {}
        for dev in SerialToId:
            logging.info(f"configured batt device: {dev}")

            # Get MAC addr of neey balancer for this batt 
            devid = SerialToId[dev]
            if devid in IdToBTMac:
                (neey_mac, desc) = IdToBTMac[devid]

                devname = dev.split("/")[-1]
                logging.info(f"mac for {devname}: {neey_mac}, desc: {desc}")
                self.balancers[devname] = NeeyBalancer(
                    devname, neey_mac, self.doneCb)

                self.stateChanges[devname] = None
                self.balancerStates[devname] = None

        self.running = False
        # GLib.idle_add(self.idlefunc)
        GLib.idle_add(self.idlefuncWrapper)

        # Get dynamic servicename for batteries
        battServices = self.dbusmon.get_service_list(classfilter="com.victronenergy.battery") or {}

        logging.info(f"found initial batt: {battServices}")
        assert("com.victronenergy.battery.aggregate" in battServices)

        balstate = self.dbusmon.get_value("com.victronenergy.battery.aggregate", "/Ess/Balancing") or []
        self.stateChanged(balstate)

        GLib.timeout_add(10000, self.updateWrapper)
        return

    def updateWrapper(self):
        return exit_on_error(self.update)

    def update(self):

        for devname in self.stateChanges:
            deststate = self.stateChanges[devname]
            if deststate != None:
                curstate = self.balancerStates[devname]
                if not self.running and deststate != curstate:
                    logging.info(f"update(): running dev: {devname}, state: {curstate} -> {deststate}")
                    self.running = True
                    self.balancers[devname].switchRun(deststate)

        return True


    # #############################################################################################################

    # Calls value_changed with exception handling
    def value_changed_wrapper(self, *args, **kwargs):
        exit_on_error(self.value_changed, *args, **kwargs)

    def value_changed(self, service, path, options, changes, deviceInstance):

        if service == "com.victronenergy.battery.aggregate":
            value = changes["Value"]
            self.stateChanged(value or [])

    def stateChanged(self, newstate):

        logging.info(f'stateChanged: {newstate}')

        if self.running:
            logging.info(f'Warning, already running...')

        for dev in self.balancerStates: # newstate:

            state = False
            if dev in newstate:
                state = True

            logging.info(f"balancing dev: {dev}, state: {self.balancerStates[dev]} -> {state}")
            # Get serial device from dbus service name (com.victronenergy.battery.ttyUSBx)

            if self.stateChanges[dev] != None:
                logging.info(f'Warning, stateChanged: state pending {newstate}, self.stateChanges[dev]')

            self.stateChanges[dev] = state

    def doneCb(self, devname, ec, newstate):

        logging.info(f"doneCb: {devname}, newstate: {newstate}")
        self.running = False

        if ec != None:
            logging.info(f"doneCb(): {devname}, error-code: {ec}")
            return

        if self.stateChanges[devname] == newstate:
            self.stateChanges[devname] = None
        else:
            logging.info(f"doneCb(): keep stateChange {self.stateChanges[devname]}")

        self.balancerStates[devname] = newstate

    def idlefuncWrapper(self):
        return exit_on_error(self.idlefunc)

    def idlefunc(self):
        for batt in self.balancers:
            self.balancers[batt].run()
        if self.running:
            time.sleep(0.05)
        else:
            time.sleep(0.5)
        return True

# ################
# ## Main loop ###
# ################
def main():

    format = "%(asctime)s :%(name)s:%(message)s"
    logging.basicConfig(level=logging.DEBUG, format=format, datefmt="%d.%m.%y_%X_%Z")
    logging.info("%s: Starting NeeyControl." % (dt.now()).strftime("%c"))

    DBusGMainLoop(set_as_default=True)
    mainloop = GLib.MainLoop()

    NeeyControl()

    logging.info(
        "%s: Connected to DBus, and switching over to GLib.MainLoop()"
        % (dt.now()).strftime("%c")
    )
    mainloop.run()

if __name__ == "__main__":
    main()


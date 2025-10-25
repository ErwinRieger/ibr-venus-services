#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
control smart loads like kettles, heaters or heat pumps.
"""


from gi.repository import GLib
import platform
import logging
import sys
import os, time

import libmqtt

sys.path.insert(1, '/data/ibr-venus-services/common/velib_python')
# sys.path.insert(1, '/data/ibr-venus-services/common/python')

from vedbus import VeDbusService
from dbusmonitor import DbusMonitor
from ve_utils import exit_on_error

servicename='com.victronenergy.ibrloads'

# from /opt/victronenergy/vrmlogger/vrmlogger.py
def calculate_rtt(load, rtt, scale=0.2):
    """ This is an exponentially decaying function for working out the average
    rount-trip time over some window similar to what you'd use for load
    averages. Here we use it to get a clear picture of the round trip time
    of messages over dbus. For the chosen values you get a 4-minute picture
    when using 10-second spaced probes."""
    # return int(load * 0.8 + rtt * 0.2)
    return load * (1.0-scale) + rtt * scale

class ESS(object):

    def __init__(self, productname='IBR dbus loads', connection='dbus-ibr-loads'):

        logging.debug("Service %s starting... " % servicename)

        dummy = {'code': None, 'whenToLog': 'configChange', 'accessLevel': None}
        dbus_tree= {
                # victron system
                'com.victronenergy.system': { 
                    '/Dc/Pv/Power': dummy,
                    '/Dc/Battery/Power': dummy,
                    '/Ac/Consumption/NumberOfPhases': dummy,
                    '/Ac/Consumption/L1/Power': dummy,
                    '/Ac/Consumption/L2/Power': dummy,
                    '/Ac/Consumption/L3/Power': dummy,
                    },
                'com.victronenergy.ibrsystem': { 
                    '/MppOperationMode': dummy,
                    },
                }

        self._dbusmonitor = DbusMonitor(dbus_tree)



        self._dbusservice = VeDbusService(servicename)

        # Create the management objects, as specified in the ccgx dbus-api document
        self._dbusservice.add_path('/Mgmt/ProcessName', __file__)
        self._dbusservice.add_path('/Mgmt/ProcessVersion', 'Unkown version, and running on Python ' + platform.python_version())
        self._dbusservice.add_path('/Mgmt/Connection', connection)

        # Create the mandatory objects
        self._dbusservice.add_path('/DeviceInstance', 1)
        self._dbusservice.add_path('/ProductId', 0)
        self._dbusservice.add_path('/ProductName', productname)
        self._dbusservice.add_path('/FirmwareVersion', 0)
        self._dbusservice.add_path('/HardwareVersion', 0)
        self._dbusservice.add_path('/Connected', 1)

        self.numberOfPhases = self._dbusmonitor.get_value("com.victronenergy.system", "/Ac/Consumption/NumberOfPhases")

        m = self._dbusmonitor.get_value("com.victronenergy.ibrsystem", "/MppOperationMode")
        logging.info(f"initial ibrsystem mpmode: {m}")

        self.loadSwitch = libmqtt.MqttSwitch("DynamicLoadSwitch", "cmnd/tasmota_exess_power/Dimmer", rate=1)
        self.loadSwitch.publish("0") # xxx errorhandling

        self.Kc = 1/500 # 250
        self.Ki = 0.005 # 0.0025 # 0.0015

        self.ysum = 45 / self.Ki

        self.pvavg = 0
        self.pbatt = 0

        self.logtime = 0

        GLib.timeout_add(1000, exit_on_error, self.update)

    def update(self):

        # chgmode = self._dbusmonitor.get_value(self.battserviceName, "/Ess/Chgmode")
        th = self._dbusmonitor.get_value("com.victronenergy.ibrsystem", "/MppOperationMode")

        # Self-consumption
        # powerconsumption = 0
        # for i in range(self.numberOfPhases):
            # powerconsumption += self._dbusmonitor.get_value("com.victronenergy.system", f"/Ac/Consumption/L{i+1}/Power") or 0

        # ppv = self._dbusmonitor.get_value("com.victronenergy.system", "/Dc/Pv/Power") # - pself
        # if ppv > self.pvavg:
            # self.pvavg = calculate_rtt(self.pvavg, ppv, scale=0.25)
        # else:
            # self.pvavg = calculate_rtt(self.pvavg, ppv, scale=0.025)

        # pbatt = self._dbusmonitor.get_value("com.victronenergy.system", "/Dc/Battery/Power") or 0

        # pdest = 0
        # self.pbatt = calculate_rtt(self.pbatt, pbatt, scale=0.01)

        # if True: # not th:
            # if chgmode == 0 or chgmode == "bulk": # bulk
                # pdest = 0.75*self.pvavg
            # elif chgmode == 1 or chgmode == "balancing": # balance
# 
                # if self.pbatt > 0:
                    # pdest = 50
                # else:
                    # pdest = self.pbatt * -1 + 50
            # elif chgmode == 2: # sink
                # pass
            # else: # 3 float "floating"
                # if self.pbatt > 0:
                    # pdest = 30
                # else:
                    # pdest = self.pbatt * -1 + 30

        # pbattchg = pdest # int(self.pbatt)

        # # p_avail = self.pvavg - powerconsumption - pbattchg
        # e = self.pvavg - powerconsumption - pbattchg

        e = -100
        if th == 1: # limiting
            self.ysum = max(self.ysum, 50 / self.Ki)
            e = 25

        maxout = 100

        self.ysum += e 

        ymaxpos = maxout/self.Ki
        ymaxneg = 0 # -ymaxpos/10

        if self.ysum > ymaxpos:
            self.ysum = ymaxpos
        elif self.ysum < ymaxneg:
            self.ysum = ymaxneg

        yp = self.Kc * e 
        yi = self.Ki*self.ysum

        y = ( yp + yi )

        out = round( max(0, y) )

        if (self.logtime % 10) == 0:
            logging.info(f"th: {th}, e: {e:.0f}, P: {yp:.1f}, ysum: {self.ysum} ({ymaxneg}..{ymaxpos}), I: {yi:.1f}, out {out:.1f}")
        self.logtime += 1

        self.loadSwitch.publish(f"{out}") # xxx errorhandling
        return True

    def _get_connected_service_list(self, classfilter=None):
        services = self._dbusmonitor.get_service_list(classfilter=classfilter)
        return services

# === All code below is to simply run it from the commandline for debugging purposes ===

# It will created a dbus service called com.victronenergy.pvinverter.output.
# To try this on commandline, start this program in one terminal, and try these commands
# from another terminal:
# dbus com.victronenergy.pvinverter.output
# dbus com.victronenergy.pvinverter.output /Ac/Energy/Forward GetValue
# dbus com.victronenergy.pvinverter.output /Ac/Energy/Forward SetValue %20
#
# Above examples use this dbus client: http://code.google.com/p/dbus-tools/wiki/DBusCli
# See their manual to explain the % in %20

def main():

    # set timezone used for log entries
    # os.environ['TZ'] = 'Europe/Berlin'
    # time.tzset()

    format = "%(asctime)s %(levelname)s:%(name)s:%(message)s"
    logging.basicConfig(level=logging.DEBUG, format=format, datefmt="%d.%m.%y_%X_%Z")

    from dbus.mainloop.glib import DBusGMainLoop
    # Have a mainloop, so we can send/receive asynchronous calls to and from dbus
    DBusGMainLoop(set_as_default=True)

    ess = ESS()

    logging.info('Connected to dbus, and switching over to GLib.MainLoop() (= event based)')
    mainloop = GLib.MainLoop()

    mainloop.run()


if __name__ == "__main__":
    main()



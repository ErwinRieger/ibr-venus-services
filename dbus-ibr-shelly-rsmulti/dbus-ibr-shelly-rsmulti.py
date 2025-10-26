#!/usr/bin/env python3

#
# todo: 
# * use exit_on_error()
#

import logging
import sys
import os, time
import asyncio

from argparse import ArgumentParser

# 3rd party
try:
    from dbus_fast.aio import MessageBus
    from dbus_fast.constants import BusType
except ImportError:
    from dbus_next.aio import MessageBus
    from dbus_next.constants import BusType

sys.path.insert(1, os.path.join(os.path.dirname(__file__), '..', 'aiovelib'))
sys.path.insert(1, '/data/ibr-venus-services/aiovelib')
sys.path.insert(1, '/data/ibr-venus-services/common/python')

from aiovelib.service import Service as AioDbusService
from aiovelib.service import IntegerItem, TextItem # , DoubleItem
from aiovelib.client import Monitor, Service as AioDbusClient, ServiceHandler

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

NOISELEVEL = 5

# from /opt/victronenergy/vrmlogger/vrmlogger.py
def calculate_rtt(load, rtt, scale=0.2):
    """ This is an exponentially decaying function for working out the average
    rount-trip time over some window similar to what you'd use for load
    averages. Here we use it to get a clear picture of the round trip time
    of messages over dbus. For the chosen values you get a 4-minute picture
    when using 10-second spaced probes."""
    return load * (1.0-scale) + rtt * scale

# Monitor Shelly smart meter
class ShellyHandler(AioDbusClient, ServiceHandler):
    servicetype = "com.victronenergy.device"
    paths = { "/Ac/Power" }

    async def wait_for_essential_paths(self):
        res = {}
        for p in self.paths:
            v = await self.fetch_value(p)
            logger.debug(f"initial {p}: {v}")
            res[p] = v
        return res

# Monitor Rs multi inverter (using dbus-acsystem)
class ACHandler(AioDbusClient, ServiceHandler):
    servicetype = "com.victronenergy.device"
    paths = { 
              "/Ess/AcPowerSetpoint",
              "/Ess/InverterPowerSetpoint",
              "/Ess/UseInverterPowerSetpoint",
              "/Ac/In/1/CurrentLimit",
              "/Ac/In/1/L1/V",
              "/Ac/In/1/L1/P" }

    async def wait_for_essential_paths(self):
        res = {}
        for p in self.paths:
            v = await self.fetch_value(p)
            logger.debug(f"initial {p}: {v}")
            res[p] = v
        return res

class SystemMonitor(Monitor):

    def __init__(self, bus, make_bus, inverterService):

        super().__init__(bus, handlers = {
            'com.victronenergy.grid': ShellyHandler,
            'com.victronenergy.acsystem': ACHandler,
        })
        self.values = {} # { "sp": 0, "ip": 0, "iv": 0 }
        self.inverterService = inverterService
        inverterService.setMonitor(self)

    async def serviceAdded(self, service):

        # We have to wait for some paths to become valid before
        # we can really place or sync things.

        logger.debug(f"service added: {service.name}, waiting for essential paths...")

        self.inverterService.serviceAdded(service.name)

        values = await service.wait_for_essential_paths()
        logger.debug(f"initial values: {values}")

        if "/Ac/In/1/CurrentLimit" in values:
            cl = values['/Ac/In/1/CurrentLimit']
            self.inverterService.setCurrentLimit(cl)

        self.itemsChanged(service, values)

        if len(self.values) == 3:
            asyncio.create_task(self.loop())


    async def serviceRemoved(self, service):

        logger.debug("serviceRemoved(): "+service.name)

    async def systemInstanceChanged(self, service):
        
        logger.debug("systemInstanceChanged(): "+service.name)
        
        await self.serviceRemoved(service)
        await self.serviceAdded(service)

    def itemsChanged(self, service, values):

        if "/Ac/Power" in values:
            self.values["sp"] = values["/Ac/Power"]

        if "/Ac/In/1/L1/P" in values:
            self.values["ip"] = values["/Ac/In/1/L1/P"]

        if "/Ac/In/1/L1/V" in values:
            self.values["iv"] = values["/Ac/In/1/L1/V"]

    async def loop(self):

        while True:
            await asyncio.sleep(1)
            self.inverterService.itemsChanged(self.values)

class IbrEssService(AioDbusService):

    def __init__(self, bus):
        super().__init__(bus, name="com.victronenergy.ibrshellyrsmulti")

        # Compulsory paths
        self.add_item(IntegerItem("/ProductId", 1))
        self.add_item(TextItem("/ProductName", "IBR Shelly RSMulti ESS"))
        self.add_item(IntegerItem("/DeviceInstance", 1))
        self.add_item(TextItem("/Mgmt/ProcessName", __file__))
        self.add_item(TextItem("/Mgmt/ProcessVersion", "0.1"))
        self.add_item(TextItem("/Mgmt/Connection", "local"))
        self.add_item(IntegerItem("/Connected", 1))

        self.acservice = None
        self.currentlimit = None
        self.powerlimit = None
        self.monitor = None
        self.lastPower = None
        self.lastUpdate = time.time()
        self.nextOutput = time.time() + 20
        self.isum = 0
        self.Kp = 0.5
        self.Ki = 0.1
        self.loadavg = 0
        self.pavg = 0
        self.lower_noise = -NOISELEVEL
        self.upper_noise = NOISELEVEL

        asyncio.create_task(self.ping())

    def setMonitor(self, monitor):
        self.monitor = monitor

    def serviceAdded(self, service):

        if service.startswith("com.victronenergy.acsystem"):
            self.acservice = service
            self.monitor.set_value_async(service, '/Ess/AcPowerSetpoint', -0)
            self.monitor.set_value_async(service, '/Ess/InverterPowerSetpoint', -0)
            self.monitor.set_value_async(service, '/Ess/UseInverterPowerSetpoint', 0)

    def itemsChanged(self, values):

        dt = time.time() - self.lastUpdate
        _p = values["sp"] # positiv: verbrauch
        v = values["iv"]
        power = values["ip"]
        _load = _p - power

        self.pavg = calculate_rtt(self.pavg, _p, scale=0.33)
        self.loadavg = calculate_rtt(self.loadavg, _load, scale=0.33)

        logger.debug(f"*** itemsChanged(), dt: {dt:.2f}: ***")

        D = 0
        # if self.lastPower != None:
            # D = 0.1 * (p - self.lastPower) / dt

        if self.lastPower:
            if (self.lastPower <= 0 and _p > 0) or (self.lastPower > 0 and _p < 0):
                # zero cross
                self.lower_noise = -NOISELEVEL
                self.upper_noise = NOISELEVEL
                if abs(_p) < abs(self.lastPower):
                    if _p >= 0:
                        self.upper_noise = min(_p+NOISELEVEL, 10+NOISELEVEL)
                    else:
                        self.lower_noise = max(_p-NOISELEVEL, -5-NOISELEVEL)
                else:
                    if self.lastPower >= 0:
                        self.upper_noise = min(self.lastPower+NOISELEVEL, 10+NOISELEVEL)
                    else:
                        self.lower_noise = max(self.lastPower-NOISELEVEL, -5-NOISELEVEL)

                logger.debug(f"cross {self.lastPower:.1f} -> {_p:.1f}, window: {self.lower_noise:.1f} - {self.upper_noise:.1f}")

        self.lastPower = _p

        delta_isum = 0
        if _p >= self.lower_noise and _p <= self.upper_noise:

            # no isum change window
            logger.debug(f"skip update, window: {self.lower_noise:.1f} - {self.upper_noise:.1f}")
            logger.debug(f"p(e): {_p:.1f}, pavg: {self.pavg:.1f}, power: {power:.1f}, load: {_load:.1f}, loadavg: {self.loadavg:.1f}")
            self.lastUpdate = time.time()
            return

        elif abs(_p) < 10: # slow isum change window

            logger.debug(f"very slow isum update")
            delta_isum = 0.5 * self.pavg * dt

        elif abs(_p) < 15: # slow isum change window

            logger.debug(f"slow isum update")
            delta_isum = 0.75 * self.pavg * dt
        
        else: # normal isum change window

            logger.debug(f"normal isum update")
            delta_isum = self.pavg * dt

        logger.debug(f"p(e): {_p:.1f}, pavg: {self.pavg:.1f}, power: {power:.1f}, load: {_load:.1f}, loadavg: {self.loadavg:.1f}, isum: {self.isum:.1f}")

        P = self.loadavg * self.Kp
        I = self.Ki*(self.isum+delta_isum)

        out = P + I + D

        if (out >= 2500 and self.pavg > 0) or (out <= 0 and self.pavg < 0):
            logger.debug(f"Anti-windup active. Output: {out:.1f}, Error: {self.pavg:.1f}")
        else:
            self.isum += delta_isum

        logger.debug(f"P: {P:.1f}, I: {I:.1f}, D: {D:.1f}, out: {out:.1f}")

        out = max(out, 0)
        out = min(out, 2500)

        self.powerlimit = out

        cl = round(out/v, 3)
        if cl != self.currentlimit:
            self.currentlimit = cl
            self.setOutput(out, cl)

        self.lastUpdate = time.time()

    async def ping(self):

        while True:
            await asyncio.sleep(1)

            if time.time() > self.nextOutput:
                logger.debug(f"ping")
                self.setOutput(self.powerlimit, self.currentlimit)

    def setOutput(self, pout, cl):

        p = - pout * 1.05
        self.monitor.set_value_async(self.acservice, '/Ess/InverterPowerSetpoint', p)
        self.monitor.set_value_async(self.acservice, '/Ess/AcPowerSetpoint', p)
        self.monitor.set_value_async(self.acservice, '/Ess/UseInverterPowerSetpoint', 1)

        logger.debug(f"setting setpoint: {pout:.1f} (scaled: {p:.1f}, currentlimit: {cl}")
        self.monitor.set_value_async(self.acservice, '/Ac/In/1/CurrentLimit', cl)

        self.nextOutput = time.time() + 30 # we have to update rs multi/acsystem every 60 seconds

    def setCurrentLimit(self, cl):
        self.currentlimit = cl
        self.isum = (cl * 230) / self.Ki

async def amain(bus_type):

    bus = await MessageBus(bus_type=bus_type).connect()

    service = IbrEssService(bus)
    await service.register()

    monitor = await SystemMonitor.create(bus,
        lambda: MessageBus(bus_type=bus_type),
        service)

    await bus.wait_for_disconnect()


def main():
    parser = ArgumentParser(description=sys.argv[0])
    parser.add_argument('--dbus', help='dbus bus to use, defaults to system',
            default='system')
    args = parser.parse_args()

    logging.basicConfig(format='%(levelname)-8s %(message)s',
            level=(logging.DEBUG))

    bus_type = {
        "system": BusType.SYSTEM,
        "session": BusType.SESSION
    }.get(args.dbus, BusType.SYSTEM)

    mainloop = asyncio.get_event_loop()
    logger.info("Starting main loop")
    try:
        asyncio.get_event_loop().run_until_complete(amain(bus_type))
    except KeyboardInterrupt:
        logger.info("Terminating")

if __name__ == "__main__":
    main()


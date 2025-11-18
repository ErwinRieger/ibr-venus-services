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

from venus_service_utils import bound

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
            while v==None or v==[]:
                logger.debug(f"waiting for initial {p}, got: {v}")
                await asyncio.sleep(0.25)
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
              "/Ac/In/1/L1/P",
              "/Soc" }

    async def wait_for_essential_paths(self):
        res = {}
        for p in self.paths:
            v = await self.fetch_value(p)
            while v==None or v==[]:
                logger.debug(f"waiting for initial {p}, got: {v}")
                await asyncio.sleep(0.25)
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
        self.values = {}
        self.inverterService = inverterService
        inverterService.setMonitor(self)

    async def serviceAdded(self, service):

        # We have to wait for some paths to become valid before
        # we can really place or sync things.

        logger.debug(f"service added: {service.name}, waiting for essential paths...")

        self.inverterService.serviceAdded(service.name)

        values = await service.wait_for_essential_paths()
        logger.debug(f"initial values: {values}")

        self.itemsChanged(service, values)

    async def serviceRemoved(self, service):

        logger.debug("serviceRemoved(): "+service.name)

    async def systemInstanceChanged(self, service):
        
        logger.debug("systemInstanceChanged(): "+service.name)
        
        await self.serviceRemoved(service)
        await self.serviceAdded(service)

    def itemsChanged(self, service, values):

        self.values.update(values)

        if len(self.values) == 8:
            # Got all needed values
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
        self.monitor = None
        self.lastPower = None
        self.lastUpdate = time.time()
        self.isum = 0
        self.delta_isum = 0
        self.Kp = 0.5
        self.Ki = 0.1
        self.loadavg = 0
        self.voltage = 230
        self.pavg = 0
        self.lower_noise = -NOISELEVEL
        self.upper_noise = NOISELEVEL

    def setMonitor(self, monitor):
        self.monitor = monitor
        asyncio.create_task(self.update())

    def serviceAdded(self, service):

        if service.startswith("com.victronenergy.acsystem"):
            self.acservice = service
            self.monitor.set_value_async(service, '/Ess/AcPowerSetpoint', 0)
            self.monitor.set_value_async(service, '/Ess/InverterPowerSetpoint', 0)
            self.monitor.set_value_async(service, '/Ess/UseInverterPowerSetpoint', 0)

    def itemsChanged(self, values):

        dt = time.time() - self.lastUpdate
        _p = values["/Ac/Power"] # shelly power, positiv: verbrauch
        power = values["/Ac/In/1/L1/P"] # inverter power
        _load = _p - power

        self.pavg = calculate_rtt(self.pavg, _p, scale=0.33)
        self.loadavg = calculate_rtt(self.loadavg, _load, scale=0.33)
        self.voltage = calculate_rtt(self.voltage, values["/Ac/In/1/L1/V"], scale=0.33)

        # logger.debug(f"*** itemsChanged(), dt: {dt:.2f}: ***")

        if self.lastPower is not None:
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

                # logger.debug(f"cross {self.lastPower:.1f} -> {_p:.1f}, window: {self.lower_noise:.1f} - {self.upper_noise:.1f}")

        self.lastPower = _p
        self.lastUpdate = time.time()

        soc = values["/Soc"]

        if soc <= 10:
            logger.debug(f"skip update, soc low: {soc}")
            self.loadavg = 0
            self.isum = 0
            self.delta_isum = 0
            return

        if _p >= self.lower_noise and _p <= self.upper_noise:

            # no isum change window
            # logger.debug(f"skip update, window: {self.lower_noise:.1f} - {self.upper_noise:.1f}")
            # logger.debug(f"p(e): {_p:.1f}, pavg: {self.pavg:.1f}, power: {power:.1f}, load: {_load:.1f}, loadavg: {self.loadavg:.1f}")
            return

        elif abs(_p) < 10: # slow isum change window

            # logger.debug(f"very slow isum update")
            self.delta_isum += 0.5 * self.pavg * dt

        elif abs(_p) < 15: # slow isum change window

            # logger.debug(f"slow isum update")
            self.delta_isum += 0.75 * self.pavg * dt
        
        else: # normal isum change window

            # logger.debug(f"normal isum update")
            self.delta_isum += self.pavg * dt

        # logger.debug(f"p(e): {_p:.1f}, pavg: {self.pavg:.1f}, power: {power:.1f}, load: {_load:.1f}, loadavg: {self.loadavg:.1f}, isum: {self.isum:.1f}")
        # self.lastUpdate = time.time()

    async def update(self):

        while True:

            P = self.loadavg * self.Kp
            I = self.Ki*(self.isum+self.delta_isum)

            D = 0
            # if self.lastPower != None:
                # D = 0.1 * (p - self.lastPower) / dt

            out = P + I + D

            if (out >= 2500 and self.pavg > 0) or (out <= 0 and self.pavg < 0):
                logger.debug(f"Anti-windup active. Output: {out:.1f}, Error: {self.pavg:.1f}")
            else:
                self.isum += self.delta_isum

            self.delta_isum = 0

            # logger.debug(f"P: {P:.1f}, I: {I:.1f}, D: {D:.1f}, out: {out:.1f}")

            out = bound(0, out, 2500)

            cl = round(out/self.voltage, 3)
            self.setOutput(out, cl)

            await asyncio.sleep(1)

    def setOutput(self, pout, cl):

        p = - pout * 1.05
        self.monitor.set_value_async(self.acservice, '/Ess/InverterPowerSetpoint', p)
        self.monitor.set_value_async(self.acservice, '/Ess/AcPowerSetpoint', p)
        self.monitor.set_value_async(self.acservice, '/Ess/UseInverterPowerSetpoint', 1)

        logger.debug(f"setting setpoint: {pout:.1f} (scaled: {p:.1f}, currentlimit: {cl}")
        self.monitor.set_value_async(self.acservice, '/Ac/In/1/CurrentLimit', cl)

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


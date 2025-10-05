#!/usr/bin/env python3

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
from aiovelib.service import IntegerItem, TextItem, DoubleItem
from aiovelib.client import Monitor, Service as AioDbusClient, ServiceHandler
from aiovelib.localsettings import SettingsService as SettingsClient, Setting

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

MULTIOFFMODE = 4
POWERPATH = "/Ac/Out/L1/P"

# Monitor RS6000
class RSHandler(AioDbusClient, ServiceHandler):
    servicetype = "com.victronenergy.device"
    paths = { "/Ac/Out/L1/P" }

    async def wait_for_essential_paths(self):
        res = {}
        for p in self.paths:
            v = await self.fetch_value(p)
            logger.debug(f"initial {p}: {v}")
            res[p] = v
        return res

# Monitor Multiplus
class MPHandler(AioDbusClient, ServiceHandler):
    servicetype = "com.victronenergy.device"
    paths = { "/Mode" }

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
            'com.victronenergy.inverter': RSHandler,
            'com.victronenergy.vebus': MPHandler, # assumes vebus devices are multiplus 2 devices.
        })
        self.inverterService = inverterService

    async def serviceAdded(self, service):

        if service.name == "com.victronenergy.inverter.rshack":
            return

        logger.debug(f"service added: {service.name}")

        # We have to wait for some paths to become valid before
        # we can really place or sync things.
        logger.debug("Waiting for essential paths, service: "+service.name)
        values = await service.wait_for_essential_paths()
        logger.debug(f"initial values: {values}")

        self.itemsChanged(service, values)

    async def serviceRemoved(self, service):

        if service.name == "com.victronenergy.inverter.rshack":
            return

        logger.debug("serviceRemoved(): "+service.name)
        if service.name.startswith("com.victronenergy.inverter."):
            self.inverterService.itemsChanged({"/Ac/L1/P": 0})

    async def systemInstanceChanged(self, service):
        logger.debug("systemInstanceChanged(): "+service.name)
        await self.serviceRemoved(service)
        await self.serviceAdded(service)

    def itemsChanged(self, service, values):

        if service.name == "com.victronenergy.inverter.rshack":
            return

        # logger.debug(f"items changed, service: {service.name}, values: {values}")
        self.inverterService.itemsChanged(values)

class IbrRsHackService(AioDbusService):

    def __init__(self, bus):
        super().__init__(bus, name="com.victronenergy.inverter.rshack")

        # Compulsory paths
        self.add_item(IntegerItem("/ProductId", 1))
        self.add_item(TextItem("/ProductName", "IBR RS Hack"))
        self.add_item(IntegerItem("/DeviceInstance", 1))
        self.add_item(TextItem("/Mgmt/ProcessName", __file__))
        self.add_item(TextItem("/Mgmt/ProcessVersion", "0.1"))
        self.add_item(TextItem("/Mgmt/Connection", "local"))
        self.add_item(IntegerItem("/Connected", 1))

        self.add_item(DoubleItem("/Energy/InverterToAcOut", 0))

        # flag, output load and energy consumption if
        # multiplus is off
        self.output = False
        self.power = 0
        self.ts = 0
        self.energy = 0

    def itemsChanged(self, values):

        if "/Mode" in values:
            mode = values["/Mode"]
            if mode == MULTIOFFMODE:
                if not self.output:
                    self.output = True
                    self.ts = 0
            else:
                self.output = False

        if POWERPATH in values:

            power = values[POWERPATH]
            now = time.time()

            if self.output and self.ts:
                dt = now - self.ts
                self.energy += (self.power*dt)/3600000.0
                logger.debug(f"energy: {self.power}, dt: {dt}, {self.energy}")
                with self as service:
                    service["/Energy/InverterToAcOut"] = self.energy

            self.power = power
            self.ts = now

async def amain(bus_type):

    bus = await MessageBus(bus_type=bus_type).connect()

    service = IbrRsHackService(bus)
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


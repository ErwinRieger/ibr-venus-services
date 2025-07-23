#!/usr/bin/env python3

import logging
import sys
import os
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
sys.path.insert(1, os.path.join(os.path.dirname(__file__), '/data', 'etc', 'ibr-venus-services', 'aiovelib'))

from aiovelib.service import Service as AioDbusService
from aiovelib.service import IntegerItem, TextItem, DoubleItem
from aiovelib.client import Monitor, Service as AioDbusClient, ServiceHandler
from aiovelib.localsettings import SettingsService as SettingsClient, Setting

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class SettingsMonitor(Monitor):
    def __init__(self, bus, **kwargs):
        super().__init__(bus, handlers = {
        'com.victronenergy.settings': SettingsClient
        }, **kwargs)

class ClientBase(ServiceHandler):
    servicetype = "com.victronenergy.device"

    async def wait_for_essential_paths(self):
        res = {}
        for p in self.paths:
            v = await self.fetch_value(p)
            logger.debug(f"initial {p}: {v}")
            res[p] = v
        return res

class SystemMonitor(Monitor):

    def __init__(self, bus, make_bus, system_service):

        # Solar chargers, Inverter multi rs
        chargerType = type("ChargerClient", (AioDbusClient, ClientBase),
                     { "paths": { "/Yield/User" } })
        # Inverter RS and Mulitiplus 2
        loadType = type("LoadClient", (AioDbusClient, ClientBase),
                     { "paths": { "/Dc/0/Current" } })

        super().__init__(bus, handlers = {
            'com.victronenergy.settings': SettingsClient,
            'com.victronenergy.multi': chargerType,
            'com.victronenergy.solarcharger': chargerType,
            'com.victronenergy.inverter': loadType,
            'com.victronenergy.vebus': loadType, # assumes vebus devices are multiplus 2 devices.
        })
        self.system_service = system_service
        self.yields = { } # total pv load
        self.currents = { } # load current from invertes
        self.settings = None

        self.settingsCalled = asyncio.Future()

    async def serviceAdded(self, service):

        logger.debug(f"service added: {service.name}")

        if service.name == "com.victronenergy.settings":

            self.settings = service
            await self.settings.add_settings(
                Setting("/Settings/IbrSystem/GridEnergyPrice", 0.5, 0, 10),
            )
            ep = await service.fetch_value("/Settings/IbrSystem/GridEnergyPrice")
            logger.debug(f"initial energy price: {ep}")
            self.system_service.gridEnergyPrice = ep
            self.settingsCalled.set_result(True)
            return

        # We have to wait for some paths to become valid before
        # we can really place or sync things.
        logger.debug("Waiting for essential paths, service: "+service.name)
        values = await service.wait_for_essential_paths()
        logger.debug(f"initial values: {values}")

        await self.settingsCalled

        self.itemsChanged(service, values)

    async def serviceRemoved(self, service):
        logger.debug("serviceRemoved(): "+service.name)

    async def systemInstanceChanged(self, service):
        logger.debug("systemInstanceChanged(): "+service.name)
        await self.serviceRemoved(service)
        await self.serviceAdded(service)

    @property
    def pvyield(self):
        return sum(self.yields.values())

    def itemsChanged(self, service, values):
        logger.debug(f"items changed, service: {service.name}, values: {values}")

        if "/Yield/User" in values:
            pvyield = values["/Yield/User"]
            self.yields[service.name] = pvyield
            self.system_service.publishPVYield(self.pvyield)

        elif "/Dc/0/Current" in values:
            cur = values["/Dc/0/Current"]
            self.currents[service.name] = cur
            self.system_service.publishBattLoad(sum(self.currents.values()))

        elif "/Settings/IbrSystem/GridEnergyPrice" in values:
            ep = values["/Settings/IbrSystem/GridEnergyPrice"]
            self.system_service.gridEnergyPrice = ep
            self.system_service.publishPVYield(self.pvyield)

class IbrSystemService(AioDbusService):

    def __init__(self, bus):
        super().__init__(bus, name="com.victronenergy.ibrsystem")

        # Compulsory paths
        self.add_item(IntegerItem("/ProductId", None))
        self.add_item(TextItem("/ProductName", None))
        self.add_item(IntegerItem("/DeviceInstance", 1))
        self.add_item(TextItem("/Mgmt/ProcessName", __file__))
        self.add_item(TextItem("/Mgmt/ProcessVersion", "0.1"))
        self.add_item(TextItem("/Mgmt/Connection", "local"))
        self.add_item(IntegerItem("/Connected", 1))

        self.add_item(DoubleItem("/BattLoad", None))
        self.add_item(DoubleItem("/TotalPVYield", None))
        self.add_item(DoubleItem("/TotalPVEarnings", None))

    @property
    def gridEnergyPrice(self):
        return self._gridEnergyPrice

    @gridEnergyPrice.setter
    def gridEnergyPrice(self, ep):
        self._gridEnergyPrice = ep

    def publishPVYield(self, pvyield):
        earn = pvyield * self.gridEnergyPrice
        print(f"publish yield: {pvyield}, earn: {earn}")
        with self as s:
            s['/TotalPVYield'] = pvyield
            s['/TotalPVEarnings'] = earn

    def publishBattLoad(self, load):
        print(f"publish load: {load}")
        with self as s:
            s['/BattLoad'] = load

async def amain(bus_type):

    bus = await MessageBus(bus_type=bus_type).connect()

    service = IbrSystemService(bus)
    monitor = await SystemMonitor.create(bus,
        lambda: MessageBus(bus_type=bus_type),
        service)

    # Fire off update threads
    loop = asyncio.get_event_loop()

    await service.register()

    await bus.wait_for_disconnect()


def main():
    parser = ArgumentParser(description=sys.argv[0])
    parser.add_argument('--dbus', help='dbus bus to use, defaults to system',
            default='system')
    # parser.add_argument('--debug', help='Turn on debug logging',
            # default=False, action='store_true')
    args = parser.parse_args()

    # logging.basicConfig(format='%(levelname)-8s %(message)s',
            # level=(logging.DEBUG if args.debug else logging.INFO))
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


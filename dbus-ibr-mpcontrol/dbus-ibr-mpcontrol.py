#!/usr/bin/env python3

# todo:
# * use exit_on_error?

import logging
import sys
import os, time, asyncio

# 3rd party
try:
    from dbus_fast.aio import MessageBus
    from dbus_fast.constants import BusType
except ImportError:
    from dbus_next.aio import MessageBus
    from dbus_next.constants import BusType

sys.path.insert(1, os.path.join(os.path.dirname(__file__), '..', 'aiovelib'))
sys.path.insert(1, '/data/ibr-venus-services/aiovelib')
# sys.path.insert(1, '/data/ibr-venus-services/common/python')

from aiovelib.service import Service as AioDbusService
from aiovelib.service import IntegerItem, TextItem
from aiovelib.client import Monitor, Service as AioDbusClient, ServiceHandler
from aiovelib.localsettings import SettingsService as SettingsClient, Setting


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


MAXPOWER = 6000 # RS6000 inverter
ONPOWER =   MAXPOWER * 0.5 # watts of rs6000 power when we turn on the slave multiplus, depends on ac current limit of multiplus (19.0A)
OFFPOWER = (ONPOWER * 2) / 3 # turn off mp2 when power is below offpower, to add some hysteresis
# LOGPOWER = MAXPOWER * 0.8 # log inverter power above this value

OnTimeout = 3600 # Power must be below OFFPOWER for OnTimeout seconds to turn off multiplus

servicename='com.victronenergy.ibrmpcontrol'

# To map Multiplus and Inverter RS modes to strings
mode_on=3
mode_off=4

victron_mode_names = {
        None: "None",
        1: "Charger only",
        2:"Inverter only",
        mode_on: "On",
        mode_off: "Off",
        5:"Low Power/Eco",
        251:"Passthrough",
        252:"Standby",
        253:"Hibernate",
        }

# To map Multiplus and Inverter RS states to strings
state_off=0

victron_state_names = {
        None: "None",
        state_off:"Off",
        1:"Low Power",
        2:"Fault",
        3:"Bulk",
        4:"Absorption",
        5:"Float",
        6:"Storage",
        7:"Equalize",
        8:"Passthrough",
        9:"Inverting",
        10:"Power assist",
        11:"Power supply mode",
        244:"Sustain(Prefer Renewable Energy)",
        245:"Wake-up",
        # 25-:"Blocked", ???
        252:"External control",
        }


# todo: factor out into common lib
class ClientBase(ServiceHandler, AioDbusClient):
    servicetype = "com.victronenergy.device"
    offDefaults = {}

    async def wait_for_essential_paths(self):
        res = {}
        for p in self.paths:
            v = await self.fetch_value(p)
            # Cannot test for [] here. This would block because
            # an empty list is returned if
            # device (inveter, multiplus) is turned off.
            while v==None: # or v==[]:
                logger.debug(f"waiting for initial {p}, got: {v}")
                await asyncio.sleep(0.25)
                v = await self.fetch_value(p)

            logger.debug(f"initial {p}: {v}")
            res[p] = v

        return self.handleOffValues(res)

    def handleOffValues(self, values):

        for (p, default) in self.offDefaults.items():
            if values.get(p) == []:
                logger.debug(f"handle default: {p}: [] -> {default}")
                values[p] = default

        return values

    def update_items(self, items):
        updated = AioDbusClient.update_items(self, items)
        return self.handleOffValues(updated)

    def update_unseen_items(self, items):
        updated = AioDbusClient.update_unseen_items(self, items)
        return self.handleOffValues(updated)

class SystemMonitor(Monitor):

    def __init__(self, bus, mpcontrol):

        # Inverter RS
        inverterType = type("InverterClient", (ClientBase, ),
                     { "paths": { '/Mode', '/State', '/Ac/Out/L1/P' },
                       "offDefaults": { '/Ac/Out/L1/P': 0, '/Mode': mode_off, '/State': state_off } })
        # Mulitiplus 2
        multiType = type("MultiClient", (ClientBase, ),
                     { "paths": { '/Mode', '/State' },
                       "offDefaults": { '/Mode': mode_off, '/State': state_off } })

        super().__init__(bus, handlers = {
            'com.victronenergy.inverter': inverterType,
            'com.victronenergy.vebus': multiType, # assumes vebus devices are multiplus 2 devices.
        })
        self.mpcontrol = mpcontrol
        self.inverter = None
        # self.settings = None

        # self.settingsCalled = asyncio.Future()
        mpcontrol.setMonitor(self)

    async def serviceAdded(self, service):

        logger.debug(f"service added: {service.name}, waiting for essential paths...")

        if service.name.startswith("com.victronenergy.inverter"):
            self.inverter = service
        else:
            self.mpcontrol.setMultiplus(service.name)

        """
        if service.name == "com.victronenergy.settings":

            self.settings = service
            await self.settings.add_settings(
                Setting("/Settings/IbrSystem/GridEnergyPrice", 0.5, 0, 10),
            )
            ep = await service.fetch_value("/Settings/IbrSystem/GridEnergyPrice")
            logger.debug(f"initial energy price: {ep}")
            self.mpcontrol.gridEnergyPrice = ep
            self.settingsCalled.set_result(True)
            return
        """

        # We have to wait for some paths to become valid before
        # we can really place or sync things.
        values = await service.wait_for_essential_paths()
        logger.debug(f"{service.name}: initial values: {values}")

        # await self.settingsCalled

        self.itemsChanged(service, values)

    async def serviceRemoved(self, service):
        logger.debug("serviceRemoved(): "+service.name)

    async def systemInstanceChanged(self, service):
        logger.debug("systemInstanceChanged(): "+service.name)
        await self.serviceRemoved(service)
        await self.serviceAdded(service)

    def itemsChanged(self, service, values):
        # logger.debug(f"items changed, service: {service.name}, values: {values}")

        if service == self.inverter:

            if values.get("/Mode", mode_on) == mode_off:
                # turn off multiplus, too
                logger.info("xxx todo: turn off multiplus...")

            if (p := values.get("/Ac/Out/L1/P")) is not None:
                self.mpcontrol.update(p)

            return

        # multiplus mode
        if (mode := values.get("/Mode")) != None:
            self.mpcontrol.setMPMode(mode)

        # multiplus state
        if (state := values.get("/State")) != None:
            logger.info(f"multiplus State changed to {victron_state_names[state]}")

class MPControl(AioDbusService):

    def __init__(self, bus):

        super().__init__(bus, name=servicename)

        logger.debug("Service %s starting... "% servicename)

        # Compulsory paths
        self.add_item(IntegerItem("/DeviceInstance", 0))
        self.add_item(IntegerItem("/ProductId", 1))
        self.add_item(TextItem("/ProductName", "IBR MP Control"))
        self.add_item(TextItem("/Mgmt/ProcessName", __file__))
        self.add_item(TextItem("/Mgmt/ProcessVersion", "0.1"))
        self.add_item(TextItem("/Mgmt/Connection", "local"))
        self.add_item(IntegerItem("/Connected", 1))

        self.add_item(IntegerItem('/Timer', 0))
        self.add_item(IntegerItem('/MaxPRS', 0))

        self.monitor = None
        self.multiplus = None
        self.multimode = None

        self.maxPRS = 0

        self.endTimer = time.time() + OnTimeout 

    def setMonitor(self, monitor):
        self.monitor = monitor
        asyncio.create_task(self.loop())

    def setMultiplus(self, mp):
        self.multiplus = mp

    def setMPMode(self, mode):
        if mode != self.multimode:
            logger.info(f"Multiplus mode changed from {victron_mode_names[self.multimode]} to {victron_mode_names[mode]}")
            self.multimode = mode

    def isOn(self):
        return self.multimode == mode_on

    def isOff(self):
        return self.multimode == mode_off

    def turnOn(self):
        logger.info(f"Turning on {self.multiplus}")
        self.monitor.set_value_async(self.multiplus, '/Mode', mode_on)

    def turnOff(self):
        logger.info(f"Turning off {self.multiplus}")
        self.monitor.set_value_async(self.multiplus, '/Mode', mode_off)

    # Check, if we have to turn on multiplus
    def update(self, inverterPower):

        # todo: use async future here
        if self.multiplus is None:
            logger.debug(f"no multiplus, yet...")
            return

        if inverterPower >= ONPOWER:

            if self.isOff():
                logger.info("Starting mp2, power: %d" % inverterPower)
                self.turnOn()

        if inverterPower >= OFFPOWER:
            self.endTimer = time.time() + OnTimeout # Re-Start power-off timer

        if inverterPower > self.maxPRS:
            with self as s:
                s['/MaxPRS'] = inverterPower
            self.maxPRS = inverterPower

        return

    # Check periodically, if we have to turn off multiplus
    async def loop(self):

        while True:

            await asyncio.sleep(10)

            dt = self.endTimer - time.time()

            if self.isOn() and (dt < 0):
                # switch off mp2
                logger.info(f"stopping mp2...")
                self.turnOff()

            with self as s:
                if dt > 0:
                    s['/Timer'] = int(dt)
                else:
                    s['/Timer'] = 0
    
async def amain():

    bus = await MessageBus(bus_type=BusType.SYSTEM).connect()

    service = MPControl(bus)

    await service.register()

    monitor = await SystemMonitor.create(bus, service)


    await bus.wait_for_disconnect()


def main():

    format = "%(asctime)s %(levelname)s:%(name)s:%(message)s"
    logging.basicConfig(level=logging.DEBUG, format=format, datefmt="%d.%m.%y_%X_%Z")

    mainloop = asyncio.get_event_loop()
    logger.info("Starting main loop")
    try:
        asyncio.get_event_loop().run_until_complete(amain())
    except KeyboardInterrupt:
        logger.info("Terminating")


if __name__ == "__main__":
    main()



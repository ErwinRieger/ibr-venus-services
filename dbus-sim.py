#!/usr/bin/env python3

import logging, sys, os, asyncio, math, random
from argparse import ArgumentParser

# 3rd party
try:
    from dbus_fast.aio import MessageBus
    from dbus_fast.constants import BusType
except ImportError:
    from dbus_next.aio import MessageBus
    from dbus_next.constants import BusType

sys.path.insert(1, os.path.join(os.path.dirname(__file__), 'aiovelib'))

from aiovelib.service import Service as AioDbusService
from aiovelib.service import IntegerItem, TextItem, DoubleItem
from aiovelib.client import Monitor, Service as AioDbusClient, ServiceHandler
from aiovelib.localsettings import SettingsService as SettingsClient

import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

fig, axs = plt.subplots(3)
fig.suptitle('Simulator: PV [W], load [A], battcurrent [A]')
pvplot = axs[0]
loadplot = axs[1]
battloadplot = axs[2]

class Simulation:

    def __init__(self, scale, installed_pv, steps, delay, services, 
                 inverter_services, twait):

        self.scale = scale
        self.installed_pv = installed_pv / len(services)
        self.steps = steps
        self.delay = delay
        self.services = services
        self.inverter_services = inverter_services
        self.twait = twait
        self.interval = (12*3600) / steps

        self.startload = steps/3
        self.endload = steps*2/3

        logger.debug(f"interval: {self.interval} seconds, {self.interval/3600} h")
        self.step = 0

        for plot in axs:
            plot.set_xlim([0, steps])
            plot.grid(True)
            plot.plot([0,steps], [0, 0])
        pvplot.set_ylim([0, self.installed_pv*1.05])
        loadplot.set_ylim([0, self.installed_pv/50*1.5])
        battloadplot.set_ylim([-self.installed_pv/50*0.5, self.installed_pv/50*1.05])
        plt.pause(0.001)

    async def loop(self):

        _yield = 0
        while self.step < self.steps+1:

            logger.debug(f"simul loop {self.step}/{self.steps}")

            pvpower = self.installed_pv * math.sin(self.step/self.steps * math.pi)
            _yield += pvpower * (self.interval/3600) / 1000

            dccurrent = 0.033
            if (self.step >= self.startload) and (self.step <= self.endload):
                srange = self.endload - self.startload
                y = max(0.01, self.step - self.startload)
                dccurrent = ((self.installed_pv*1.25) * math.sin(y/srange * math.pi)) / 50 

            pvplot.plot(self.step, pvpower, marker=".", color="green")
            loadplot.plot(self.step, dccurrent, marker=".", color="red")
            battloadplot.plot(self.step, (pvpower/50) - dccurrent, marker=".", color="black")

            for plot in axs:
                plot.figure.canvas.flush_events()
                plot.figure.canvas.draw_idle()

            for service in self.services:
                with service as s:
                    rand = (random.random()/25) + (1-1/50)
                    # logger.debug("simul loop, step, random:", self.step, rand);
                    s['/Yield/User'] = _yield * rand

            for service in self.inverter_services:
                with service as s:
                    rand = (random.random()/25) + (1-1/50)
                    # logger.debug("simul loop, step, random:", self.step, rand);
                    s['/Dc/0/Current'] = dccurrent * rand

            await asyncio.sleep(self.delay)

            if self.step == self.steps and self.twait == -1:
                # repeat
                logger.debug("loop done, restarting ")
                self.step = 0
                _yield = 0
            else:
                self.step += 1


        if self.twait > 0:
            logger.debug("loop done, waiting {self.twait}");
            await asyncio.sleep(self.twait)
            # for s in self.services:
                # s.done()


class ServiceMockup(AioDbusService):

    def __init__(self, bus, name, path="/Yield/User"):
        super().__init__(bus, "com.victronenergy."+name)

        # Compulsory paths
        self.add_item(IntegerItem("/ProductId", None))
        self.add_item(TextItem("/ProductName", None))
        self.add_item(IntegerItem("/DeviceInstance", len(name)))
        self.add_item(TextItem("/Mgmt/ProcessName", __file__+":"+name))
        self.add_item(TextItem("/Mgmt/ProcessVersion", "0.1"))
        self.add_item(TextItem("/Mgmt/Connection", "local"))
        self.add_item(IntegerItem("/Connected", 1))

        self.add_item(DoubleItem(path, None))

        with self as s:
            s[path] = 0

async def amain(bus_type, args):

    busses = []
    # Fire off update threads
    loop = asyncio.get_event_loop()

    bus = await MessageBus(bus_type=bus_type).connect()
    chgsrv = ServiceMockup(bus, "solarcharger", "/Yield/User")
    await chgsrv.register()

    bus = await MessageBus(bus_type=bus_type).connect()
    multisrv = ServiceMockup(bus, "multi", "/Yield/User")
    await multisrv.register()

    bus = await MessageBus(bus_type=bus_type).connect()
    mp2srv = ServiceMockup(bus, "vebus", "/Dc/0/Current")
    await mp2srv.register()

    bus = await MessageBus(bus_type=bus_type).connect()
    rs6srv = ServiceMockup(bus, "inverter", "/Dc/0/Current")
    await rs6srv.register()

    simul = Simulation(1, 10000, int(args.steps), float(args.delay),
                       [chgsrv, multisrv],
                       [rs6srv, mp2srv],
                       int(args.twait))
    logger.debug("await loop")
    await loop.create_task(simul.loop())

def main():
    parser = ArgumentParser(description=sys.argv[0])
    parser.add_argument('--dbus', help='dbus bus to use, defaults to system',
            default='system')
    parser.add_argument('--twait', help='Wait seconds after simulation.',
            default=0)
    parser.add_argument('--steps', help='Numbers of steps to run.',
            default=24)
    parser.add_argument('--delay', help='Delay between steps [s].',
            default=0.5)
   
    args = parser.parse_args()

    logging.basicConfig(format='%(levelname)-8s %(message)s', level=(logging.DEBUG))

    bus_type = {
        "system": BusType.SYSTEM,
        "session": BusType.SESSION
    }.get(args.dbus, BusType.SYSTEM)

    mainloop = asyncio.get_event_loop()
    logger.info("Starting main loop")
    try:
        asyncio.get_event_loop().run_until_complete(amain(bus_type, args))
    except KeyboardInterrupt:
        logger.info("Terminating")
        pass

if __name__ == "__main__":
    main()





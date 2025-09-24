#!/usr/bin/env python3

"""
Service to aggregate multiple (serial-) batteries into one virtual battery and
to implement a charging algorithm for them.
"""

"""
XXXX

watch (entire) batsoc and (bank-) min cellvoltage (xxx bank- dynamic low bound) and
control ESS/inverter through faked (entire-) battsoc

minsoc: 10%
onsoc:  15%

batsoc (bank):


fakesoc (entire):


hysterese:

    zum ausschalten:
        flag setzen
        wir merken uns beim ausschalten den aktuellen gesamt-soc
        fake-soc auf 5% setzen, dadurch inverter aus

    wenn wir turned off sind und batt-spannung sich erholt hat:
        warten bis gesamt-soc >= dem gemerkten end-sock+hysterese (10%) ist

        --> fake beenden und realen (10%) grösseren gesamt-sock "freigeben"
            xxx: es ist nicht gesagt, dass der inverter dann auch schon wieder
            einschaltet, da er ja eine eigene hysterese hat...

        


    
"""

from gi.repository import GLib
import logging
import sys, os, time, math
import dbus
import datetime

sys.path.insert(1, '/data/ibr-venus-services/common/velib_python')
sys.path.insert(1, '/data/ibr-venus-services/common/python')

from vedbus import VeDbusService
from dbusmonitor import DbusMonitor, Service, notfound, MonitoredValue
from ve_utils import exit_on_error
from venus_service_utils import *

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

##################################################
# Configuration:
from config import *
logger.info(f"Config: NUMBER_OF_BATTERIES: {NUMBER_OF_BATTERIES}")
logger.info(f"Config: BATTERY_CAPACITY: {BATTERY_CAPACITY}")
##################################################

# Current
C100 = max(BATTERY_CAPACITY/100, 1)
C2 = BATTERY_CAPACITY/2

CGES = BATTERY_CAPACITY * NUMBER_OF_BATTERIES
CGES100 = max(CGES/100, 1)
CGES2 = CGES/2

# Cell voltages
# cellfloat = 3.370
# cellpull = cellfloat + 0.015
cellfloat = 3.340
cellfloat = 3.335
cellpull = 3.380

MAX_CHARGING_CELL_VOLTAGE = 3.55
MAX_CHARGING_VOLTAGE = MAX_CHARGING_CELL_VOLTAGE*16 # XXX hardcoded number of cells
vrange = MAX_CHARGING_CELL_VOLTAGE - cellpull

# balancer
BALANCER_CELLDIFF = 0.005 # [V]

# delta bms soc to change from floating state to
# bulk state
DELTA_BMSSOC_BALANCE = 0.1 # [%]
DELTA_BMSSOC_FLOAT = 2.5 # [%]

VERSION = "0.1"

from statemachine import StateMachine, State
from statemachine.exceptions import TransitionNotAllowed

minbalancesoc = 99

class ChargerStateMachine(StateMachine):
    bulk = State(initial=True)
    balancing = State()
    floating = State()

    cycle = (
        bulk.to(balancing, cond="ladeende")
        | balancing.to(floating, cond="balanced")
        | balancing.to(bulk, cond="discharge")
        | floating.to(bulk, cond="discharge")
    )

    def __init__(self):
        super(ChargerStateMachine, self).__init__()
        self.reset()

    def reset(self):
        self.balancetimer = BALANCETIME
        # self.balancetimer = 5 # BALANCETIME

    def isBalanced(self):
        assert(self.balancetimer >= 0)
        return self.balancetimer == 0

    def inBulk(self):
        return self.current_state == self.bulk

    def isBalancing(self):
        return self.current_state == self.balancing

    def isFloating(self):
        return self.current_state == self.floating

    def ladeende(self, battery):
        logger.info(f"    Batt {battery.batt[-1]}, State {self.current_state}: ladeende: estsoc: {battery.estsoc:.1f}%")
        
        if not battery.bhistory.valid():
            logger.info(f"    Filling history {battery.bhistory.n()} / {battery.bhistory.nhist}")
            return False

        return battery.estsoc >= minbalancesoc

    def balanced(self, battery):
        logger.info(f"    Batt {battery.batt[-1]}, State {self.current_state}: balanced: celldiff: {battery.voltagediff:.3f}, timer: {self.balancetimer}s")
        if self.balancetimer and (battery.voltagediff < BALANCER_CELLDIFF):
            assert(self.balancetimer >= 0)
            self.balancetimer -= 1
        return self.balancetimer == 0

    def discharge(self, battery):

        logger.info(f"    Batt {battery.batt[-1]}, State {self.current_state}, discharge: bmssoc: {battery.bmssoc:.1f}%, start: {self.start_bmssoc}%")

        if battery.bmssoc > self.start_bmssoc:
            self.start_bmssoc = battery.bmssoc
            return False

        if self.isBalancing():
            return battery.bmssoc < (self.start_bmssoc - DELTA_BMSSOC_BALANCE)

        return battery.bmssoc < (self.start_bmssoc - DELTA_BMSSOC_FLOAT)

    def on_enter_balancing(self, battery):
        logger.info(f"enter balancing charging, Start soc: {battery.bmssoc:.1f}")
        self.start_bmssoc = battery.bmssoc

    def on_enter_float(self, battery):
        logger.info(f"enter float charging, Start soc: {battery.bmssoc:.1f}")
        self.start_bmssoc = battery.bmssoc

    def before_cycle(self, event: str, source: State, target: State, message: str = ""):
        message = ". " + message if message else ""
        return f"{event} from {source.id} to {target.id}{message}"

    # def on_enter_bulk(self):
        # logger.info("Bulk charging.")

    # def on_enter_float(self):
        # logger.info("float charging.")

    # def on_exit_red(self):
        # logger.info("Go ahead!")


class MyDbusMonitor(DbusMonitor):

    def scan_dbus_service_inner(self, *args, **kwargs):
        exit_on_error(self._scan_dbus_service_inner, *args, **kwargs)

    def _scan_dbus_service_inner(self, serviceName):
        paths = self.dbusTree.get(serviceName, None)
        if paths is None:
            logger.debug("Ignoring service %s, not in the tree" % serviceName)
            return False

        logger.info("Found: %s, scanning and storing items" % serviceName)
        serviceId = self.dbusConn.get_name_owner(serviceName)

        # we should never be notified to add a D-Bus service that we already have. If this assertion
        # raises, check process_name_owner_changed, and D-Bus workings.
        assert serviceName not in self.servicesByName
        assert serviceId not in self.servicesById

        try:
            di = self.dbusConn.call_blocking(serviceName,
                '/DeviceInstance', None, 'GetValue', '', [])
        except dbus.exceptions.DBusException:
            logger.info("       %s was skipped because it has no device instance" % serviceName)
            return False # Skip it

        logger.info("       %s has device instance %s" % (serviceName, di))
        service = Service(serviceId, serviceName, di)

        # Let's try to fetch everything in one go
        values = {}
        try:
            values.update(self.dbusConn.call_blocking(serviceName, '/', None, 'GetValue', '', []))
        except:
            pass

        for path, options in paths.items():
            # path will be the D-Bus path: '/Ac/ActiveIn/L1/V'
            # options will be a dictionary: {'code': 'V', 'whenToLog': 'onIntervalAlways'}
            # check that the whenToLog setting is set to something we expect
            assert options['whenToLog'] is None or options['whenToLog'] in Service.whentologoptions

            # Try to obtain the value we want from our bulk fetch. If we
            # cannot find it there, do an individual query.
            value = values.get(path[1:], notfound)
            if value != notfound:
                service.set_seen(path)
            else:
                try:
                    value = self.dbusConn.call_blocking(serviceName, path, None, 'GetValue', '', [])
                    service.set_seen(path)
                except dbus.exceptions.DBusException as e:
                    if e.get_dbus_name() in (
                            'org.freedesktop.DBus.Error.ServiceUnknown',
                            'org.freedesktop.DBus.Error.Disconnected'):
                        raise # This exception will be handled below

                    # TODO org.freedesktop.DBus.Error.UnknownMethod really
                    # shouldn't happen but sometimes does.
                    logger.info("%s %s does not exist (yet)" % (serviceName, path))
                    value = None

            service.paths[path] = MonitoredValue(value, None, options)

            if options['whenToLog']:
                service[options['whenToLog']].append(path)

        logger.info(f"Finished scanning and storing items for {serviceName} id: {id(self)}")

        # Adjust self at the end of the scan, so we don't have an incomplete set of
        # data if an exception occurs during the scan.
        self.servicesByName[serviceName] = service
        self.servicesById[serviceId] = service
        self.servicesByClass[service.service_class].append(service)
        return True


# umin = 3.35
umin = cellfloat - 0.020
def fu(u, bcv):
    if u < umin:
        return 0
    return min((u-umin)/(bcv-umin), 1)

def fi(i):
    if i > C2:
        return 0
    elif i < C100:
        return 1
    return (1-((i-C100)/(C2-C100)))

class expfilter(object):
    value = 0
    k = 0

    def __init__(self, iv, k):
        super(expfilter, self).__init__()

        self.value = iv
        self.k = k

    def filter(self, value):
        self.value = self.k*value + (1.0-self.k)*self.value

class battery(object):

    def __init__(self, dbusmon, servicename):
        super(battery, self).__init__()

        self.dbusmon = dbusmon
        self.batt = servicename
        self.id = servicename[-1]

        self.bhistory = history(30) # self.history.nhist)
        self.ysum = 0
        self.lastbcv = None

        # self.kp = 1 # 1.25
        # self.ki = 0.025
        self.kp = 0.75 # 1 # 1.25
        self.ki = 0.02 # 0.025

        self.sm = ChargerStateMachine()

        self.testdone = False

        # self.cellCutoff = 3.0
        self.turnOff = False

    def get_value(self, path):
        return self.dbusmon.get_value(self.batt, path)

    def resetDaily(self):
        self.sm.reset()

    def isBalanced(self):
        return self.sm.isBalanced()

    def inBulk(self):
        return self.sm.inBulk()

    def isBalancing(self):
        return self.sm.isBalancing()

    def isFloating(self):
        return self.sm.isFloating()

    def isThrottling(self):
        if self.sm.current_state == self.sm.bulk:
            return False
        if self.isBalancing() or self.sm.current_state == self.sm.floating:
            return True

    def update(self, cvavg, allfloat):

        ubatt = self.dbusmon.get_value(self.batt, "/Dc/0/Voltage")
        self.cbatt = self.dbusmon.get_value(self.batt, "/Dc/0/Current")
        self.ucell = self.dbusmon.get_value(self.batt, "/System/MaxCellVoltage")
        ucell_min = self.dbusmon.get_value(self.batt, "/System/MinCellVoltage")
        self.voltagediff = self.dbusmon.get_value(self.batt, "/Voltages/Diff")
        self.bmssoc = self.dbusmon.get_value(self.batt, "/Soc")

        self.bhistory.update(self.cbatt)
        cavg = self.bhistory.As()

        if self.sm.current_state == self.sm.bulk:
            bcv = max(
                cellpull,
                round( min( cellpull + vrange * (cavg-C100) / C2, MAX_CHARGING_CELL_VOLTAGE ), 2)
                )
        elif self.sm.current_state == self.sm.balancing:
            bcv = cellpull
        else: # float
            if allfloat:
                bcv = cellfloat
            else:
                bcv = cellpull

        self.f_u = fu(self.ucell, bcv)
        f_i = fi(cavg)
        self.estsoc = min( self.f_u * f_i * 100, 99 )

        # yyyy debug
        """
        if not self.testdone:
            if self.sm.current_state == self.sm.bulk:
                self.estsoc = 99
                self.debugtime = time.time()
            if self.sm.current_state == self.sm.balancing:
                if time.time() - self.debugtime < 10:
                    self.estsoc = 99
            elif self.sm.current_state == self.sm.floating:
                self.testdone = True
        """

        try:
            res=self.sm.cycle(self)
        except TransitionNotAllowed:
            pass
        else:
            if res!=None:
                logger.info(f"    State Event: {res}")

        if self.lastbcv and self.lastbcv != bcv:
            dv = bcv - self.lastbcv
            logger.info(f"adjusting ysum: {16*dv}")
            self.ysum -= 16*dv

        self.lastbcv = bcv

        diff = 0
        if self.ucell > bcv:
            #diff -= 16 * 2* (self.ucell - bcv)
            diff -= 16 * (self.ucell - bcv)
        else:
            diff += 16 * min(bcv - self.ucell, 0.005)

        logger.info(f"    U: {ubatt:.3f}V, I: {self.cbatt:.3f}A, iavg: {cavg:.3f}A, max: {self.ucell:.3f}V, bcv: {bcv:.3f}V, diff: {diff:.3f}V")

        diffvolt = max( min(cvavg - ubatt, 1), 0)

        self.ysum += diff * self.ki

        if self.ysum > 0.75:
            self.ysum = 0.75
        elif self.ysum < -1.5:
            self.ysum = -1.5

        cv = 16*bcv + self.kp*diff + self.ysum + diffvolt
        logger.info(f"    CV: {16*bcv:.3f}V + {self.kp*diff:.3f}(P) + {self.ysum:.3f}(ysum) + {diffvolt:.3f}(cable) = {cv:.3f}")
            
        self.chargevoltage = cv
        logger.info(f"    fu: {self.f_u:.2f}, fi: {f_i:.2f}, estimsoc: {self.estsoc:.1f}%")

        # Dynamic cut off voltage
        uCutoff_0 = 3.1
        dynCutoffRange = 0.25 
        if self.cbatt:
            # cellCutoff = max(2.85, 3.1 + 0.25 * (min(self.cbatt, 0)/BATTERY_CAPACITY))
            cellCutoff = bound(
                    uCutoff_0-dynCutoffRange,
                    uCutoff_0 + dynCutoffRange * (self.cbatt/BATTERY_CAPACITY),
                    uCutoff_0)
        else:
            cellCutoff = uCutoff_0

        if ucell_min <= cellCutoff:
            self.turnOff = True
        else:
            self.turnOff = False

        logger.info(f"    minvolt: {ucell_min:.3f}V, cellcutoff: {cellCutoff:.3f}V, turnoff: {self.turnOff}")


class history(object):

    def __init__(self, nhist):
        super(history, self).__init__()
        self.nhist = nhist
        self.aslist = []

    def sum(self):
        return abs(sum(self.aslist))

    def update(self, As):
        if len(self.aslist) == self.nhist:
            self.aslist.pop(0)
        self.aslist.append(As)

    def As(self):
        if not len(self.aslist):
            return 0
        return sum(self.aslist) / len(self.aslist)

    def n(self):
        return len(self.aslist)

    def valid(self):
        return len(self.aslist) == self.nhist

dummy = {"code": None, "whenToLog": "configChange", "accessLevel": None}

class DbusAggBatService(object):

    def __init__(self, servicename=f"com.victronenergy.{SERVICENAME}.aggregate"):
        super(DbusAggBatService, self).__init__()

        self.turnedOff = False
        self.turnOnSoc = 0
        # self.fakeSoc = None
        self.forceSoc = 0

        self.maindbusmon = DbusMonitor({
                        "com.victronenergy.battery" : { "/Soc": dummy }, 
                        'com.victronenergy.inverter': {
                            "/Dc/0/Voltage": dummy,
                            "/Dc/0/Current": dummy,
                        },
                        'com.victronenergy.multi': {
                            "/Dc/0/Voltage": dummy,
                            "/Dc/0/Current": dummy,
                        },
                        'com.victronenergy.vebus': {
                            "/Dc/0/Voltage": dummy,
                            "/Dc/0/Current": dummy,
                        },
                        'com.victronenergy.solarcharger': {
                            "/Dc/0/Voltage": dummy,
                        },
                    },
                deviceAddedCallback=self.deviceAddedCb,
                deviceRemovedCallback=self.deviceRemovedCb)

        self.busmon_scan_dbus_service = self.maindbusmon.scan_dbus_service
        self.maindbusmon.scan_dbus_service = self.scan_dbus_service

        self._dbusservice = VeDbusService(servicename)

        # Create the mandatory objects
        self._dbusservice.add_mandatory_paths(
            processname=__file__,
            processversion="0.0",
            connection="Virtual",
            deviceinstance=1,
            productid=0,
            productname="ibrbms",
            firmwareversion=VERSION,
            hardwareversion="0.0",
            connected=1,
        )

        self._dbusservice.add_path('/Ess/Balancing', [], writeable=True)
        self._dbusservice.add_path('/Ess/Chgmode', "bulk", writeable=True)
        self._dbusservice.add_path('/Ess/Throttling', False, writeable=True)
        # self._dbusservice.add_path('/TimeToGo', 1)
        self._dbusservice.add_path('/Ibr/Debug/ForceSoc', 0, writeable=True,
                                   onchangecallback=self.forceSocChanged)

        self.addPath = (
            "Info/MaxDischargeCurrent",
            "Dc/0/Current",
            "Dc/0/Power",
            "InstalledCapacity",
            "ConsumedAmphours",
            "Capacity",
            "System/NrOfModulesOnline",
            "System/NrOfModulesOffline",
            "System/NrOfModulesBlockingCharge",
            "System/NrOfModulesBlockingDischarge",
            "Alarms/CellImbalance",
            "Alarms/HighCellVoltage",
            "Alarms/HighChargeCurrent",
            "Alarms/InternalFailure_alarm",
            "Alarms/HighChargeTemperature",
            "Alarms/HighDischargeCurrent",
            "Alarms/HighTemperature",
            "Alarms/HighVoltage",
            "Alarms/InternalFailure",
            "Alarms/LowCellVoltage",
            "Alarms/LowChargeTemperature",
            "Alarms/LowSoc",
            "Alarms/LowTemperature",
            "Alarms/LowVoltage",
            "Alarms/BmsCable",
            )

        self.avgPath = (
            # "Soc",
            )

        self.ownPath = (
            "Info/MaxChargeVoltage",
            "Info/MaxChargeCurrent",
            "Ess/Balancing",
            "Ess/Chgmode",
            "Ess/Throttling",
            "Soc",
            "Ibr/Debug/ForceSoc",
            # "TimeToGo",
            )

        self.minPath = (
            "System/MinCellTemperature",
            "System/MinCellVoltage",
            )

        self.maxPath = (
            "Info/BatteryLowVoltage",
            "Dc/0/Voltage",
            "Dc/0/Temperature",
            "System/MaxCellTemperature",
            "System/MaxCellVoltage",
            "Voltages/Diff",
            )

        self.allsetPath = (
            "Io/AllowToCharge",
            "Io/AllowToDischarge",
            "Io/AllowToBalance",
        )

        self.onesetPath = (
            )
            
        self.ignorePath = (
            'Mgmt/ProcessName',
            'Mgmt/ProcessVersion',
            'Mgmt/Connection',
            'DeviceInstance',
            'ProductId',
            'ProductName',
            'FirmwareVersion',
            'HardwareVersion',
            'Connected',
            "Dc/0/MidVoltage",
            "Dc/0/MidVoltageDeviation",
            "History/ChargeCycles",
            "History/TotalAhDrawn",
            "System/NrOfCellsPerBattery",
            )

        self.getTextCallbacks = {
            '/Dc/0/Voltage': lambda a, x: "{:.2f}V".format(x),
            '/Dc/0/Current':lambda a, x: "{:.2f}A".format(x),
            '/Dc/0/Power': lambda a, x: "{:.0f}W".format(x),
            '/ConsumedAmphours': lambda a, x: "{:.0f}Ah".format(x),
        }

        self.batteries = {}
        self.monitorlist = {}

        # charger
        self.chargevoltage = 16 * cellfloat # xxx hardcoded
        self._dbusservice.add_path('/Info/MaxChargeVoltage', self.chargevoltage, writeable=True, gettextcallback=lambda p, v: "{:2.2f}V".format(v))

        self.lastchargevoltage = None
        self.maxccfilter = expfilter(10*CGES100, 0.25)

        self.lastmaxcc = None
        self._dbusservice.add_path('/Info/MaxChargeCurrent', 0, writeable=True, gettextcallback=lambda p, v: "{:2.2f}A".format(v))

        self._dbusservice.add_path('/Soc', 33, writeable=True)

        self.lastTime = time.time()

        self.history = history(30) # 120
        # end charger

        # xxx multi plus missing!
        # xxx make services dynamic
        self.chargers = self.maindbusmon.get_service_list(classfilter="com.victronenergy.solarcharger") or {}
        self.inverters = self.maindbusmon.get_service_list(classfilter="com.victronenergy.inverter") or {}
        # for inverter in self.inverters:
            # self.chargers[inverter] = 1
        for multi in self.maindbusmon.get_service_list(classfilter="com.victronenergy.multi") or {}:
            self.chargers[multi] = 1
            self.inverters[multi] = 1
        for multiplus in self.maindbusmon.get_service_list(classfilter="com.victronenergy.vebus") or {}:
            self.inverters[multiplus] = 1

        logger.info(f"chargers: {self.chargers}")
        logger.info(f"inverters: {self.inverters}")
        assert(self.chargers)
        assert(self.inverters)

        # Get dynamic servicename for batteries
        battServices = self.maindbusmon.get_service_list(classfilter="com.victronenergy.battery") or []

        if len(battServices) != NUMBER_OF_BATTERIES:
            logger.error(f"Error: found {len(battServices)} batterie(s), should have: {NUMBER_OF_BATTERIES}, exiting!")
            sys.exit(1)
            return

        for batt in battServices:
            logger.info(f"found initial batt: {batt}")
            GLib.timeout_add(250, self.addBatteryWrapper, batt)

        GLib.timeout_add(1000, self.updateWrapper)
        return

    # #############################################################################################################

    # XXX Dbusmonitor tries to scan OUR service, too. This leads to
    # a unnessesary delay/timeout. So filter our own service out here:
    def scan_dbus_service(self, serviceName):
        logger.info("scan_service: " + serviceName)
        if serviceName.startswith(f"com.victronenergy.{SERVICENAME}.aggregate"):
            return False
        return self.busmon_scan_dbus_service(serviceName)

    # Calls value_changed with exception handling
    def value_changed_wrapper(self, *args, **kwargs):
        exit_on_error(self.value_changed, *args, **kwargs)

    def deviceAddedCb(self, service, instance):
        logger.error(f"Error: new battery {service} appeared, exiting!")
        sys.exit(1)

    def deviceRemovedCb(self, service, instance):
        logger.error(f"Error: battery {service} diappeared, exiting!")
        sys.exit(1)

    def updateWrapper(self):
        return exit_on_error(self.update)

    def update(self):

        logger.info("--- update ---")

        chargerVoltages = []
        for charger in self.chargers:
            vc = self.maindbusmon.get_value(charger, "/Dc/0/Voltage")
            if vc:
                chargerVoltages.append(vc)
        cvavg = sum(chargerVoltages) / len(chargerVoltages)

        allbulk = not (False in map(lambda b: b.inBulk(), self.batteries.values()))
        allbalanced = not (False in map(lambda b: b.isBalanced(), self.batteries.values()))
        allfloat = not (False in map(lambda b: b.isFloating(), self.batteries.values()))

        balancing = []
        throttling = False
        chgmode = "bulk"
        turnOff = False
        avgsoc = []
        for batt in self.batteries.values():

            batt.update(cvavg, allfloat)

            # control balancers
            if not (allbulk or allfloat or allbalanced):
                if batt.isBalancing() or batt.isBalanced():
                    battname = batt.batt.split(".")[-1]
                    balancing.append(battname)

            # Reset balancing state at midnight
            if batt.isBalanced() and time.localtime().tm_hour == 0:
                batt.resetDaily()

            if batt.isThrottling():
                throttling = True

            if batt.isBalancing():
                chgmode = "balancing"
            elif allfloat:
                chgmode = "floating"

            if batt.turnOff:
                turnOff = True

            avgsoc.append(batt.bmssoc)

        avgsoc = sum(avgsoc) / len(avgsoc)

        self._dbusservice['/Ess/Balancing'] = balancing
        self._dbusservice['/Ess/Chgmode'] = chgmode
        self._dbusservice['/Ess/Throttling'] = throttling

        t = time.time()
        dt = t - self.lastTime
        self.lastTime = t

        currsum = sum(map(lambda b: b.cbatt, self.batteries.values()))
        As = currsum * dt

        self.history.update(As)

        socs = map(lambda b: b.estsoc, self.batteries.values())
        estsoc = sum(socs) / len(self.batteries)

        loadcurrent = 0
        for inverter in self.inverters:
            loadcurrent += min(self.maindbusmon.get_value(inverter, "/Dc/0/Current"), 0)

        self.maxccfilter.filter( 5*CGES100 + CGES2 * (1 - math.pow(estsoc/99.0, 2)) - loadcurrent)

        chargevoltages = map(lambda b: b.chargevoltage, self.batteries.values())
        self.chargevoltage = min(chargevoltages)

        if self.chargevoltage > MAX_CHARGING_VOLTAGE:
            logger.info(f"    cap cv!: {self.chargevoltage:.3f}V to MAX_CHARGING_VOLTAGE: {MAX_CHARGING_VOLTAGE:.3f}V")
            self.chargevoltage = MAX_CHARGING_VOLTAGE

        logger.info(f"batt current: {currsum:.3f}A, loadcurrent: {loadcurrent:.3f}, estsoc: {estsoc:.1f}%")

        v = round(self.chargevoltage, 3)
        if v != self.lastchargevoltage:
            self._dbusservice[ "/Info/MaxChargeVoltage" ] = v
            self.lastchargevoltage = v

        i = round(self.maxccfilter.value)
        if i != self.lastmaxcc:
            self._dbusservice[ "/Info/MaxChargeCurrent" ] = i
            self.lastmaxcc = i

        logger.info(f"chargevoltage: {v:.3f}V, charge current: {i}A")

        # turn on/off battery
        essminsoc = 10 # xxx must match setting in ESS/inverter
        if turnOff:
            if not self.turnedOff:
                self.turnedOff = True
                self.turnOnSoc = max(avgsoc + 10, essminsoc + 10)
        else:
            if self.turnedOff and avgsoc >= self.turnOnSoc:
                self.turnedOff = False

        fakesoc = avgsoc
        if self.turnedOff:
            # # force batt off?
            # fakesoc = min(avgsoc, essminsoc)
            # # avoid victron ess charging start (starting at 5% soc?)
            # fakesoc = max(fakesoc, 6) 

            # force batt off?
            # avoid victron ess charging start (starting at 5% soc?)
            bound(6, avgsoc, essminsoc)
        else:
            # keep batt alive?
            fakesoc = max(avgsoc, essminsoc + 4) # SocSwitchOffset = 3.0

        if self.forceSoc:
            fakesoc = self.forceSoc

        logger.info(f"turnOff: {turnOff}, TurnedOff: {self.turnedOff}, avg-soc: {avgsoc}, turnOnSoc: {self.turnOnSoc}, fake-soc: {fakesoc}")
        self._dbusservice[ "/Soc" ] = fakesoc
        return True

    def addBatteryWrapper(self, batt):
        return exit_on_error(self.addBattery, batt)

    def addBattery(self, batt):

        logger.info(f"add battery, waiting for /Soc...")
        soc = self.maindbusmon.get_value(batt, "/Soc")

        logger.info(f"got /Soc: {soc}")

        # Sometimes we get None and sometimes a "dbus.Array([], signature=dbus.Signature('i')"
        # value for a None-value on the sender side?
        if soc == None or type(soc) == dbus.Array:
            return True

        logger.info(f"newbatt: initializing new dbus monitor for {batt}")

        allvalues = self.maindbusmon.dbusConn.call_blocking(batt, '/', None, 'GetValue', '', [])
        for key in allvalues:
            fqnkey = "/"+key
            if key in self.ignorePath or fqnkey in self.monitorlist:
                continue
            self.monitorlist[fqnkey] = dummy

        logger.info(f"newbatt: watching {len(self.monitorlist)} items of {batt}: {self.monitorlist.keys()}")
        dbusmon = MyDbusMonitor({ batt: self.monitorlist },
                valueChangedCallback=self.value_changed_wrapper)

        self.batteries[batt] = battery(dbusmon, batt)

        for fqnkey in self.monitorlist:
            if fqnkey in self.ignorePath:
                continue
            if fqnkey not in self._dbusservice:
                self._dbusservice.add_path(
                        fqnkey,
                        None,
                        gettextcallback=self.getTextCallbacks.get(fqnkey, None))
            self.publishValue(batt, fqnkey, allvalues[fqnkey[1:]])

        return False

    def value_changed(self, service, path, options, changes, deviceInstance):
        self.publishValue(service, path, changes["Value"])

    def publishValue(self, service, path, value):

        # logger.info(f'publishValue: {service} {path} {value} {type(value)}')

        if service not in self.batteries:
            logger.info(f"skipping publishValue: early notification...")
            return

        spath = path[1:]

        if spath in self.ownPath:
            # skip
            return

        iv = 0
        lv = []
        sv = ""
        v = None
        vt = type(value)
        if spath in self.addPath:

            for batt in self.batteries:

                battvalue = self.batteries[batt].get_value(path)

                if batt == service:
                    # logger.info(f"add new value {batt} {path} {value}")
                    v = value
                else:
                    # logger.info(f"add old value {batt} {path} {battvalue}")
                    v = battvalue

                if vt == int or vt == float or vt == dbus.Double or vt == dbus.Int32:
                    iv += v
                elif vt == dbus.Array:
                    lv += v
                elif vt == dbus.String:
                    sv += v
                else:
                    logger.info(f"unknown type: {vt}")
                    assert(0)

            if vt == dbus.Array:
                # logger.info(f"sum value {batt} {path} {lv}")
                self._dbusservice[path] = lv
            elif vt == dbus.String:
                # logger.info(f"sum value {batt} {path} {sv}")
                self._dbusservice[path] = sv
            else: # vt == int or vt == float or vt == dbus.Double or vt == dbus.Int32:
                # logger.info(f"sum value {batt} {path} {iv}")
                self._dbusservice[path] = iv

        elif spath in self.avgPath:

            for batt in self.batteries:
                if batt == service:
                    iv += value
                else:
                    iv += self.batteries[batt].get_value(path)

            iv /= len(self.batteries)
            # logger.info(f"avg value {batt} {path} {round(iv, 3)}")
            self._dbusservice[path] = round(iv, 3)

        elif spath in self.maxPath:

            for batt in self.batteries:
                if batt == service:
                    iv = max(iv, value)
                else:
                    iv = max(iv, self.batteries[batt].get_value(path))

            # logger.info(f"max value {batt} {path} {iv}")
            self._dbusservice[path] = iv

        elif spath in self.minPath:

            iv = 0xffffffff
            for batt in self.batteries:
                if batt == service:
                    iv = min(iv, value)
                else:
                    iv = min(iv, self.batteries[batt].get_value(path))

            # logger.info(f"min value {batt} {path} {iv}")
            self._dbusservice[path] = iv

        elif spath in self.allsetPath:

            iv = 1
            for batt in self.batteries:
                if batt == service:
                    if not value:
                        iv = 0
                else:
                    if not self.batteries[batt].get_value(path):
                        iv = 0

            # logger.info(f"allset value {batt} {path} {iv}")
            self._dbusservice[path] = iv

        elif spath in self.onesetPath:

            iv = 0
            for batt in self.batteries:
                if batt == service:
                    if value:
                        iv = 1
                        break
                else:
                    if self.batteries[batt].get_value(path):
                        iv = 1
                        break

            # logger.info(f"oneset value {batt} {path} {iv}")
            self._dbusservice[path] = iv

        else:
            # logger.info(f"copy single value from {service}: {path} {value}")
            self._dbusservice[path] = value

        return

    def forceSocChanged(self, path, force):
        logger.info(f"forcesoc: {path}, {force}, {type(force)}")
        self._dbusservice[path] = force
        self.forceSoc = force


# ################
# ## Main loop ###
# ################
def main():

    from dbusmonitor import DbusMonitor

    logger.info("%s: Starting ibr bms service." % (datetime.datetime.now()).strftime("%c"))
    from dbus.mainloop.glib import DBusGMainLoop

    DBusGMainLoop(set_as_default=True)

    DbusAggBatService()

    logger.info(
        "%s: Connected to DBus, and switching over to GLib.MainLoop()"
        % (datetime.datetime.now()).strftime("%c")
    )
    mainloop = GLib.MainLoop()
    mainloop.run()


if __name__ == "__main__":
    main()


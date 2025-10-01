# -*- coding: utf-8 -*-

import math, time, random
from datetime import timedelta

#
# eve standard charge:
# * 0.5C charging current
# * 3.65V charging voltage
# * 0.05C cut off current
#
THTime = 60 # [s]

from config import *
from utils import *

C50 = BATTERY_CAPACITY / 2
CUTOFFCURR = BATTERY_CAPACITY*0.05 # [A]

logger.info(f"CUTOFFCURR: {CUTOFFCURR}")

class ValueTimer(object):
    def __init__(self, name, th_secs):
        self.name = name
        self.th = th_secs
        self._ok = False
        self.reset()
    def add(self, v):
        if not self.value:
            logger.info(f"state {self.name}: begin counting")
        self.value += v
        if not self._ok and self.value > self.th:
            logger.info(f"state of value {self.name} changed to True ({self.value}s)")
            self._ok = True
    def ok(self):
        return self._ok
    def reset(self):
        if self._ok:
            logger.info(f"state of value {self.name} changed to False ({self.value}s)")
            self._ok = False
        self.value = 0
    def stateStr(self):
        return f"{self.value}/{self.th}"

class State(object):
    def __init__(self, name):
        self.name = name

# Error cell-voltage from bms
# measureoffs = 0.005
# u0 = 3.375 # i=0
cellu0 = 3.375 # + measureoffs
umax = 3.5

cellpull = cellu0 + 0.010
cellfloat = cellu0 - 0.010

vrange = umax - cellpull

MAX_CHARGING_CELL_VOLTAGE = 3.55
MAX_CHARGING_VOLTAGE = umax*16 # XXX hardcoded number of cells

STATEBULK  = 0
STATEBAL   = 1
STATESINK  = 2
STATEFLOAT = 3

class Protection(object):
    # 2 = Alarm, 1 = Warning, 0 = Normal
    def __init__(self):
        self.voltage_high = None
        self.voltage_low = None
        self.voltage_cell_low = None
        self.soc_low = None
        self.current_over = None
        self.current_under = None
        self.cell_imbalance = None
        self.internal_failure = None
        self.temp_high_charge = None
        self.temp_low_charge = None
        self.temp_high_discharge = None
        self.temp_low_discharge = None


class Cell:
    voltage = None
    balance = None

    def __init__(self, balance):
        self.balance = balance


class Battery(object):

    def __init__(self, port, baud):
        self.port = port
        self.baud_rate = baud
        self.role = 'battery'
        self.type = 'Generic'
        self.poll_interval = 1000 # mS # xxx overwritten in Battery subclass (Daliy)

        self.hardware_version = None
        self.voltage = None
        self.current = None
        self.capacity_remain = None
        self.capacity = None
        self.cycles = None
        self.total_ah_drawn = None

        self.production = None
        self.protection = Protection()
        self.version = None
        self.soc = None
        self.charge_fet = None
        self.discharge_fet = None
        self.cell_count = None
        self.temperatures = 3 * [0]
        self.cells = []
        # self.control_voltage = None
        # self.control_discharge_current = None # xxx remove me: not set in daly.py:get_settings()
        # self.timeToGo = 0
        # self.control_charge_current = None
        self.control_allow_charge = True
        self.control_allow_discharge = True
        # max battery charge/discharge current
        self.max_battery_current = None
        self.max_battery_discharge_current = C50 # initial value
        
        # charging/balancing
        self.throttling = None # xxx remove

    def test_connection(self):
        # Each driver must override this function to test if a connection can be made
        # return false when fail, true if successful
        return False

    def get_settings(self):
        # Each driver must override this function to read/set the battery settings
        # It is called once after a successful connection by DbusHelper.setup_vedbus()
        # Values:  battery_type, version, hardware_version, min_battery_voltage, max_battery_voltage,
        #   MAX_BATTERY_CURRENT, MAX_BATTERY_DISCHARGE_CURRENT, cell_count, capacity
        # return false when fail, true if successful
        return False

    def refresh_data(self):
        # Each driver must override this function to read battery data and populate this class
        # It is called each poll just before the data is published to vedbus
        # return false when fail, true if successful
        return False

    def get_capacity_remain(self):
        if self.capacity_remain is not None:
            return self.capacity_remain
        if self.capacity is not None and self.soc is not None:
            return self.capacity * self.soc / 100
        return None

    def get_min_cell_voltage(self):
        min_voltage = None
        if hasattr(self, 'cell_min_voltage'):
            min_voltage = self.cell_min_voltage

        if min_voltage is None:
            try:
                min_voltage = min(c.voltage for c in self.cells if c.voltage is not None)
            except ValueError:
                pass
        return min_voltage

    def get_max_cell_voltage(self):
        max_voltage = None
        if hasattr(self, 'cell_max_voltage'):
            max_voltage = self.cell_max_voltage

        if max_voltage is None:
            try:
                max_voltage = max(c.voltage for c in self.cells if c.voltage is not None)
            except ValueError:
                pass
        return max_voltage

    def get_temp(self):
        return sum(self.temperatures) / len(self.temperatures)

    def get_min_temp(self):
        return min(self.temperatures)

    def get_max_temp(self):
        return min(self.temperatures)

    def log_cell_data(self):
        if logger.getEffectiveLevel() > logging.INFO and len(self.cells) == 0:
            return False

        cell_res = ""
        cell_counter = 1
        for c in self.cells:
            cell_res += "[{0}]{1}V ".format(cell_counter, c.voltage)
            cell_counter = cell_counter + 1
        logger.debug("Cells:" + cell_res)
        return True

    def log_settings(self):
        
        logger.info(f'Battery connected to dbus from {self.port}')
        logger.info(f'=== Settings ===')
        cell_counter = len(self.cells)
        logger.info(f'> Connection voltage {self.voltage}V | current {self.current}A | SOC {self.soc}%')
        logger.info(f'> Cell count {self.cell_count} | cells populated {cell_counter}')
        logger.info(f'> CCL Charge {self.max_battery_current}A | DCL Discharge {self.max_battery_discharge_current}A')
        logger.info(f'> MIN_CELL_VOLTAGE {MIN_CELL_VOLTAGE}V | MAX_CELL_VOLTAGE {MAX_CELL_VOLTAGE}V')
  
        return









if __name__ == "__main__":
    pass

# -*- coding: utf-8 -*-

# Constants - Need to dynamically get them in future
DRIVER_VERSION = 0.12
DRIVER_SUBVERSION = 'b3'

# battery Current limits
MAX_BATTERY_CURRENT = 50.0
MAX_BATTERY_DISCHARGE_CURRENT = 60.0

# Some daly bms have a very unsteady current measurement, enable
# this to average the current values from bms.
SMOOTH_BMS_CURRENT = True

#
# CCCM, CVL, CCL, DCL, CVCL
# 
# Charge voltage control management enable (True/False). 
CVCM_ENABLE = True
# Cell min/max voltages - used with the cell count to get the min/max battery voltage
MIN_CELL_VOLTAGE = 3.0
# pv charger control
MAX_CELL_VOLTAGE = 3.45                       # CVCM_ENABLE max charging voltage
# Charging cellvoltage when to reconnect inverter (load)
RECONNECTCELLVOLTAGE = 3.3 # 52.8v
BALANCETIME = 120 # [s]

# Daly settings
# Battery capacity (amps) if the BMS does not support reading it 
BATTERY_CAPACITY = 50
# Invert Battery Current. Default non-inverted. Set to -1 to invert
INVERT_CURRENT_MEASUREMENT = -1

# Service name for debugging
SERVICENAME="battery"

#
# Import loal settings
#
try:
    from config_local import *
except ModuleNotFoundError:
    pass



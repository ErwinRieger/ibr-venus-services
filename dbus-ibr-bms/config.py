
# Time to wait after cells are balanced to
# enter floating state 
BALANCETIME = 5 * 60 # [s]

# Discharging, Cell voltage when to turn off battery.
# Note: dynamic cutoff voltage, allows up to 0.25v
# lower cell voltage when dischargecurrent is 1C.
MIN_CELL_VOLTAGE = 3.1

# Service name for debugging
SERVICENAME="battery"

#
# Import loal settings
#
try:
    from config_local import *
except ModuleNotFoundError:
    pass



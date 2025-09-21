
# Expected number of battery banks.
NUMBER_OF_BATTERIES = 1

# Battery capacity [Ah]
BATTERY_CAPACITY = (100*0.9)

# Time to wait after cells are balanced to
# enter floating state 
BALANCETIME = 5 * 60 # [s]

# Rename to "battery" to, ibrbatt is for debugging
SERVICENAME="ibrbatt"

#
# Import loal settings
#
try:
    from config.local import *
except ModuleNotFoundError:
    pass



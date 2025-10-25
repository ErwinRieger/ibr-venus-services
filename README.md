# ibr-venus-services

Note: Work in progress.

Some victron dbus services i use to run my victron installations.

* dbus-ibr-system: compute/aggregate some values and publish it on dbus.
  Values computed:
  + Entire daily PV Yield: "/TotalPVYield"
  + Battery load "/BattLoad": battery current of all inverters (inverter rs, multiplus 2)
  + MPPT charger state "/MppOperationMode"
* dbus-ibr-serialbat: serial battery driver for Daly or Felicity BMS's.
* dbus-ibr-bms: Aggregate values from (serial-) battery services,
  implements (lifepo4-) charging algorithm.
* dbus-ibr-mpcontrol: Turn on/off multiplus (in assisting mode).
* dbus-ibr-neeycontrol: Turn on/off neey active balancer(s), to implement
  a "balance-when-charged" charging/balancing.
* dbus-ibr-shelly-rsmulti: This service implements a "Zero-Export" ESS using a RS-Multi
  together with a Shelly 3EM pro smartmeter.
* dbus-ibr-loads: Control a kettle/boiler to use excess PV-power (using mqtt).
* dbus-ibr-rshack: Workaround to fix display loads and power consumption of my
  somewhat unusual setup.



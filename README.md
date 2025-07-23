# ibr-venus-services

Note: Work in progress.

Some victron dbus services i use to run my victron installations.

* dbus-ibr-system: compute/aggregate some values and publish it on dbus.
  Values computed:
  + Entire daily PV Yield: "/TotalPVYield"
  + Battery load "/BattLoad": battery current of all inverters (inverter rs, multiplus 2)
* dbus-ibr-serialbattery: serial battery driver for daly BMS.
* dbus-ibr-aggregate-battery: Aggregate values from (serial-) battery services,
  implements (lifepo-) charging algorithm.
* dbus-ibr-mpcontrol: Turn on/off multiplus (in assisting mode).
* dbus-ibr-neeycontrol: Turn on/off neey active balancer(s), to implement
  a "balance-when-charged" charging/balancing.


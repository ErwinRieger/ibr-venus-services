# -*- coding: utf-8 -*-
import sys
import os
import platform
import dbus

sys.path.insert(1, '/data/ibr-venus-services/common/python')
sys.path.insert(1, '/data/ibr-venus-services/common/velib_python')

from vedbus import VeDbusService
from settingsdevice import SettingsDevice
import battery
from config import *
from utils import logger

def get_bus():
    return dbus.SessionBus() if 'DBUS_SESSION_BUS_ADDRESS' in os.environ else dbus.SystemBus()

class DbusHelper:

    def __init__(self, battery):
        self.battery = battery
	# +10 to be above virtual aggregate BMS's for
	# automatatic DVCC and Battery Monitor detection
        self.instance = int(self.battery.port[-1]) + 15
        self.settings = None
        devport = self.battery.port[self.battery.port.rfind('/') + 1:]
        self._dbusservice = VeDbusService(f"com.victronenergy.{SERVICENAME}.{devport}", get_bus())

    def setup_instance(self):
        # bms_id = self.battery.production if self.battery.production is not None else \
        #     self.battery.port[self.battery.port.rfind('/') + 1:]
        bms_id = self.battery.port[self.battery.port.rfind('/') + 1:]
        path = '/Settings/Devices/ibrserialbatt_' + str(bms_id).replace(" ", "_")
        default_instance = 'battery:1'
        settings = {'instance': [path + '/ClassAndVrmInstance', default_instance, 0, 0], }

        self.settings = SettingsDevice(get_bus(), settings, self.handle_changed_setting)
        self.battery.role, self.battery.instance = self.get_role_instance()

    def get_role_instance(self):
        val = self.settings['instance'].split(':')
        logger.info("DeviceInstance = %d", int(val[1]))
        return val[0], int(val[1])

    def handle_changed_setting(self, setting, oldvalue, newvalue):
        if setting == 'instance':
            logger.info("Changed DeviceInstance = %d", self.instance)
            return

    def setup_vedbus(self):
        # Set up dbus service and device instance
        # and notify of all the attributes we intend to update
        # This is only called once when a battery is initiated
        self.setup_instance()
        short_port = self.battery.port[self.battery.port.rfind('/') + 1:]
        logger.info("%s" % ("com.victronenergy.battery." + short_port))

        # Get the settings for the battery
        if not self.battery.get_settings():
            return False

        # Create the management objects, as specified in the ccgx dbus-api document
        self._dbusservice.add_path('/Mgmt/ProcessName', __file__)
        self._dbusservice.add_path('/Mgmt/ProcessVersion', 'Python ' + platform.python_version())
        self._dbusservice.add_path('/Mgmt/Connection', 'Serial ' + self.battery.port)

        # Create the mandatory objects
        self._dbusservice.add_path('/DeviceInstance', self.instance)
        self._dbusservice.add_path('/ProductId', 0x0)
        self._dbusservice.add_path('/ProductName', 'IBR Serial Batt ({self.battery.type})')
        self._dbusservice.add_path('/FirmwareVersion', self.battery.version)
        self._dbusservice.add_path('/HardwareVersion', self.battery.hardware_version)
        self._dbusservice.add_path('/Connected', 1)

        # Create static battery info
        self._dbusservice.add_path('/Info/BatteryLowVoltage', self.battery.min_battery_voltage, writeable=True,
                                   gettextcallback=lambda p, v: "{:0.2f}V".format(v))
        self._dbusservice.add_path('/Info/MaxChargeVoltage', self.battery.max_battery_voltage, writeable=True,
                                   gettextcallback=lambda p, v: "{:0.2f}V".format(v))
        self._dbusservice.add_path('/Info/MaxChargeCurrent', self.battery.max_battery_current, writeable=True,
                                   gettextcallback=lambda p, v: "{:0.2f}A".format(v))
        self._dbusservice.add_path('/Info/MaxDischargeCurrent', self.battery.max_battery_discharge_current,
                                   writeable=True, gettextcallback=lambda p, v: "{:0.2f}A".format(v))
        self._dbusservice.add_path('/System/NrOfCellsPerBattery', self.battery.cell_count, writeable=True)
        self._dbusservice.add_path('/System/NrOfModulesOnline', 1, writeable=True)
        self._dbusservice.add_path('/System/NrOfModulesOffline', 0, writeable=True)
        self._dbusservice.add_path('/System/NrOfModulesBlockingCharge', None, writeable=True)
        self._dbusservice.add_path('/System/NrOfModulesBlockingDischarge', None, writeable=True)
        self._dbusservice.add_path('/Capacity', self.battery.get_capacity_remain(), writeable=True,
                                   gettextcallback=lambda p, v: "{:0.2f}Ah".format(v))
        self._dbusservice.add_path('/InstalledCapacity', self.battery.capacity, writeable=True,
                                   gettextcallback=lambda p, v: "{:0.0f}Ah".format(v))
        self._dbusservice.add_path('/ConsumedAmphours', None, writeable=True,
                                   gettextcallback=lambda p, v: "{:0.0f}Ah".format(v))
        # Not used at this stage
        # self._dbusservice.add_path('/System/MinTemperatureCellId', None, writeable=True)
        # self._dbusservice.add_path('/System/MaxTemperatureCellId', None, writeable=True)

        # Create SOC, DC and System items
        self._dbusservice.add_path('/Soc', None, writeable=True)
        self._dbusservice.add_path('/Dc/0/Voltage', None, writeable=True, gettextcallback=lambda p, v: "{:2.2f}V".format(v))
        self._dbusservice.add_path('/Dc/0/Current', None, writeable=True, gettextcallback=lambda p, v: "{:2.2f}A".format(v))
        self._dbusservice.add_path('/Dc/0/Power', None, writeable=True, gettextcallback=lambda p, v: "{:0.0f}W".format(v))
        self._dbusservice.add_path('/Dc/0/Temperature', None, writeable=True)

        # Create battery extras
        self._dbusservice.add_path('/System/MinCellTemperature', None, writeable=True)
        self._dbusservice.add_path('/System/MaxCellTemperature', None, writeable=True)
        self._dbusservice.add_path('/System/MaxCellVoltage', None, writeable=True,
                                   gettextcallback=lambda p, v: "{:0.3f}V".format(v))
        # self._dbusservice.add_path('/System/MaxVoltageCellId', None, writeable=True)
        self._dbusservice.add_path('/System/MinCellVoltage', None, writeable=True,
                                   gettextcallback=lambda p, v: "{:0.3f}V".format(v))
        # self._dbusservice.add_path('/System/MinVoltageCellId', None, writeable=True)
        self._dbusservice.add_path('/History/ChargeCycles', None, writeable=True)
        self._dbusservice.add_path('/History/TotalAhDrawn', None, writeable=True)
        self._dbusservice.add_path('/Ess/Throttling', None, writeable=True)

        self._dbusservice.add_path('/Io/AllowToCharge', 0, writeable=True)
        self._dbusservice.add_path('/Io/AllowToDischarge', 0, writeable=True)
        # self._dbusservice.add_path('/SystemSwitch',1,writeable=True)
        # self._dbusservice.add_path('/TimeToGo', self.battery.timeToGo, writeable=True)

        # Create the alarms
        self._dbusservice.add_path('/Alarms/LowVoltage', None, writeable=True)
        self._dbusservice.add_path('/Alarms/HighVoltage', None, writeable=True)
        self._dbusservice.add_path('/Alarms/LowCellVoltage', None, writeable=True)
        self._dbusservice.add_path('/Alarms/HighCellVoltage', None, writeable=True)
        self._dbusservice.add_path('/Alarms/LowSoc', None, writeable=True)
        self._dbusservice.add_path('/Alarms/HighChargeCurrent', None, writeable=True)
        self._dbusservice.add_path('/Alarms/HighDischargeCurrent', None, writeable=True)
        self._dbusservice.add_path('/Alarms/CellImbalance', None, writeable=True)
        self._dbusservice.add_path('/Alarms/InternalFailure', None, writeable=True)
        self._dbusservice.add_path('/Alarms/HighChargeTemperature', None, writeable=True)
        self._dbusservice.add_path('/Alarms/LowChargeTemperature', None, writeable=True)
        self._dbusservice.add_path('/Alarms/HighTemperature', None, writeable=True)
        self._dbusservice.add_path('/Alarms/LowTemperature', None, writeable=True)

        #cell voltages
        # for i in range(1, self.battery.cell_count+1):
            # cellpath = '/Voltages/Cell%s'
            # self._dbusservice.add_path(cellpath%(str(i)), None, writeable=True, gettextcallback=lambda p, v: "{:0.3f}V".format(v))
        pathbase = 'Voltages'
        # self._dbusservice.add_path('/%s/Sum'%pathbase, None, writeable=True, gettextcallback=lambda p, v: "{:2.2f}V".format(v))
        self._dbusservice.add_path('/%s/Diff'%pathbase, None, writeable=True, gettextcallback=lambda p, v: "{:0.3f}V".format(v))

        return True

    def publish_battery(self, loop):
        # This is called every battery.poll_interval milli second as set up per battery type to read and update the data
        # logger.info("*** PUBLISH_BATTERY ***\n")
        try:
            error_count = 0
            # Call the battery's refresh_data function
            success = self.battery.refresh_data()
            if success:
                error_count = 0
            else:
                error_count += 1
                # If the battery is offline for more than 10 polls (polled every second for most batteries)
                if error_count >= 10: 
                    logger.warning("publish_battery: to many comm. errors, restarting...")
                    loop.quit()
                    return False

            # publish all the data fro the battery object to dbus
            self.publish_dbus()

        except OSError as e:
            logger.exception(e)
            if e.errno == 5:
                logger.error("publish_battery(): caught OSError (Input/output error) exception, restarting...")
                loop.quit()
                return False
            logger.error(f"publish_battery(): un-caught OSError exception, errno: {e.errno} restarting...")
            loop.quit()
            return False
        except Exception as e:
            logger.exception(e)
            logger.warning("publish_battery: un-caught exception, restarting...")
            loop.quit()
            return False


        # logger.info("*** end ***")
        return True

    def publish_dbus(self):

        # Update SOC, DC and System items
        self._dbusservice['/System/NrOfCellsPerBattery'] = self.battery.cell_count
        self._dbusservice['/Soc'] = round(self.battery.soc, 2)
        self._dbusservice['/Dc/0/Voltage'] = self.battery.voltage
        self._dbusservice['/Dc/0/Current'] = self.battery.current
        self._dbusservice['/Dc/0/Power'] = self.battery.voltage * self.battery.current
        self._dbusservice['/Dc/0/Temperature'] = self.battery.get_temp()
        self._dbusservice['/Capacity'] = self.battery.get_capacity_remain()
        self._dbusservice['/ConsumedAmphours'] = 0 if self.battery.capacity is None or \
                                self.battery.get_capacity_remain() is None else \
                                self.battery.capacity - self.battery.get_capacity_remain()
        
        # Update battery extras
        self._dbusservice['/History/ChargeCycles'] = self.battery.cycles
        self._dbusservice['/History/TotalAhDrawn'] = self.battery.total_ah_drawn

        allow_charge =    self.battery.charge_fet and self.battery.control_allow_charge
        allow_discharge = self.battery.discharge_fet and self.battery.control_allow_discharge

        self._dbusservice['/Io/AllowToCharge'] = 1 if allow_charge else 0
        self._dbusservice['/Io/AllowToDischarge'] = 1 if allow_discharge else 0
        # self._dbusservice['/TimeToGo'] = self.battery.timeToGo

        self._dbusservice['/System/NrOfModulesBlockingCharge'] = 0 if allow_charge else 1
        self._dbusservice['/System/NrOfModulesBlockingDischarge'] = 0 if allow_discharge else 1

        self._dbusservice['/System/NrOfModulesOnline'] = 1 
        self._dbusservice['/System/NrOfModulesOffline'] = 0 
        self._dbusservice['/System/MinCellTemperature'] = self.battery.get_min_temp()
        self._dbusservice['/System/MaxCellTemperature'] = self.battery.get_max_temp()

        # Charge control
        # self._dbusservice['/Info/MaxChargeCurrent'] = self.battery.control_charge_current
        # self._dbusservice['/Info/MaxDischargeCurrent'] = self.battery.control_discharge_current

        # Voltage control
        # self._dbusservice['/Info/BatteryLowVoltage'] = self.battery.min_battery_voltage
        # self._dbusservice['/Info/MaxChargeVoltage'] = self.battery.control_voltage
        
        # Updates from cells
        # self._dbusservice['/System/MinVoltageCellId'] = self.battery.get_min_cell_desc()
        # self._dbusservice['/System/MaxVoltageCellId'] = self.battery.get_max_cell_desc()
        self._dbusservice['/System/MinCellVoltage'] = self.battery.get_min_cell_voltage()
        self._dbusservice['/System/MaxCellVoltage'] = self.battery.get_max_cell_voltage()
        self._dbusservice['/Ess/Throttling'] = self.battery.throttling

        # Update the alarms
        self._dbusservice['/Alarms/LowVoltage'] = self.battery.protection.voltage_low
        self._dbusservice['/Alarms/LowCellVoltage'] = self.battery.protection.voltage_cell_low
        self._dbusservice['/Alarms/HighVoltage'] = self.battery.protection.voltage_high
        self._dbusservice['/Alarms/LowSoc'] = self.battery.protection.soc_low
        self._dbusservice['/Alarms/HighChargeCurrent'] = self.battery.protection.current_over
        self._dbusservice['/Alarms/HighDischargeCurrent'] = self.battery.protection.current_under
        self._dbusservice['/Alarms/CellImbalance'] = self.battery.protection.cell_imbalance
        self._dbusservice['/Alarms/InternalFailure'] = self.battery.protection.internal_failure
        self._dbusservice['/Alarms/HighChargeTemperature'] = self.battery.protection.temp_high_charge
        self._dbusservice['/Alarms/LowChargeTemperature'] = self.battery.protection.temp_low_charge
        self._dbusservice['/Alarms/HighTemperature'] = self.battery.protection.temp_high_discharge
        self._dbusservice['/Alarms/LowTemperature'] = self.battery.protection.temp_low_discharge

        #cell voltages
        # voltageSum = 0
        # for i in range(self.battery.cell_count):
            # voltage = self.battery.get_cell_voltage(i)
            # cellpath = '/Voltages/Cell%s'
            # self._dbusservice[cellpath%(str(i+1))] = voltage
            # if voltage:
                # voltageSum+=voltage
        pathbase = 'Voltages'
        # self._dbusservice['/%s/Sum'%pathbase] = voltageSum
        self._dbusservice['/%s/Diff'%pathbase] = self.battery.get_max_cell_voltage() - self.battery.get_min_cell_voltage()

        logger.debug("logged to dbus [%s]"%str(round(self.battery.soc, 2)))
        self.battery.log_cell_data()

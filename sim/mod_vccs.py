
from venus_service_utils import expfilter
from module_base import ModuleBase

class vccs(ModuleBase):
    """
    Voltage Controlled Current Source (VCCS).
    Basisklasse für Spannungs-/Stromquellen (Netzteil, Laderegler).
    Simuliert eine CCCV-Quelle, die Strom liefert, bis eine Zielspannung erreicht ist.
    """
    def __init__(self, name, config, time_step):
        super().__init__(name, config, time_step)
        self.type = 'vccs' # Identifikator
        
        # Hardware-Limits aus Config
        self.max_voltage = float(config.get('max_voltage', 58.0)) # Hardware Limit [V]
        self.max_current = float(config.get('max_current', 50.0)) # Hardware Limit [A]
        self.r_connect = float(config.get('r_connect', 0.002)) # Anschlusswiderstand [Ohm]
        
        # Startverzögerung
        t_start_str = config.get('t_start', '0')
        self.delay_seconds = 0.0
        
        if t_start_str.endswith('%'):
            try:
                # Versuch Zugriff auf Global via Parser-Referenz
                # config ist ein SectionProxy, config.parser der ConfigParser
                t_sim = float(config.parser['Global'].get('t_simulation', 3600))
                percent = float(t_start_str.rstrip('%'))
                self.delay_seconds = t_sim * (percent / 100.0)
            except Exception as e:
                print(f"Warnung: Konnte t_start Prozentwert nicht auflösen: {e}")
                self.delay_seconds = 0.0
        else:
            self.delay_seconds = float(t_start_str)
            
        self._elapsed_time = 0.0
        
        self._current_output = 0.0
        self._power = 0.0
        self._u_bus = 0.0 # Zuletzt gesehene Busspannung

        self.cfilter = expfilter(0, 0.33, 0, self.max_current)

    def step(self, bus_voltage, ccl):
        """
        Berechnet den Strom, den die Quelle bei gegebener Busspannung liefert.
        Respektiert Hardware-Limits UND System-DVCC-Limits.
        """
        self._elapsed_time += self.time_step
        if self._elapsed_time < self.delay_seconds:
            self._u_bus = bus_voltage
            self._current_output = 0.0
            self._power = 0.0
            return 0.0

        self._u_bus = bus_voltage
        u_drop = self._current_output * self.r_connect
        u_int = bus_voltage + u_drop
        
        # 1. Limits ermitteln
        sys_cvl = self.system.get_value('/Info/MaxChargeVoltage')
            
        # Effektive Limits (Minimum aus Hardware & System)
        target_v = self.max_voltage
        if sys_cvl is not None:
            target_v = min(target_v, sys_cvl)
            
        limit_i = self.max_current
        if ccl is not None:
            limit_i = min(limit_i, ccl)
            
        self.cfilter.maxvalue = limit_i

        # Proportionale anpassung
        diff = target_v - u_int

        self.cfilter.filter(self.cfilter.value + diff*self.time_step) # 1A/sec

        self._current_output = self.cfilter.value

        self._power = u_int * self._current_output
        
        self.warnImpedance(u_drop)
            
        batteries = self.system.get_modules_by_type('battery')
        
        u_batt_min = 2 * self.max_voltage
        if batteries:
            for bat in batteries:
                metrics = bat.get_metrics()
                u_batt_min = min(u_batt_min, metrics['u_int'])

        self.warnImpedance(u_int - u_batt_min, limit=0.5, idx=1, msg="Charger <-> Battery")

        return self._current_output

    def get_metrics(self):
        u_int = self._u_bus + self._current_output * self.r_connect
        return {
            'i': self._current_output,
            'p': self._power,
            'u_target': self.max_voltage,
            'i_limit': self.max_current,
            'u_bus': self._u_bus,
            'u_r_connect': self._current_output * self.r_connect,
            'u_int': u_int
        }

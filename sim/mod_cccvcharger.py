from mod_bms import bms
from pid import PID
from venus_service_utils import expfilter

class cccvcharger(bms):
    """
    Implementiert einen generischen CCCV Ladealgorithmus (Bulk, Absorption, Float).
    Steuert CVL und CCL basierend auf Zellspannungen und Zeit.
    """
    def __init__(self, name, config, time_step):
        super().__init__(name, config, time_step)
        
        # Parameter für den Algorithmus
        self.bulk_voltage = float(config.get('bulk_voltage', 55.2))
        self.float_voltage = float(config.get('float_voltage', 54.0))
        self.absorption_time = float(config.get('absorption_time', 3600)) # Sekunden
        self.rebulk_offset = float(config.get('rebulk_offset', 1.0)) # V unter Float
        
        # Interner Zustand
        self.state = 0 # 0=Off, 1=Bulk, 2=Absorb, 3=Float
        
        # Override Standard-Limits aus Basisklasse
        # self.cvl = self.bulk_voltage

        self.target = self.bulk_voltage
        self.cclfilter = expfilter(25, 0.1, 0, 50) # xxx max current hardcoded

        # self.voltagePid = PID(1, 0.1, 0, min_out=self.float_voltage-1.5, max_out=self.bulk_voltage+1.5)
        self.voltagePid = PID(1, 1, 50, min_out=45, max_out=self.bulk_voltage+0.5) # 0.25v for r_connect and 0.25v for r_conect battery.

    def step(self):
        # 1. Daten sammeln (via System)
      
        batteries = self.system.get_modules_by_type('battery')
        
        u_batt_max = 0.0
        # u_batt_min = 2 * self.bulk_voltage
        i_batt_min = 50 # xxx our or batteries max charge current

        if batteries:
            for bat in batteries:
                metrics = bat.get_metrics()
                print("metrics: ", metrics["u_int"])
                u_batt_max = max(u_batt_max, metrics['u_int'])
                # u_batt_min = min(u_batt_min, metrics['u_int'])
                i_batt_min = min(i_batt_min, metrics['i'])

        pidout = self.voltagePid.step(self.target, u_batt_max, self.time_step)

        print(f"target: {self.target}, u_batt: {u_batt_max}, pidout: {pidout}")

        e = self.target - u_batt_max

        self.cclfilter.filter(self.cclfilter.value+max(e*self.time_step, 0))

        if e<0 and i_batt_min < (50*0.05): # hardocde end current
            self.cvl = 0
            self.ccl = 0
        else:
            self.cvl = pidout
            self.ccl = max(self.cclfilter.value, 10) # (50*0.05)) # hardcoded

        print(f"i_batt_min: {i_batt_min}, ccfitler: {self.cclfilter.value}, delta: {e*self.time_step}, ccl: {self.ccl}")

        # 3. Limits anwenden
        # Ruft Basis-Methode auf, die self.sources steuert
        super().step()

    def get_metrics(self):
        m = super().get_metrics()
        m['state'] = self.state
        return m

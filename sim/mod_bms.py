from module_base import ModuleBase

class bms(ModuleBase):
    """
    Basisklasse für Battery Management Systeme.
    Regelt DVCC Limits basierend auf Batteriezustand.
    """
    def __init__(self, name, config, time_step):
        super().__init__(name, config, time_step)
        self.type = 'bms'
        
        # DVCC Sollwerte
        self.cvl = float(config.get('cvl', 55.2)) # Charge Voltage Limit
        self.ccl = float(config.get('ccl', 100.0)) # Charge Current Limit
        self.dcl = float(config.get('dcl', 200.0)) # Discharge Current Limit

    def step(self):
        """
        Hauptzyklus des BMS.
        1. Zustand der Batterien erfassen (Aggregation via System).
        2. Limits berechnen.
        3. Limits via System/DVCC setzen.
        """
        if not self.system: return

        # 1. Aggregation (Beispiel: Max Zellspannung finden)
        u_cell_max = 0.0
        soc_avg = 0.0
        
        batteries = self.system.get_modules_by_type('battery')
        
        if batteries:
            for bat in batteries:
                metrics = bat.get_metrics() # Dictionary abrufen
                # Wir suchen nach 'u_max' in den Metriken
                u_cell_max = max(u_cell_max, metrics['u_max'])
                soc_avg += metrics['soc']
            soc_avg /= len(batteries)

        # 2. Logik (kann in Subklassen überschrieben werden)
        # Hier: Einfaches Durchreichen der konfigurierten Limits
        
        print("bms: write /Info/MaxChargeVoltage: ", self.cvl)

        # 3. Steuerung via System (DVCC)
        self.system.set_value('/Info/MaxChargeVoltage', self.cvl)
        self.system.set_value('/Info/MaxChargeCurrent', self.ccl)
        self.system.set_value('/Info/MaxDischargeCurrent', self.dcl)

    def get_metrics(self):
        return {
            'cvl': self.cvl,
            'ccl': self.ccl,
            'dcl': self.dcl
        }

class DCBus:
    def __init__(self, time_step):
        self.time_step = time_step
        self.batteries = []
        self.chargers = []
        self.voltage = 0.0
        self.total_current = 0.0

    def register_battery(self, battery):
        self.batteries.append(battery)
        # Initiale Spannung setzen, falls erste Batterie
        if len(self.batteries) == 1:
            self.voltage = battery.u()

    def register_charger(self, charger):
        self.chargers.append(charger)

    def step(self):
        # 1. Alle Quellen/Senken berechnen ihren Wunsch-Strom basierend auf aktueller Spannung
        current_sum = 0.0
        
        for chg in self.chargers:
            current_sum += chg.step(self.voltage)
            
        # 2. Summenstrom auf Batterien verteilen
        if self.batteries:
            # Vereinfacht: Gleichmäßige Verteilung
            i_per_bat = current_sum / len(self.batteries)
            
            v_avg = 0.0
            for bat in self.batteries:
                v_avg += bat.step(i_per_bat)
            
            # Neue Busspannung
            self.voltage = v_avg / len(self.batteries)
            
        else:
            self.voltage = 0.0

        self.total_current = current_sum
        return self.voltage, self.total_current
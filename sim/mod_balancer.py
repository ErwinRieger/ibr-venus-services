from module_base import ModuleBase

class balancer(ModuleBase):
    """
    Simuliert einen aktiven Balancer, der Energie zwischen den Zellen umverteilt.
    """
    def __init__(self, name, config, time_step):
        super().__init__(name, config, time_step)
        self.type = 'balancer'
        
        # Parameter aus der Config laden (entsprechend modules.md)
        self.max_current = float(config.get('current', 4.0)) # [A]
        self.run_voltage_diff = float(config.get('runVoltage', 0.010)) # [V]
        self.start_voltage = float(config.get('startVoltage', 3.40)) # [V]
        self.stop_voltage = float(config.get('stopVoltage', 3.30)) # [V]
        
        # Referenz auf die zu balancierende Batterie
        self.target_battery_name = config.get('battery', 'Battery1')
        self.target_battery = None 
        self.system = None

        self.is_running = False
        self.current_flow = 0.0
        self._last_u_diff = 0.0

    def step(self, bus_voltage=None):
        # Dynamische Auflösung der Batterie via System
        if self.target_battery is None and self.system:
            if self.target_battery_name in self.system.modules:
                self.target_battery = self.system.modules[self.target_battery_name]
        
        if not self.target_battery:
            return 0.0
        
        cells = self.target_battery.cells
        voltages = [c.u() for c in cells]
        u_max = max(voltages)
        u_min = min(voltages)
        u_diff = u_max - u_min
        self._last_u_diff = u_diff
        
        # Hysterese und Start-Bedingung
        if not self.is_running:
            if u_diff > self.run_voltage_diff and u_max >= self.start_voltage:
                self.is_running = True
        else:
            if u_diff < (self.run_voltage_diff * 0.5) or u_max < self.stop_voltage:
                self.is_running = False
        
        if self.is_running:
            # Finde Index der höchsten und niedrigsten Zelle
            idx_max = voltages.index(u_max)
            idx_min = voltages.index(u_min)
            
            # Stromfluss berechnen (Ah Transfer)
            # Wir "entnehmen" der vollen Zelle Strom und "geben" ihn der leeren Zelle.
            # Da wir ah_loss in cell.step() haben, ist ein direkter Transfer von Ah sinnvoll.
            # In der Realität hat ein Balancer Wirkungsgradverluste, hier erst mal idealer Transfer.
            
            # cell.step() wird in battery.step() aufgerufen. 
            # Der Balancer sollte den Strom ZUSÄTZLICH zum Bus-Strom auf die Zellen geben.
            # PROBLEM: cell.step(input_current) wird von battery.step() aufgerufen.
            # Wir müssen den Balancer-Strom VOR dem battery.step() anwenden oder die Zellen direkt manipulieren.
            
            # Da sim.py erst bus.step() aufruft (was battery.step() triggert), 
            # manipulieren wir hier die Energie direkt (Ah = I * dt).
            ah_to_move = self.max_current * (self.time_step / 3600.0)
            
            cells[idx_max].energy -= ah_to_move
            cells[idx_min].energy += ah_to_move
            self.current_flow = self.max_current
        else:
            self.current_flow = 0.0
            
        return 0.0 # Der Balancer verbraucht/liefert keinen Strom zum DC-Bus (Idealisiert)

    def get_metrics(self):
        return {
            'i': self.current_flow,
            'u_diff': self._last_u_diff,
            'active': 1 if self.is_running else 0
        }

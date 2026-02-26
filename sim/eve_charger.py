class Charger:
    def __init__(self, name, config, time_step):
        self.name = name
        self.time_step = time_step
        self.max_current = float(config.get('max_current', 10.0))
        self.num_cells = int(config.get('cells', 16))
        
        self.target_v_cell = 3.45
        self.cv_window = 0.05
        self.current = 0.0

    def step(self, bus_voltage):
        # Schätzung der Zellspannung (ignoriert r_connect Abfall, was real ist: 
        # der Lader misst an seinen Klemmen, also am Bus)
        u_cell = bus_voltage / self.num_cells
        
        if u_cell >= self.target_v_cell:
            # Über Zielspannung: Strom drastisch reduzieren
            excess = u_cell - self.target_v_cell
            factor = max(0, 1.0 - (excess / 0.01))
            self.current *= factor
            
        elif u_cell > (self.target_v_cell - self.cv_window):
            # CV-Annäherung: Linear runterregeln
            dist = self.target_v_cell - u_cell
            target_i = self.max_current * (dist / self.cv_window)
            # Soft-Übergang: Minimum aus bisherigem und neuem Ziel
            self.current = min(self.max_current, target_i)
            
        else:
            # CC-Phase
            self.current = self.max_current
            
        return self.current
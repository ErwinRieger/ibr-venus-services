from cell import LifepoCell

class Battery:
    def __init__(self, name, config, time_step):
        self.name = name
        self.time_step = time_step
        
        self.capacity = float(config.get('capacity', 280))
        self.num_cells = int(config.get('cells', 16))
        self.r_connect = float(config.get('r_connect', 0.02))
        initial_soc = float(config.get('initial_soc', 20))
        
        # Zellparameter
        r0 = 0.00025
        r1 = 0.0005
        cap_rc = 103000
        
        self.cells = [LifepoCell(r0, r1, cap_rc, self.time_step) for _ in range(self.num_cells)]
        
        # Start-SOC
        start_energy = (initial_soc / 100.0) * self.capacity
        for cell in self.cells:
            cell.energy = start_energy
            cell.step(0) # OCV berechnen

        self._voltage = self.get_internal_voltage()

    def step(self, current):
        # Alle Zellen sehen den gleichen Strom
        for cell in self.cells:
            # Achtung: cell.py step() braucht nur input_current, 
            # wenn wir dt fix im Konstruktor von LifepoCell übergeben haben.
            # Da cell.py von mir vorhin modifiziert wurde, um optional dt zu nehmen,
            # können wir es hier weglassen oder sicherheitshalber self.time_step übergeben.
            # Da wir in __init__ self.time_step übergeben haben, passt es ohne Argument.
            cell.step(current)
            
        self._voltage = self.get_internal_voltage() + (current * self.r_connect)
        return self._voltage

    def get_internal_voltage(self):
        return sum(cell.u() for cell in self.cells)

    def u(self):
        return self._voltage

    def soc(self):
        return sum(cell.soc() for cell in self.cells) / len(self.cells)
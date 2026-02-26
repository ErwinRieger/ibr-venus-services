import random
from cell import LifepoCell
from module_base import ModuleBase

class battery(ModuleBase):
    """
    Simuliert eine Batterie basierend auf Einzelzellen.
    Aggregiert Spannung/Strom der Zellen.
    """
    def __init__(self, name, config, time_step, parameter_defaults=None):
        super().__init__(name, config, time_step)
        self.type = 'battery'
        
        if parameter_defaults is None: parameter_defaults = {}

        def get_val(key, fallback):
            # Priorität: Config > Defaults-Argument > Hardcoded Fallback (100Ah)
            if key in config: return float(config[key])
            return parameter_defaults.get(key, fallback)

        self.capacity = get_val('capacity', 100.0) # Default 100Ah
        self.num_cells = int(config.get('cells', parameter_defaults.get('cells', 16)))
        self.r_connect = get_val('r_connect', 0.002)
        initial_soc = get_val('initial_soc', 20)
        
        # Zellparameter (Defaults für 100Ah)
        p = {
            'r0': get_val('r0', 0.0004),
            'r1': get_val('r1', 0.0003),
            'c1': get_val('c1', 66000),
            'r2': get_val('r2', 0.0004),
            'c2': get_val('c2', 500000),
            'r3': get_val('r3', 0.0006),
            'c3': get_val('c3', 3300000),
            'time_step': self.time_step,
            'initial_soc': initial_soc,
            'r_self': config.get('r_self', None)
        }
        if p['r_self'] is not None: p['r_self'] = float(p['r_self'])
        
        self.cells = [LifepoCell(self.capacity, **p) for _ in range(self.num_cells)]
        
        self._last_i = 0.0
        self._u_bus = self.get_internal_voltage()

    def step(self, current):
        self._last_i = current
        for cell in self.cells:
            cell.step(current)
            
        u_drop = current * self.r_connect
        self.warnImpedance(u_drop)

        self._u_bus = self.get_internal_voltage() + u_drop
        return self._u_bus

    def u_bus(self):
        return self._u_bus

    def get_thevenin_params(self):
        """Liefert (U_quelle, R_innen) für die Netzwerkanalyse."""
        u_source = 0.0
        r_total = self.r_connect
        
        for cell in self.cells:
            u_source += (cell.u0 + cell.u_rc_total)
            r_total += cell.r0
            
        return u_source, r_total

    def get_internal_voltage(self):
        return sum(cell.u() for cell in self.cells)

    def soc(self):
        return sum(cell.soc() for cell in self.cells) / len(self.cells)

    def get_metrics(self):
        cell_voltages = [c.u() for c in self.cells]
        m = {
            'u_bus': self._u_bus,
            'u_int': self.get_internal_voltage(),
            'i': self._last_i,
            'p': self._u_bus * self._last_i,
            'soc': self.soc(),
            'u_min': min(cell_voltages),
            'u_max': max(cell_voltages),
            'u_diff': max(cell_voltages) - min(cell_voltages),
            'u_r_connect': self._last_i * self.r_connect
        }
        # Einzelzellen und Details hinzufügen
        for idx, c in enumerate(self.cells):
            # 1. Standard-Spannung (mit Unterstrich für Kompatibilität zu 'cells' Gruppe)
            m[f'cell_{idx+1}'] = c.u()
            
            # 2. Neue Detail-Syntax (gemäß battery.md, z.B. cell1:u0)
            prefix = f'cell{idx+1}'
            m[f'{prefix}:u0'] = c.u0
            m[f'{prefix}:uri'] = c.uri
            m[f'{prefix}:u_rc'] = c.u_rc_total
            m[f'{prefix}:p_loss'] = c.p_loss
            m[f'{prefix}:energy'] = c.energy
            
        return m

from mod_battery import battery

class battery280ah(battery):
    """
    Spezifische Batterie-Implementierung für 280Ah EVE LiFePO4 Zellen.
    Parameter sind skaliert basierend auf 100Ah Referenzwerten.
    """
    def __init__(self, name, config, time_step):
        # Defaults für 280Ah Zelle
        # Skalierung: R ~ 1/Kapazität, C ~ Kapazität
        defaults = {
            'capacity': 280.0,
            'r0': 0.00014, # ca. 0.14 mOhm
            'r1': 0.00011,
            'c1': 184800,
            'r2': 0.00014,
            'c2': 1400000,
            'r3': 0.00021,
            'c3': 9240000,
            'r_connect': 0.01 # Anschlusswiderstand bleibt Installationsabhängig, Default 10mOhm
        }
        
        super().__init__(name, config, time_step, parameter_defaults=defaults)

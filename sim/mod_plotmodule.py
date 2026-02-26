
import configparser
from module_base import ModuleBase

class plotmodule(ModuleBase):
    """
    Spezial-Modul zur Visualisierung von Zell-Details oder aggregierten Werten.
    Kann Daten von anderen Modulen abgreifen (z.B. Battery1.cell0:u).
    """
    def __init__(self, name, config, time_step):
        super().__init__(name, config, time_step)
        self.type = 'plot_module'

    def step(self, bus_voltage=None):
        # Passives Modul, tut nichts im Simulations-Loop
        pass

    def get_metrics(self):
        # Liefert keine eigenen Metriken zurück
        return {}

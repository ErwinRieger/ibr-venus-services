
class ModuleBase:
    """
    Basisklasse für Simulations-Module.
    Stellt gemeinsame Funktionalität wie Logging und Warnungen bereit.
    """
    def __init__(self, name, config, time_step):
        self.name = name
        self.time_step = time_step
        self.system = None # Wird vom System gesetzt (via register_module)
        
        # Status für Warnungen: Speichert Max-Werte pro Index
        self._maxList = {} 

    def warnImpedance(self, u_drop, limit=0.25, idx=0, msg=None):
        """
        Prüft den Spannungsabfall u_drop (an Messstelle idx).
        Warnt, wenn |u_drop| > limit UND |u_drop| > bisheriges Max an diesem Index.
        """
        val = abs(u_drop)
        
        # Initialisierung für diesen Index falls noch nicht vorhanden (Startwert = Limit)
        if idx not in self._maxList:
            self._maxList[idx] = 0
            
        if val > limit and val > self._maxList[idx]:
            if self.system:
                text = f"{self.name}: Hoher Spannungsabfall ({val:.2f}V)"
                if msg:
                    text += f" - {msg}"
                self.system.logWarn(text)
            self._maxList[idx] = val

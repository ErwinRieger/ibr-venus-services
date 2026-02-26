
class System:
    """
    Zentraler Hub für Simulation.
    - Registry für Module
    - Data-Bus (get_value / set_value) für Parameter und DVCC
    - Physik-Engine (Berechnung von Busspannung und Strömen)
    """
    def __init__(self, time_step):
        self.time_step = time_step
        self.modules = {}        # Name -> Objekt
        self.modules_by_type = {} # Typ -> [Objekte]
        self._log_callback = None
        
        # Zentraler Datenspeicher (Data-Bus)
        self._values = {
            '/Info/MaxChargeVoltage': None, # None = kein Limit
            '/Info/MaxChargeCurrent': None,
            '/Info/MaxDischargeCurrent': None
        }
        
        # Physik Zustand
        self.voltage = 0.0
        self.total_current = 0.0

    def set_log_callback(self, callback):
        """Registriert eine Funktion für Log-Ausgaben (z.B. GUI)."""
        self._log_callback = callback

    def log(self, message, level='Info'):
        """Sendet eine Nachricht an das Log-System. Level: Info, Warning, Error"""
        if self._log_callback:
            self._log_callback(message, level)
        else:
            print(f"[System][{level}] {message}")

    def logWarn(self, message):
        """Sendet eine Warnung."""
        self.log(message, level='Warning')

    def logError(self, message):
        """Sendet eine Fehlermeldung."""
        self.log(message, level='Error')

    def register_module(self, module):
        self.modules[module.name] = module
        if not hasattr(module, 'type'): module.type = 'unknown'
        
        if module.type not in self.modules_by_type:
            self.modules_by_type[module.type] = []
        self.modules_by_type[module.type].append(module)
        
        module.system = self # Rückreferenz

    # --- Data Bus ---
    def get_value(self, path, default=None):
        """Liest einen globalen Wert oder einen Modul-Parameter (ModulName.Attr)."""
        if path in self._values:
            return self._values[path]
        
        # Versuch Zugriff auf Modul: "Battery1.soc"
        if '.' in path:
            mod_name, attr = path.split('.', 1)
            if mod_name in self.modules:
                mod = self.modules[mod_name]
                if hasattr(mod, attr):
                    val = getattr(mod, attr)
                    if callable(val): return val()
                    return val
        
        return default

    def set_value(self, path, value):
        """Setzt einen globalen Wert."""
        self._values[path] = value

    def get_modules_by_type(self, type_name):
        return self.modules_by_type.get(type_name, [])

    # --- Physik Loop ---
    def step(self):
        # 1. DVCC Limits vorbereiten (werden von BMS gesetzt, hier nur Defaults/Reset falls nötig)
        # Wir lassen die Werte stehen, BMS aktualisiert sie im step().

        # 2. Logik-Module (BMS, Balancer) ausführen -> Setzen Limits
        for mod in self.get_modules_by_type('bms'):
            mod.step()
        for mod in self.get_modules_by_type('balancer'):
            mod.step() # Balancer ist hier Logik, manipuliert Batterie direkt
        for mod in self.get_modules_by_type('cccvcharger'):
            mod.step() # Ladealgorithmus

        # 3. Physik: Ströme einsammeln
        # Strategie: Dominante Batterie.
        # Wir nehmen an, die Busspannung ist initial die Batteriespannung (vom letzten Step oder OCV).
        # Da wir diskret sind, nehmen wir die Spannung aus dem letzten Step.
        
        batteries = self.get_modules_by_type('battery')
        sources = self.get_modules_by_type('vccs') # Hardware
        
        # Initialisierung der Spannung beim allerersten Schritt (falls 0)
        if self.voltage < 1.0 and batteries:
            self.voltage = sum(b.u_bus() for b in batteries) / len(batteries)

        current_from_sources = 0.0
        
        # 1. Quellen (Charger) berechnen ihren Strom basierend auf aktueller Spannung
        for source in sources:
            # Vereinfachte Aufteilung des CCL auf alle Quellen
            ccl_per_source = self.get_value('/Info/MaxChargeCurrent', 0) / max(1, len(sources))
            current_from_sources += source.step(self.voltage, ccl_per_source)
            
        # Lasten (Inverter) - noch nicht implementiert, würden hier abgezogen
        
        # 2. Netzwerkanalyse (Knotenregel) für Batterien
        if batteries:
            sum_g = 0.0 # Summe der Leitwerte (1/R)
            sum_u_g = 0.0 # Summe U_quelle * G
            
            # Thevenin-Parameter sammeln
            bat_params = []
            for bat in batteries:
                u_source, r_total = bat.get_thevenin_params()
                g = 1.0 / max(1e-6, r_total) # Schutz vor Division durch Null
                sum_g += g
                sum_u_g += u_source * g
                bat_params.append((bat, u_source, g))
            
            # Neue Busspannung berechnen: U_bus = (I_load + Sum(Uq*G)) / Sum(G)
            # I_load ist hier current_from_sources (positiv = in den Knoten hinein)
            self.voltage = (current_from_sources + sum_u_g) / sum_g
            
            # Ströme auf Batterien verteilen
            for bat, u_source, g in bat_params:
                # I_bat = (U_bus - U_quelle) * G  <-- Falsch! Stromrichtung!
                # Strom IN die Batterie (Laden) ist positiv.
                # U_bus = U_quelle + I * R  => I = (U_bus - U_quelle) / R ist falsch rum?
                # Wenn U_bus > U_quelle (z.B. Charger aktiv), fließt Strom IN die Batterie.
                # Also I = (U_bus - U_quelle) / R stimmt für Laderichtung positiv.
                
                i_bat = (self.voltage - u_source) * g
                bat.step(i_bat)
                
        else:
            # Ohne Batterie: Wenn Quellen aktiv sind, springt Spannung auf Max
            if current_from_sources > 0: self.voltage = 60.0 
            else: self.voltage = 0.0
            
        self.total_current = current_from_sources

    def get_metrics(self):
        return {
            'u': self.voltage,
            'i_sum': self.total_current,
            'dvcc_cvl': self.get_value('/Info/MaxChargeVoltage', 0),
            'dvcc_ccl': self.get_value('/Info/MaxChargeCurrent', 0)
        }


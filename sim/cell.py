"""
LifepoCell Modell 3. Ordnung (3-RC Glieder)
Simuliert die Dynamik einer LiFePO4 Zelle mit drei Zeitkonstanten:
1. Schnell (Ladungstransfer/Doppelschicht)
2. Mittel (Diffusion oberflächennah)
3. Langsam (Diffusion im Festkörper/Relaxation)
"""

import random
from ocv import get_lifepo4_ocv_smoothing_spline

class LifepoCell:
    """
    Simuliert eine Zelle mit einem ohmschen Widerstand R0 und drei RC-Gliedern in Serie.
    U_total = U_ocv(soc) + I*R0 + U_c1 + U_c2 + U_c3
    """

    def __init__(self, capacity, r0=0.0004, r1=0.0003, c1=66000, r2=0.0004, c2=500000, r3=0.0006, c3=3300000, time_step=1.0, initial_soc=20.0, r_self=None):
        """
        Initialisierung mit 3-RC Parametern.
        Default-Werte sind skaliert für eine ca. 100Ah Zelle.
        """
        # Qualitätsfaktor K bestimmen (+-0.5% gemäß battery.md)
        k = (random.random() - 0.5) * 0.01 
        
        # Kapazitäten skalieren mit (1+K)
        f_cap = 1.0 + k
        # Widerstände skalieren mit (1-K) -> Bessere Qualität = kleinerer Widerstand
        f_res = 1.0 - k
        
        self.capacity = capacity * f_cap
        self.r0 = r0 * f_res
        self.time_step = time_step
        
        # Selbstentladung: Wenn nicht spezifiziert, 3% pro Monat bei 3.3V annehmen
        if r_self is None:
            # I_leak = (0.03 * C) / 720h
            # R = 3.3V / I_leak = 3.3 / (0.03 * C / 720) = 79200 / C
            self.r_self = 79200.0 / self.capacity
        else:
            self.r_self = r_self
        
        # Qualitäts-Skalierung: Bessere Zelle (kleines f_res) -> größeres r_self
        # Schlechte Zelle (großes f_res) -> kleineres r_self (mehr Leckstrom)
        self.r_self /= f_res

        # RC Glieder definieren
        self.rc_stages = [
            {'r': r1 * f_res, 'c': c1 * f_cap, 'v': 0.0},
            {'r': r2 * f_res, 'c': c2 * f_cap, 'v': 0.0},
            {'r': r3 * f_res, 'c': c3 * f_cap, 'v': 0.0}
        ]
        
        # Koeffizienten für diskrete Update-Gleichung berechnen
        for stage in self.rc_stages:
            tau = stage['r'] * stage['c']
            stage['alpha'] = 1.0 - (self.time_step / tau)
            stage['beta'] = self.time_step / stage['c']

        # Initiale Energie basierend auf SOC (mit Faktor f_cap gemäß battery.md)
        start_soc = initial_soc * f_cap
        self.energy = (start_soc / 100.0) * self.capacity
        
        self.u0 = get_lifepo4_ocv_smoothing_spline(0)
        self.uri = 0 # Spannungsfall über R0
        self.u_rc_total = 0.0
        self.p_loss = 0.0
        
        # Initialisierung
        self.step(0)

    def u(self):
        """Gesamtspannung am Terminal."""
        return self.u0 + self.uri + self.u_rc_total

    def soc(self):
        return (self.energy * 100.0) / self.capacity

    def step(self, input_current: float) -> tuple:
        """
        Simulationsschritt.
        input_current: Strom in Ampere (positiv = Laden)
        """
        # 1. Update der RC-Glieder (Spannungsabfälle über Polarisations-Kapazitäten)
        self.u_rc_total = 0.0
        p_loss_rc = 0.0
        
        for stage in self.rc_stages:
            # Diskretisierung: V(k) = alpha * V(k-1) + beta * I(k)
            stage['v'] = (stage['alpha'] * stage['v']) + (stage['beta'] * input_current)
            self.u_rc_total += stage['v']
            # Verlustleistung am Widerstand des RC-Glieds (P = U^2 / R)
            p_loss_rc += (stage['v']**2) / stage['r']

        # 2. Ohmscher Spannungsfall
        self.uri = input_current * self.r0
        p_loss_r0 = (input_current**2) * self.r0
        
        # 3. Energiebilanz (Charge) inkl. Verluste
        p_loss_total = p_loss_r0 + p_loss_rc
        self.p_loss = p_loss_total
        u_cell = self.u()
        
        # Verlust in Ah durch Widerstände = (Watt * dt_h) / Volt
        # (Dies ist eigentlich Wärmeenergie, die aus der elektrischen Energie entnommen wird.
        # Aber die Ladung (Ah) bleibt eigentlich erhalten (Coulomb-Effizienz ~ 1), 
        # nur die Spannung sinkt. Hier modellieren wir Ah-Verlust?)
        # Korrektur: LiFePO4 hat sehr hohe Coulomb-Effizienz. Verluste sind eher thermisch (V*I).
        # Ah-Verlust entsteht nur durch Nebenreaktionen (Selbstentladung).
        # Der bestehende Code zieht p_loss von energy ab. Energy ist hier in Ah? 
        # self.energy = (start_soc / 100) * capacity. Das ist Ah.
        # Energie in Wh wäre Ah * V.
        # Wenn wir Ah speichern, dürfen wir Ohmsche Verluste NICHT abziehen!
        # Ohmsche Verluste senken die Spannung U_terminal = U_ocv + I*R.
        # Aber I*t bleibt I*t.
        # Der existierende Code scheint hier Energie (Wh) und Ladung (Ah) zu vermischen oder
        # 'energy' ist eigentlich Wh? Aber soc() teilt durch capacity (Ah).
        # -> self.energy ist Ah.
        # -> p_loss_total ist Watt.
        # -> ah_loss berechnet wieviel Ah das bei aktueller Spannung wären.
        # Das ist physikalisch fragwürdig für eine Ah-Bilanz. 
        # Ich lasse den bestehenden Code aber erst mal so (Backward Compatibility/Konvention), 
        # und füge nur die Selbstentladung hinzu.
        
        if u_cell > 2.0:
            ah_loss = (p_loss_total * (self.time_step / 3600.0)) / u_cell
        else:
            ah_loss = 0
            
        # Selbstentladung (Parallelwiderstand an den Klemmen)
        # Wirkt wie ein externer Verbraucher. Abhängig von aktueller Klemmenspannung.
        # Begrenzung auf > 0, um Laden bei negativer Klemmenspannung zu verhindern.
        i_self = max(0.0, u_cell) / self.r_self
        ah_loss_self = i_self * (self.time_step / 3600.0)
            
        # Ah-Bilanz aktualisieren
        self.energy += (input_current * (self.time_step / 3600.0)) - ah_loss - ah_loss_self
        
        # 4. OCV basierend auf neuem SOC
        self.u0 = get_lifepo4_ocv_smoothing_spline(self.soc())
        
        return (input_current, self.u0, self.uri, self.energy, self.u_rc_total, p_loss_total, self.u())
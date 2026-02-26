"""

C1: "Polarisationskapazität", "elektrochemische Kapazität" der zelle

Tabelle 4: Skalierte R1- und C1-Werte (100Ah)
| SOC  | R1 (mΩ) | C1 (kF) |
| 100% | 0,40    | 117,5 |
| 90%  | 0,27    | 141,1 |
| 80%  | 0,31    | 124,3 |
| 70%  | 0,31    | 109,8 |
| 60%  | 0,30    | 106,8 |
| 50%  | 0,36    | 91,5 |
| 40%  | 0,37    | 84,7 |
| 30%  | 0,39    | 78,6 |
| 20%  | 0,42    | 70,9 |

Mittelwert: R1: 0,35 mΩ, C1: 102,8 kF 
"""

import time

from ocv import get_lifepo4_ocv_smoothing_spline


C = 100 # [Ah]
r_r0 = 0.00025 # [ohm]
r_rc = 0.0005 # [ohm]
cap_rc = 103 * 1000 # [F]

C2 = C/2 
CEnd = C * 0.05

class LifepoCell:
    """
    Simuliert ein diskretes, parallel geschaltetes RC-Glied.

    Die Klasse berechnet die Spannung über dem RC-Glied basierend auf einem
    periodisch übergebenen Eingangsstrom.
    """

    def __init__(self, r0, r1: float, capacitance: float, time_step: float):
        """
        Konstruktor zur Initialisierung des RC-Filters.

        Args:
            r1 (float): Der Widerstandswert in Ohm (R).
            capacitance (float): Die Kapazität in Farad (C).
            time_step (float): Das diskrete Zeitintervall in Sekunden (dt),
                               in dem die 'step'-Methode aufgerufen wird.
        """
        if not (r0 > 0 and r1 > 0 and capacitance > 0 and time_step > 0):
            raise ValueError("Widerstand, Kapazität und Zeitintervall müssen positiv sein.")

        self.r0 = r0
        self.r1 = r1
        self.capacitance = capacitance
        self.time_step = time_step
        
        # Die Zeitkonstante Tau
        self.tau = self.r1 * self.capacitance
        
        # Vorberechnete Koeffizienten für die Update-Gleichung,
        # um die Berechnung in der 'step'-Methode zu beschleunigen.
        self._alpha = 1 - (self.time_step / self.tau)
        self._beta = self.time_step / self.capacitance
        
        # Die Spannung wird zu Beginn auf 0 Volt initialisiert.
        self.prevC1voltage = 0.0

        self.cap = C
        self.energy = 0
        self.u0 = get_lifepo4_ocv_smoothing_spline(0)
        self.uri = 0
        self.c1voltage = 0

    def u(self):
        return self.u0+self.uri+self.c1voltage

    def soc(self):
        return self.energy*100 / C

    def full(self):
        return self.soc() >= 100

    def cend(self):
        return CEnd

    def step(self, input_current: float) -> float:

        self.energy += input_current * (self.time_step/3600)
        self.u0 = get_lifepo4_ocv_smoothing_spline(self.energy*100/C)
        self.uri = input_current * self.r0

        # Anwenden der diskreten Update-Gleichung
        self.c1voltage = self._alpha * self.prevC1voltage + self._beta * input_current
        
        r1power = self.c1voltage * (self.c1voltage/self.r1)
        c1energy = self.c1energy(self.c1voltage)
        # print(f"c1energy: {c1energy}")

        # Den aktuellen Zustand für den nächsten Aufruf speichern
        self.prevC1voltage = self.c1voltage
       
        return (input_current, self.u0, self.uri, self.energy, self.c1voltage, r1power, c1energy, self.u())

    def c1energy(self, voltage):
    
        if voltage == 0:
            return 0.0

        # 1. Calculate energy in Joules (Watt-seconds)
        # Formula: E = 0.5 * C * V^2
        energy_joules = 0.5 * self.capacitance * voltage**2

        # 2. Convert Joules (Watt-seconds) to Watt-hours
        # 1 Wh = 3600 Ws
        energy_watt_hours = energy_joules / 3600

        # 3. Convert Watt-hours to Ampere-hours
        # Ah = Wh / V
        energy_ampere_hours = energy_watt_hours / voltage

        return energy_ampere_hours


"""
lifepoCell = LifepoCell(r1=r_rc, capacitance=cap_rc, time_step=1)

sample_data = [(0, lifepoCell.u0, 0, 0, 0, 0, lifepoCell.u0)]

for t in range(2*3600+100):

    # ladeprofil
    # lastprofil

    current=C2
    if t>2*3600:
        current=0
    elif t>5000:
        current=-C2/4
    # elif t>50:
    elif t>3600:
        current=C2/4
    # elif t>50:
        # current=0

    tup = lifepoCell.step(input_current=current) # Bsp: 10 mA Strom
    sample_data.append(tup)

    # print(f"Spannung nach {t} s: {tup} V")

visualize_measurements(sample_data)
"""






import numpy as np

# 1. Python-Dictionary mit den SOC-Spannungs-Daten
# Die Daten sind als Liste von Tupeln (SOC, Spannung) gespeichert,
# um die Reihenfolge für die Interpolation sicherzustellen.
soc_ocv_data = [
    (100, 3.425), # Mittelwert von 3.40-3.45V
    (99, 3.35),
    (90, 3.32),
    (80, 3.32),
    (70, 3.30),
    (60, 3.27),
    (50, 3.26),
    (40, 3.25),
    (30, 3.22),
    (20, 3.20),
    (14, 3.18),
    (10, 3.00),
    (9, 2.90),
    (0, 2.50)
]

# Die Daten müssen nach SOC sortiert sein, was hier bereits der Fall ist.
# Für die Interpolation trennen wir die SOC- und Spannungs-Werte.
soc_points = [item[0] for item in reversed(soc_ocv_data)]
ocv_points = [item[1] for item in reversed(soc_ocv_data)]


def get_ocv(soc):
  """
  Berechnet die Leerlaufspannung (OCV) einer LiFePO4-Zelle für einen
  gegebenen Ladezustand (SOC) mittels linearer Interpolation.

  Args:
    soc (float): Der Ladezustand in Prozent (von 0 bis 100).

  Returns:
    float: Die interpolierte Leerlaufspannung in Volt.
  """
  # numpy.interp ist ideal für diese Aufgabe. Es erwartet, dass die
  # x-Punkte (hier soc_points) monoton ansteigend sind.
  return np.interp(soc, soc_points, ocv_points)

import numpy as np
from scipy.optimize import curve_fit, brentq
import matplotlib.pyplot as plt

# --- Setup des Basismodells (Doppel-Sigmoid), unverändert ---

SOC_POINTS = np.array([0, 9, 10, 14, 20, 30, 40, 50, 60, 70, 80, 90, 99, 100])
OCV_POINTS = np.array([2.50, 2.90, 3.00, 3.18, 3.20, 3.22, 3.25, 3.26, 3.27, 3.30, 3.32, 3.32, 3.35, 3.425])

def double_sigmoid_model(soc, a1, c1, d1, a2, c2, d2, b):
    sigmoid1 = a1 / (1 + np.exp(-c1 * (soc - d1)))
    sigmoid2 = a2 / (1 + np.exp(-c2 * (soc - d2)))
    return sigmoid1 + sigmoid2 + b

initial_guesses = [0.7, 0.2, 15, 0.1, 1.5, 99, 2.5]
parameter_bounds = ([0.5, 0.05, 5, 0.01, 0.5, 95, 2.4], [1.0, 1.0, 30, 0.5, 3.0, 105, 2.6])
optimal_params, _ = curve_fit(double_sigmoid_model, SOC_POINTS, OCV_POINTS, p0=initial_guesses, bounds=parameter_bounds, maxfev=5000)

def get_lifepo4_ocv_precise(soc: float) -> float:
    soc = np.clip(soc, 0, 100)
    return double_sigmoid_model(soc, *optimal_params)

# --- NEU: Das hybride Modell mit garantiert nahtlosen Übergängen ---

# 1. Definiere den festen Startpunkt des linearen Bereichs
SOC_LINEAR_START = 20.0

# 2. Berechne die Spannung am Startpunkt für einen nahtlosen Übergang
VOLTAGE_START = get_lifepo4_ocv_precise(SOC_LINEAR_START)

# 3. Definiere die ZIEL-Spannung am Ende der Geraden
VOLTAGE_END_TARGET = VOLTAGE_START + 0.025

# 4. FINDE den SOC-Wert, bei dem die obere Kurve exakt die Zielspannung erreicht.
#    Wir verwenden einen numerischen Löser (brentq), um die Gleichung
#    `get_lifepo4_ocv_precise(soc) - VOLTAGE_END_TARGET = 0` zu lösen.
try:
    SOC_LINEAR_END = brentq(
        lambda soc: get_lifepo4_ocv_precise(soc) - VOLTAGE_END_TARGET,
        SOC_LINEAR_START,
        100
    )
except ValueError:
    # Fallback, falls die Spannung nie erreicht wird (unwahrscheinlich)
    SOC_LINEAR_END = 95.0

# 5. Berechne die finale Steigung und den y-Achsenabschnitt
slope = (VOLTAGE_END_TARGET - VOLTAGE_START) / (SOC_LINEAR_END - SOC_LINEAR_START)
intercept = VOLTAGE_START - slope * SOC_LINEAR_START

def linear_part(soc):
    return slope * soc + intercept

# 6. Die finale, nahtlose Hybrid-Methode
def get_lifepo4_ocv_seamless(soc: float) -> float:
    """
    Berechnet die OCV mit einem hybriden Modell, das nahtlose Übergänge
    und einen definierten Spannungsanstieg von 25mV im Mittelteil garantiert.
    """
    soc = np.clip(soc, 0, 100)

    if soc < SOC_LINEAR_START:
        return get_lifepo4_ocv_precise(soc)
    elif soc <= SOC_LINEAR_END:
        return linear_part(soc)
    else: # soc > SOC_LINEAR_END
        return get_lifepo4_ocv_precise(soc)

import numpy as np
from scipy.interpolate import splrep, splev
import matplotlib.pyplot as plt

# 1. Datenpunkte aus Tabelle 2
SOC_POINTS = np.array([0, 1, 3.0, 20, 30, 40, 50, 60, 70, 80, 88, 96, 99.9, 100])
OCV_POINTS_TABLE2 = np.array([2.80, 2.90, 3.0, 3.27, 3.29, 3.30, 3.31, 3.32, 3.33, 3.34, 3.342, 3.352, 3.45, 3.46])

# 2. Erstelle die B-Spline-Repräsentation mit Grad k=2 (quadratisch)
#    - k=1 wäre linear (spitze Ecken)
#    - k=2 ist quadratisch (glatter, aber folgt den Punkten enger)
#    - k=3 ist kubisch (sehr glatt, kann aber leichter überschwingen)
tck_quadratic = splrep(SOC_POINTS, OCV_POINTS_TABLE2, k=2)

# 3. Die finale Methode, die den quadratischen Spline nutzt
def get_lifepo4_ocv_spline_quad(soc: float) -> float:
    """
    Berechnet die Ruhespannung (OCV) mit einer quadratischen
    B-Spline-Approximation (k=2) basierend auf den Daten aus Tabelle 2.

    Args:
      soc (float): Der Ladezustand in Prozent (von 0.0 bis 100.0).

    Returns:
      float: Die interpolierte Ruhespannung (Uoc) in Volt.
    """
    soc = np.clip(soc, 0, 100)
    return splev(soc, tck_quadratic).item()

# --- Anwendung und Visualisierung ---
if __name__ == "__main__":
    print("--- Quadratisches B-Spline-Modell (k=2) basierend auf Tabelle 2 ---")

    # Erzeuge Daten für den Plot
    soc_smooth = np.linspace(0, 100, 400)
    ocv_spline_curve_quadratic = splev(soc_smooth, tck_quadratic)

    # Plot erstellen
    plt.figure(figsize=(10, 6))
    plt.scatter(SOC_POINTS, OCV_POINTS_TABLE2, color='red', label='Stützpunkte (Tabelle 2)', zorder=5)
    plt.plot(soc_smooth, ocv_spline_curve_quadratic, color='blue', linewidth=2.5, label='Quadratische B-Spline Kurve (k=2)')

    plt.title('Quadratische LiFePO4 Kennlinie (OCV vs. SOC)', fontsize=14)
    plt.xlabel('Ladezustand (SOC) [%]', fontsize=12)
    plt.ylabel('Ruhespannung (OCV) [V]', fontsize=12)
    plt.grid(True)
    plt.legend()
    plt.show()


from scipy.interpolate import UnivariateSpline

# 1. Datenpunkte aus Tabelle 2 (unverändert)
SOC_POINTS = np.array([0, 8, 20, 30, 40, 50, 60, 70, 80, 90, 99, 99.8, 100])
OCV_POINTS_TABLE2 = np.array([2.80, 3.10, 3.23, 3.25, 3.26, 3.27, 3.28, 3.29, 3.30, 3.31, 3.34, 3.39, 3.45])

# 2. Erstelle den Smoothing Spline
#    - k=3: Kubischer Spline für eine glatte Kurve.
#    - s=0.0001: Ein kleiner Smoothing-Faktor. Erlaubt der Kurve,
#                leicht von den Punkten abzuweichen, um glatter zu sein.
smoothing_spline = UnivariateSpline(SOC_POINTS, OCV_POINTS_TABLE2, k=3, s=0.0001)

# 3. Die finale Methode, die den Smoothing Spline nutzt
def get_lifepo4_ocv_smoothing_spline(soc: float) -> float:
    """
    Berechnet die Ruhespannung (OCV) mit einem glättenden (smoothing)
    B-Spline, der nicht exakt durch alle Punkte verläuft.

    Args:
      soc (float): Der Ladezustand in Prozent (von 0.0 bis 100.0).

    Returns:
      float: Die angenäherte Ruhespannung (Uoc) in Volt.
    """
    soc = np.clip(soc, 0, 100)
    # Die erstellte Spline-Instanz kann direkt wie eine Funktion aufgerufen werden.
    return smoothing_spline(soc).item()


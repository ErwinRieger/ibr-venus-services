import matplotlib.pyplot as plt
import numpy as np

def visualize_measurements(data: list[tuple[float, float, float, float, float]]):
    """
    Visualisiert Messwerte aus einer Simulation oder Messreihe.

    Args:
        data (list[tuple]): Eine Liste von Tupeln, wobei jedes Tupel die
                            Werte (Strom, Spannung, Gesamtenergie, Leistung R1, Energie C1)
                            für einen Messpunkt enthält.
    """
    if not data:
        print("Die Datenliste ist leer. Es gibt nichts zu plotten.")
        return

    # Daten entpacken in fünf separate Listen
    currents, voltages, uri, total_energies, rcvolt, r1_powers, c1_energies, v = zip(*data)

    # Index für die x-Achse erstellen (z.B. Messpunkt-Nummer)
    x_axis = []
    ur0urc = []
    for i in range(len(currents)):
        x_axis.append(i/60.0)
        ur0urc.append(uri[i]+rcvolt[i])

    fig, axs = plt.subplots(len(data[0]), 1, figsize=(10, 15), sharex=True)
    fig.suptitle('Visualisierung der Messwerte', fontsize=16)

    # --- Einzelne Graphen zeichnen ---

    y = 0

    # Strom
    axs[y].plot(x_axis, currents, color='dodgerblue', linestyle='-')
    axs[y].set_ylabel('Strom [A]')
    axs[y].grid(True)
    y += 1

    # Gesamtenergie
    axs[y].plot(x_axis, total_energies, color='darkorange', linestyle='-')
    axs[y].set_ylabel('Ladung/SOC [Ah]')
    axs[y].grid(True)
    y += 1

    # Spannung
    axs[y].plot(x_axis, voltages, color='crimson', linestyle='-')
    axs[y].set_ylabel('Zell U0 [V]')
    axs[y].grid(True)
    y += 1

    # Spannung innenwiderstand
    axs[y].plot(x_axis, uri, color='crimson', linestyle='-')
    axs[y].plot(x_axis, rcvolt, color='crimson', linestyle='-')
    axs[y].plot(x_axis, ur0urc, color='crimson', linestyle='-')
    axs[y].set_ylabel('U R0 [V]')
    axs[y].grid(True)
    y += 1

    # U am RC glied
    axs[y].plot(x_axis, rcvolt, color='crimson', linestyle='-')
    axs[y].set_ylabel('Spannung R1C1 [V]')
    axs[y].grid(True)
    y += 1

    # Leistung von Widerstand R1
    axs[y].plot(x_axis, r1_powers, color='forestgreen', linestyle='-')
    axs[y].set_ylabel('Leistung R1 [W]')
    axs[y].grid(True)
    y += 1

    # Energie von Kondensator C1
    axs[y].plot(x_axis, c1_energies, color='darkviolet', linestyle='-')
    axs[y].set_ylabel('Energie C1 [Ah]')
    axs[y].grid(True)
    y += 1

    # Spannung
    axs[y].plot(x_axis, v, color='crimson', linestyle='-')
    axs[y].set_xlabel('t (min)')
    axs[y].set_ylabel('Spannung [V]')
    axs[y].grid(True)
    y += 1

    # Layout anpassen und Plot anzeigen
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    plt.show()

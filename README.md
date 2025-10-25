====================
ibr-venus-services
====================

Eine Sammlung von Diensten für das Victron Venus OS zur Überwachung und Steuerung von Victron-Solaranlagen.

.. note::

   Dieses Projekt befindet sich in aktiver Entwicklung, wird aber bereits auf mehreren Victron ESS-Systemen produktiv eingesetzt.

Voraussetzungen
===============

* Getestet mit Venus OS v3.55 und v3.60. Andere Versionen sind möglicherweise ebenfalls kompatibel.

Installation
============

1. Klonen des Repositorys
--------------------------

Zuerst müssen die Quelldateien auf das Venus OS-Gerät in das Verzeichnis ``/data`` kopiert werden. Dies kann entweder durch Klonen des Git-Repositorys oder durch das Herunterladen und Entpacken einer ZIP-Datei geschehen.

Für das Klonen via Git (SSH-Zugang zum Gerät erforderlich):

.. code-block:: bash

   git clone https://github.com/ErwinRieger/ibr-venus-services.git /data/ibr-venus-services

2. Manuelle Installation der Dienste
------------------------------------

Jeder Dienst kann einzeln installiert werden. Führen Sie dazu das ``setup.sh``-Skript im Verzeichnis des jeweiligen Dienstes aus.

Beispiel für die Installation des ``dbus-ibr-system``-Dienstes:

.. code-block:: bash

   sh /data/ibr-venus-services/dbus-ibr-system/setup.sh install

3. Automatisierte Installation (Optional)
-----------------------------------------

Um eine definierte Liste von Diensten automatisch – zum Beispiel bei jedem Systemstart – zu installieren, kann der ``installall``-Befehl genutzt werden.

**a) Konfigurationsdatei erstellen**

Legen Sie eine Datei unter ``/data/conf/installed-ibr-services`` an, die die Namen der zu installierenden Dienste (getrennt durch Leerzeichen) enthält.

.. code-block:: bash

   echo "dbus-ibr-system dbus-ibr-serialbat dbus-ibr-bms" > /data/conf/installed-ibr-services

**b) In Start-Skript eintragen**

Fügen Sie den folgenden Befehl zur Datei ``/data/rcS.local`` hinzu, um die in der Konfigurationsdatei genannten Dienste bei jedem Start automatisch zu installieren:

.. code-block:: bash

   sh /data/ibr-venus-services/common/setup.sh installall > /tmp/installall.log 2>&1

Architektur und Abhängigkeiten
================================

Die Dienste in diesem Projekt interagieren teilweise miteinander:

*   **`dbus-ibr-system`**: Stellt den zentralen Dienst `com.victronenergy.ibrsystem` bereit.

*   **`dbus-ibr-serialbat`**: Stellt einen `com.victronenergy.battery` Dienst bereit und ist die Datenquelle für `dbus-ibr-bms`.

*   **`dbus-ibr-bms`**: Hängt von den Daten von `dbus-ibr-serialbat` ab und stellt den aggregierten Dienst `com.victronenergy.battery.ibrbms` bereit.

*   **`dbus-ibr-loads`**: Hängt von `dbus-ibr-system` ab, um die Drosselung der PV-Leistung zu erkennen.

*   **`dbus-ibr-neeycontrol`**: Hängt vom Balancing-Status ab, der vom `dbus-ibr-bms`-Dienst veröffentlicht wird.

*   **Unabhängige Dienste**: `dbus-ibr-mpcontrol`, `dbus-ibr-rshack` und `dbus-ibr-shelly-rsmulti` haben keine direkten Abhängigkeiten zu anderen `dbus-ibr-*` Diensten.

Zusammenfassende Kette der Abhängigkeiten:

``dbus-ibr-serialbat`` -> ``dbus-ibr-bms`` -> ``dbus-ibr-neeycontrol``

``dbus-ibr-system`` -> ``dbus-ibr-loads``

Veröffentlichte Dienste
=======================

* **dbus-ibr-system**: Sammelt und berechnet systemweite Werte und stellt sie unter Pfaden wie ``/TotalPVYield``, ``/BattLoad`` und ``/MppOperationMode`` bereit.
* **dbus-ibr-serialbat**: Ein angepasster serieller Batterietreiber für Daly- oder Felicity-BMS.
* **dbus-ibr-bms**: Fasst die Werte von mehreren Batterien zu einer virtuellen Batterie zusammen und implementiert einen LiFePO4-Ladealgorithmus.
* **dbus-ibr-mpcontrol**: Schaltet einen MultiPlus-Wechselrichter (im Assisting-Modus) bei hoher Last zu.
* **dbus-ibr-neeycontrol**: Steuert Neey-Active-Balancer, um ein "Balance-when-charged"-Verfahren zu implementieren.
* **dbus-ibr-shelly-rsmulti**: Implementiert eine "Nulleinspeisung" (Zero-Export) für ein ESS mit einem RS-Multi und einem Shelly 3EM Pro Smartmeter.
* **dbus-ibr-loads**: Steuert einen Verbraucher (z.B. Wasserkocher) via MQTT, um überschüssige PV-Energie zu nutzen.
* **dbus-ibr-rshack**: Ein Workaround zur Korrektur von Anzeige- und Verbrauchswerten in speziellen System-Setups.
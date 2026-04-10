==============
Venus OS Utils
==============

Diagnostic and monitoring tools for Venus OS.

memwatch.py
===========

Monitors memory consumption and growth trends of Victron services and core system processes.

Features
--------
* **Targeting:** Automatically filters for services in ``/opt/victronenergy`` and system programs like ``dbus-daemon``, ``flashmq``, and ``localsettings``.
* **Baseline Management:** Establishes a memory baseline at script start. For new processes, it waits 10 seconds to allow the memory footprint to stabilize before setting a baseline.
* **Sliding Window Rate:** Calculates the current growth rate (Bytes/s) based on a 10-second sliding window.
* **Sorting:** Displays the Top 5 processes, sorted primarily by absolute memory usage (RSS) and secondarily by total growth since baseline.
* **Real-time Stats:** Shows Start Memory, Current Memory, Total Growth, Growth Rate, and current CPU load.

Requirements
------------
* The ``python3-psutil`` package must be installed on Venus OS:

.. code-block:: bash

    opkg update && opkg install python3-psutil

Usage
-----
.. code-block:: bash

    python3 memwatch.py

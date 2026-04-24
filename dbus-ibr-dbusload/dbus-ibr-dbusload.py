#!/usr/bin/env python3
import os
import sys
import time
import dbus
import dbus.mainloop.glib
import logging
from gi.repository import GLib
import math

# Add velib_python to path
sys.path.insert(1, os.path.join(os.path.dirname(__file__), '../common/velib_python'))

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

UPDATE_INTERVAL = 10.0  # seconds
BURST_THRESHOLD = 50.0  # msgs/sec to flag as burst

class DbusLoadService:
    def __init__(self):
        self.start_time = time.time()
        self.counts = {}  # unique_name -> count in current interval
        self.names = {}   # unique_name -> well_known_name
        self.stats = {}   # well_known_name -> {avg10, avg60, avg300, last_count}
        
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SystemBus()
        
        # Monitor all messages on the system bus
        self.bus.add_match_string("")
        self.bus.add_message_filter(self._message_filter)
        
        # Track name ownership
        self.bus.add_signal_receiver(self._name_owner_changed, 
                                   signal_name="NameOwnerChanged",
                                   dbus_interface="org.freedesktop.DBus")
        
        # Initial name mapping
        self._refresh_names()

    def _message_filter(self, bus, message):
        sender = message.get_sender()
        dest = message.get_destination()
        
        if sender:
            self.counts[sender] = self.counts.get(sender, 0) + 1
        if dest and dest != 'org.freedesktop.DBus' and not dest.startswith(':'):
            # If destination is a well-known name, we track it via its unique name
            # but mapping destination unique names is harder in real-time without constant lookup.
            # We focus primarily on the sender as the source of "load".
            pass
        return None

    def _name_owner_changed(self, name, old_owner, new_owner):
        if name.startswith(':'): return
        if new_owner:
            self.names[new_owner] = name
        if old_owner and old_owner in self.names and self.names[old_owner] == name:
            if not new_owner:
                del self.names[old_owner]

    def _refresh_names(self):
        dbus_obj = self.bus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus')
        dbus_iface = dbus.Interface(dbus_obj, 'org.freedesktop.DBus')
        for name in dbus_iface.ListNames():
            if name.startswith(':'): continue
            try:
                owner = dbus_iface.GetNameOwner(name)
                self.names[owner] = name
            except: pass

    def update_stats(self):
        now = time.time()
        interval = UPDATE_INTERVAL
        
        # EMA coefficients
        alpha10  = 1.0 - math.exp(-interval / 10.0)
        alpha60  = 1.0 - math.exp(-interval / 60.0)
        alpha300 = 1.0 - math.exp(-interval / 300.0)

        current_counts = self.counts
        self.counts = {} # Reset for next interval

        # Map unique names to well-known names and aggregate
        aggregated = {}
        for unique, count in current_counts.items():
            name = self.names.get(unique, unique)
            # Group common victron services if they have multiple connections? 
            # Usually 1:1.
            aggregated[name] = aggregated.get(name, 0) + count

        for name, count in aggregated.items():
            rate = count / interval
            if name not in self.stats:
                self.stats[name] = {'avg10': rate, 'avg60': rate, 'avg300': rate}
            else:
                s = self.stats[name]
                s['avg10']  = s['avg10']  * (1 - alpha10)  + rate * alpha10
                s['avg60']  = s['avg60']  * (1 - alpha60)  + rate * alpha60
                s['avg300'] = s['avg300'] * (1 - alpha300) + rate * alpha300
            
            self.stats[name]['last_rate'] = rate

        # Decay stats for services not heard from
        for name in list(self.stats.keys()):
            if name not in aggregated:
                s = self.stats[name]
                s['avg10']  *= (1 - alpha10)
                s['avg60']  *= (1 - alpha60)
                s['avg300'] *= (1 - alpha300)
                s['last_rate'] = 0
                if s['avg10'] < 0.01 and s['avg60'] < 0.01:
                    del self.stats[name]

    def log_table(self):
        items = []
        for name, s in self.stats.items():
            burst = "BURST!" if s['last_rate'] > BURST_THRESHOLD else ""
            items.append((name, s['avg10'], s['avg60'], s['avg300'], burst))
        
        # Sort by 10s avg
        items.sort(key=lambda x: x[1], reverse=True)
        
        logging.info("--- D-Bus Load Report (msgs/sec) ---")
        logging.info(f"{'SERVICE':<40} {'10s':>8} {'1m':>8} {'5m':>8}  {'STATUS'}")
        for name, a10, a60, a300, burst in items[:20]:
            logging.info(f"{name[:40]:<40} {a10:>8.2f} {a60:>8.2f} {a300:>8.2f}  {burst}")
        logging.info("------------------------------------")

def main():
    service = DbusLoadService()
    
    def on_timer():
        try:
            service.update_stats()
            service.log_table()
        except Exception as e:
            logging.error(f"Error in timer: {e}")
        return True

    GLib.timeout_add(int(UPDATE_INTERVAL * 1000), on_timer)
    
    logging.info("dbus-ibr-dbusload started")
    loop = GLib.MainLoop()
    try:
        loop.run()
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()

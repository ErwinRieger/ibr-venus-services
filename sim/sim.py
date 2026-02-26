#!/usr/bin/env python3

import argparse
import configparser
import time
import importlib
import matplotlib.pyplot as plt
from dc_bus import DCBus

class SimulationRunner:
    def __init__(self, config_file):
        self.config = configparser.ConfigParser()
        self.config.read(config_file)
        
        # Global Settings
        g = self.config['Global']
        self.time_step = float(g.get('time_step', 1.0))
        self.title = g.get('name', 'Simulation')
        self.delay = float(g.get('delay', 0.1))
        
        # Dauer bestimmen: n_steps oder t_simulation
        if 'n_steps' in g:
            self.n_steps = int(g['n_steps'])
        elif 't_simulation' in g:
            t_sim = float(g['t_simulation'])
            self.n_steps = int(t_sim / self.time_step)
        else:
            self.n_steps = 3600 # Default fallback
            
        print(f"Setup: {self.n_steps} Schritte à {self.time_step}s (Total: {self.n_steps*self.time_step/3600:.2f}h)")
        
        self.bus = DCBus(self.time_step)
        self.history = {'t': [], 'u': [], 'i': [], 'soc': []}
        
        self._init_modules()
        self._init_plot()

    def _init_modules(self):
        for section in self.config.sections():
            if section == 'Global': continue
            m_config = self.config[section]
            m_type = m_config.get('type')
            
            try:
                if m_type == 'battery':
                    from battery import Battery
                    obj = Battery(section, m_config, self.time_step)
                    self.bus.register_battery(obj)
                elif m_type == 'eve_charger':
                    from eve_charger import Charger
                    obj = Charger(section, m_config, self.time_step)
                    self.bus.register_charger(obj)
                print(f"Loaded {section} ({m_type})")
            except Exception as e:
                print(f"Error loading {section}: {e}")

    def _init_plot(self):
        plt.ion()
        self.fig, (self.ax_u, self.ax_i, self.ax_soc) = plt.subplots(3, 1, sharex=True, figsize=(8, 10))
        self.fig.suptitle(self.title)
        
        self.line_u, = self.ax_u.plot([], [], 'b-', label='Bus Spannung [V]')
        self.line_i, = self.ax_i.plot([], [], 'r-', label='Gesamtstrom [A]')
        self.line_soc, = self.ax_soc.plot([], [], 'g-', label='SOC [%]')
        
        self.ax_u.set_ylabel('Voltage [V]')
        self.ax_u.grid(True)
        self.ax_u.legend(loc='upper left')
        
        self.ax_i.set_ylabel('Current [A]')
        self.ax_i.grid(True)
        self.ax_i.legend(loc='upper left')
        
        self.ax_soc.set_ylabel('SOC [%]')
        self.ax_soc.set_xlabel('Time [h]')
        self.ax_soc.grid(True)
        self.ax_soc.legend(loc='upper left')

    def run(self):
        print("Starting Simulation Loop...")
        try:
            for step in range(self.n_steps):
                start_time = time.time()
                
                # Physik Schritt
                u, i = self.bus.step()
                
                # SOC erfassen (von erster Batterie als Referenz)
                soc = 0
                if self.bus.batteries:
                    soc = self.bus.batteries[0].soc()
                
                # History
                # Zeit in Stunden für Plot
                t_hours = (step * self.time_step) / 3600.0
                self.history['t'].append(t_hours)
                self.history['u'].append(u)
                self.history['i'].append(i)
                self.history['soc'].append(soc)
                
                # GUI Update alle 5 Schritte oder wenn delay groß genug
                if step % 5 == 0:
                    self._update_plot()
                    
                    # Delay Logik
                    compute_time = time.time() - start_time
                    wait = max(0, self.delay - compute_time)
                    if wait > 0:
                        plt.pause(wait)
                    else:
                        plt.pause(0.001) # Minimum für GUI refresh
                        
        except KeyboardInterrupt:
            print("\nAborted by user.")
        
        print("Simulation finished.")
        plt.ioff()
        plt.show()

    def _update_plot(self):
        t = self.history['t']
        
        self.line_u.set_data(t, self.history['u'])
        self.ax_u.relim(); self.ax_u.autoscale_view()
        
        self.line_i.set_data(t, self.history['i'])
        self.ax_i.relim(); self.ax_i.autoscale_view()
        
        self.line_soc.set_data(t, self.history['soc'])
        self.ax_soc.relim(); self.ax_soc.autoscale_view()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='basic_charge.ini')
    args = parser.parse_args()
    
    runner = SimulationRunner(args.config)
    runner.run()
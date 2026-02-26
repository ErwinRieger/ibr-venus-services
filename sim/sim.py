import argparse
import configparser
import time, sys, os
import traceback
from system import System
from sim_gui import SimulationGui

sys.path.insert(1, os.path.join(os.path.dirname(__file__), '..', 'common', 'python'))

class SimulationRunner:
    def __init__(self, config_file):
        self.config = configparser.ConfigParser()
        self.config.read(config_file)
        
        g = self.config['Global']
        self.time_step = float(g.get('time_step', 1.0))
        self.delay = float(g.get('delay', 0.1))
        self.title = g.get('name', 'Simulation')
        
        if 'n_steps' in g: self.n_steps = int(g['n_steps'])
        else: self.n_steps = int(float(g.get('t_simulation', 3600)) / self.time_step)
        
        self.system = System(self.time_step)
        self.modules = []
        self._init_modules()
        
        # GUI initialisieren mit Parametern
        sim_params = {
            'n_steps': self.n_steps,
            'time_step': self.time_step,
            't_simulation': self.n_steps * self.time_step
        }
        self.gui = SimulationGui(self.title, self.modules, sim_params)
        
        # Log-Anbindung
        self.system.set_log_callback(self.gui.log)
        self.system.log(f"Simulation initialisiert: {self.title}")

    def _init_modules(self):
        # System als Basis-Modul vorab hinzufügen
        self.system.name = 'System'
        self.system.plot_config = []
        self.system.y2plot_config = []
        self.modules = [self.system]

        # Map für Modul-Namen zu Objekten (für Referenzen in der Config)
        mod_map = {'System': self.system}
        
        for section in self.config.sections():
            if section == 'Global': continue
            cfg = self.config[section]
            m_type = cfg.get('type')
            
            if not m_type: continue
            
            # Dynamischer Import für alle Module
            module_name = f"mod_{m_type}"
            class_name = m_type
            
            obj = None
            try:
                # Import: from mod_xyz import xyz
                mod = __import__(module_name, fromlist=[class_name])
                cls = getattr(mod, class_name)
                obj = cls(section, cfg, self.time_step)
            except ImportError as e:
                print(f"Fehler: Konnte Modul '{module_name}' für Typ '{m_type}' nicht importieren: {e}")
                traceback.print_exc()
            except AttributeError as e:
                print(f"Fehler: Klasse '{class_name}' nicht in '{module_name}' gefunden: {e}")
                traceback.print_exc()
            except Exception as e:
                print(f"Fehler beim Initialisieren von '{section}' (Typ: {m_type}): {e}")
                traceback.print_exc()

            if obj:
                self.system.register_module(obj)
                
                obj.plot_config = [p.strip() for p in cfg.get('plots', '').split(',') if p.strip()]
                obj.y2plot_config = [p.strip() for p in cfg.get('y2plots', '').split(',') if p.strip()]
                self.modules.append(obj)
                mod_map[section] = obj

    def run_generator(self):
        """Generator für die Simulation. Liefert (t_hours, all_metrics) pro Schritt."""
        for step in range(self.n_steps):
            self.system.step()
            
            t_hours = (step * self.time_step) / 3600.0
            all_metrics = {mod.name: mod.get_metrics() for mod in self.modules}
            
            yield t_hours, all_metrics

    def run(self):
        print("Simulation startet (Tkinter-driven)...")
        # Generator initialisieren
        sim_gen = self.run_generator()
        
        def step():
            try:
                # Nächsten Schritt aus dem Generator holen
                t_hours, all_metrics = next(sim_gen)
                self.gui.update(t_hours, all_metrics)
                return True # Weiterlaufen
            except StopIteration:
                return False # Ende der Simulation
            except Exception as e:
                print(f"Fehler in Simulations-Schritt: {e}")
                traceback.print_exc()
                return False

        # Simulation in den Tkinter-Loop hängen
        delay_ms = max(1, int(self.delay * 1000))
        self.gui.start_simulation_loop(step, delay_ms=delay_ms)
        
        # GUI starten (blockiert hier)
        self.gui.show()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='basic_charge.ini')
    args = parser.parse_args()
    
    config_path = args.config
    if not os.path.exists(config_path):
        alt_path = os.path.join('examples', config_path)
        if os.path.exists(alt_path):
            config_path = alt_path
        else:
            print(f"Fehler: Konfigurationsdatei {config_path} nicht gefunden.")
            sys.exit(1)

    SimulationRunner(config_path).run()
#!/usr/bin/env python3
import psutil
import time
import os
import logging
from collections import deque

# Configuration
VICTRON_PATH = "/opt/victronenergy"
SYSTEM_PROGS = ["dbus-daemon", "flashmq", "localsettings"]
UPDATE_INTERVAL = 10.0
NEW_PROC_BASELINE_DELAY = 10.0
THRESHOLD_FACTOR = 2.5
THRESHOLD_DURATION = 3600 # 1 hour
TABLE_LOG_INTERVAL = 300  # Log table every 5 minutes

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

def format_bytes(n, suffix='B'):
    for unit in ['', 'K', 'M', 'G', 'T']:
        if abs(n) < 1024.0:
            return f"{n:3.1f}{unit}{suffix}"
        n /= 1024.0
    return f"{n:.1f}P{suffix}"

class MemWatchService:
    def __init__(self):
        self.procs = {} # pid -> {name, proc, baseline_rss, threshold_start_time, discovery_time}
        self.start_time = time.time()

    def update_procs(self):
        now = time.time()
        current_pids = set()
        
        for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline']):
            try:
                pid = proc.info['pid']
                current_pids.add(pid)
                
                if pid not in self.procs:
                    exe = proc.info['exe'] or ""
                    cmdline = " ".join(proc.info['cmdline'] or [])
                    
                    is_victron = exe.startswith(VICTRON_PATH) or cmdline.startswith(VICTRON_PATH)
                    is_system = any(prog in (proc.info['name'] or "") for prog in SYSTEM_PROGS)
                    
                    if is_victron or is_system:
                        name = proc.info['name'] or (os.path.basename(exe) if exe else "unknown")
                        self.procs[pid] = {
                            'name': name,
                            'proc': proc,
                            'baseline_rss': None,
                            'discovery_time': now,
                            'threshold_start_time': None
                        }
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Cleanup
        for pid in list(self.procs.keys()):
            if pid not in current_pids:
                del self.procs[pid]

    def check_memory(self):
        now = time.time()
        for pid, info in self.procs.items():
            try:
                curr_rss = info['proc'].memory_info().rss
                
                if info['baseline_rss'] is None:
                    if (now - info['discovery_time']) >= NEW_PROC_BASELINE_DELAY:
                        info['baseline_rss'] = curr_rss
                        logging.info(f"Set baseline for {info['name']} (PID {pid}): {format_bytes(curr_rss)}")
                    continue

                if curr_rss > info['baseline_rss'] * THRESHOLD_FACTOR:
                    if info['threshold_start_time'] is None:
                        info['threshold_start_time'] = now
                        logging.warning(f"Memory threshold exceeded for {info['name']} (PID {pid}): {format_bytes(curr_rss)} > {THRESHOLD_FACTOR}x baseline")
                    elif (now - info['threshold_start_time']) >= THRESHOLD_DURATION:
                        self.restart_service(info)
                        info['threshold_start_time'] = None # Reset after restart attempt
                else:
                    if info['threshold_start_time'] is not None:
                        logging.info(f"Memory normalized for {info['name']} (PID {pid})")
                        info['threshold_start_time'] = None

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

    def find_service_name(self, proc_name):
        """Tries to find the service name in /service/ that matches the process name."""
        if os.path.exists(f"/service/{proc_name}"):
            return proc_name
        
        # Search for service directory containing the name
        try:
            for s in os.listdir("/service"):
                if proc_name in s:
                    return s
        except:
            pass
        return None

    def restart_service(self, info):
        name = info['name']
        svc_name = self.find_service_name(name)
        
        if svc_name:
            svc_path = f"/service/{svc_name}"
            logging.error(f"RESTARTING SERVICE {svc_name} (PID {info['proc'].pid}) due to high memory usage (>1h over threshold)")
            os.system(f"svc -d {svc_path}")
            time.sleep(2)
            os.system(f"svc -u {svc_path}")
        else:
            logging.error(f"Cannot restart {name}: No matching service found in /service/")

    def log_table(self):
        candidates = []
        for pid, info in self.procs.items():
            if info['baseline_rss'] is None: continue
            try:
                curr_rss = info['proc'].memory_info().rss
                growth = curr_rss / info['baseline_rss'] if info['baseline_rss'] > 0 else 0
                candidates.append((pid, info['name'], info['baseline_rss'], curr_rss, growth))
            except: continue
        
        # Sort by growth factor
        candidates.sort(key=lambda x: x[4], reverse=True)
        
        logging.info("--- Memory Report (Sorted by Growth) ---")
        logging.info(f"{'PID':<8} {'PROCESS NAME':<25} {'BASELINE':<10} {'CURRENT':<10} {'GROWTH'}")
        for pid, name, base, curr, growth in candidates[:15]:
            logging.info(f"{pid:<8} {name:<25} {format_bytes(base):<10} {format_bytes(curr):<10} {growth:.2f}x")
        logging.info("---------------------")

def main():
    service = MemWatchService()
    last_table = time.time()
    early_reports = [10, 30, 60]
    logging.info("dbus-ibr-memwatch service started")
    while True:
        try:
            service.update_procs()
            service.check_memory()
            
            now = time.time()
            uptime = now - service.start_time
            
            should_log = False
            if early_reports and uptime >= early_reports[0]:
                should_log = True
                early_reports.pop(0)
            elif now - last_table >= TABLE_LOG_INTERVAL:
                should_log = True

            if should_log:
                service.log_table()
                last_table = now

        except Exception as e:
            logging.error(f"Error in main loop: {e}")
            
        time.sleep(UPDATE_INTERVAL)

if __name__ == "__main__":
    main()

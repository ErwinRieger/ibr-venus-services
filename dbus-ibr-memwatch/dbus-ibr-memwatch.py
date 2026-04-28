#!/usr/bin/env python3
import psutil
import time
import os
import logging

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

class WatchedProcess:
    # Persistent stats shared across instances (per process name)
    restart_counts = {} 
    pid_changes = {}    
    pid_history = {}    

    def __init__(self, pid, name, proc, discovery_time):
        self.pid = pid
        self.name = name
        self.proc = proc
        self.discovery_time = discovery_time
        self.baseline_rss = None
        self.threshold_start_time = None
        
        # Track PID changes
        if name in self.pid_history and self.pid_history[name] != pid:
            self.pid_changes[name] = self.pid_changes.get(name, 0) + 1
        self.pid_history[name] = pid

    def get_rss(self):
        try:
            return self.proc.memory_info().rss
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None
            
    @property
    def restarts(self):
        return self.restart_counts.get(self.name, 0)
        
    @property
    def changes(self):
        return self.pid_changes.get(self.name, 0)

    def mark_restart(self):
        self.restart_counts[self.name] = self.restart_counts.get(self.name, 0) + 1

class MemWatchService:
    def __init__(self):
        self.procs = {} # pid -> WatchedProcess
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
                        self.procs[pid] = WatchedProcess(pid, name, proc, now)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Cleanup
        for pid in list(self.procs.keys()):
            if pid not in current_pids:
                del self.procs[pid]

    def check_memory(self):
        now = time.time()
        for pid, p in self.procs.items():
            curr_rss = p.get_rss()
            if curr_rss is None: continue
            
            if p.baseline_rss is None:
                if (now - p.discovery_time) >= NEW_PROC_BASELINE_DELAY:
                    p.baseline_rss = curr_rss
                    logging.info(f"Baseline for {p.name} (PID {pid}) set to {format_bytes(curr_rss)}")
                continue

            if curr_rss > p.baseline_rss * THRESHOLD_FACTOR:
                if p.threshold_start_time is None:
                    p.threshold_start_time = now
                    logging.warning(f"Memory threshold exceeded for {p.name} (PID {pid}): {format_bytes(curr_rss)} > {THRESHOLD_FACTOR}x baseline")
                elif (now - p.threshold_start_time) >= THRESHOLD_DURATION:
                    self.restart_service(p)
                    p.threshold_start_time = None
            else:
                if p.threshold_start_time is not None:
                    logging.info(f"Memory normalized for {p.name} (PID {pid})")
                    p.threshold_start_time = None

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

    def restart_service(self, p):
        if p.name == "dbus-daemon":
            p.mark_restart()
            logging.error(f"RESTARTING DBUS-DAEMON (PID {p.pid}) due to high memory usage")
            os.system("/etc/init.d/dbus-1 restart")
            return

        svc_name = self.find_service_name(p.name)
        if svc_name:
            p.mark_restart()
            svc_path = f"/service/{svc_name}"
            logging.error(f"RESTARTING SERVICE {svc_name} (PID {p.pid}) due to high memory usage (>1h over threshold)")
            os.system(f"svc -d {svc_path}")
            time.sleep(2)
            os.system(f"svc -u {svc_path}")
        else:
            logging.error(f"Cannot restart {p.name}: No matching service found in /service/")

    def log_table(self, now, last_table_time):
        candidates = []
        for pid, p in self.procs.items():
            if p.baseline_rss is None: continue
            curr_rss = p.get_rss()
            if curr_rss is None: continue
            
            growth = curr_rss / p.baseline_rss if p.baseline_rss > 0 else 0
            candidates.append((pid, p.name, p.baseline_rss, curr_rss, growth, p.restarts, p.changes))
        
        # Sort by growth factor
        candidates.sort(key=lambda x: x[4], reverse=True)
        
        dt = int(now - last_table_time)
        logging.info(f"--- Memory Report (Sorted by Growth), dt: {dt}s ---")
        logging.info(f"{'PID':<8} {'PROCESS NAME':<25} {'BASELINE':<10} {'CURRENT':<10} {'GROWTH':<8} {'RESTARTS':<10} {'CHANGES'}")
        for pid, name, base, curr, growth, restarts, changes in candidates[:15]:
            logging.info(f"{pid:<8} {name:<25} {format_bytes(base):<10} {format_bytes(curr):<10} {growth:.2f}x       {restarts:<10} {changes}")
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
                service.log_table(now, last_table)
                last_table = now

        except Exception as e:
            logging.error(f"Error in main loop: {e}")
            
        time.sleep(UPDATE_INTERVAL)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import psutil
import time
import os
from collections import deque
from datetime import datetime

# Configuration
VICTRON_PATH = "/opt/victronenergy"
SYSTEM_PROGS = ["dbus-daemon", "flashmq", "localsettings"]
UPDATE_INTERVAL = 1.0
NEW_PROC_BASELINE_DELAY = 10.0  # seconds to wait for a new process to stabilize
RATE_WINDOW = 3600             # seconds for sliding rate calculation (1 hour)

def format_bytes(n, suffix='B'):
    """Converts bytes to human readable format (B, K, M, G)."""
    for unit in ['', 'K', 'M', 'G', 'T']:
        if abs(n) < 1024.0:
            return f"{n:3.1f}{unit}{suffix}"
        n /= 1024.0
    return f"{n:.1f}P{suffix}"

class MemWatch:
    def __init__(self):
        self.procs = {} # pid -> {name, proc, baseline_rss, baseline_time, discovery_time, rss_history}
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
                            'baseline_time': None,
                            'discovery_time': now,
                            'rss_history': deque(maxlen=RATE_WINDOW)
                        }
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Cleanup
        for pid in list(self.procs.keys()):
            if pid not in current_pids:
                del self.procs[pid]

    def process_baselines(self):
        now = time.time()
        for pid, info in self.procs.items():
            try:
                curr_rss = info['proc'].memory_info().rss
                
                if info['baseline_rss'] is None:
                    if (now - info['discovery_time']) >= NEW_PROC_BASELINE_DELAY:
                        info['baseline_rss'] = curr_rss
                        info['baseline_time'] = now
                        info['rss_history'].append((now, curr_rss))
                else:
                    info['rss_history'].append((now, curr_rss))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

    def display(self):
        now = time.time()
        candidates = []
        
        for pid, info in self.procs.items():
            if info['baseline_rss'] is None or len(info['rss_history']) < 2:
                continue
            
            try:
                hist = list(info['rss_history'])
                curr_time, curr_rss = hist[-1]
                old_time, old_rss = hist[0]
                
                # Sliding window rate calculation (up to 1 hour)
                window_duration = curr_time - old_time
                if window_duration > 3600:
                    rate_h = (curr_rss - old_rss) / 3600
                else: window_duration > 0:
                    rate_h = ((curr_rss - old_rss) / window_duration
                else:
                    rate_h = 0
                
                total_growth = curr_rss - info['baseline_rss']
                
                candidates.append({
                    'pid': pid,
                    'name': info['name'],
                    'start_mem': format_bytes(info['baseline_rss']),
                    'curr_mem': format_bytes(curr_rss),
                    'curr_rss_val': curr_rss,
                    'growth_val': total_growth,
                    'growth_str': format_bytes(total_growth),
                    'rate_h_str': format_bytes(rate_h, suffix='/h'),
                    'cpu': info['proc'].cpu_percent()
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Sort by total growth primary, and current absolute memory secondary
        candidates.sort(key=lambda x: (x['growth_val'], x['curr_rss_val']), reverse=True)

        # Clear Screen
        elapsed = int(now - self.start_time)
        hours, remainder = divmod(elapsed, 3600)
        minutes, seconds = divmod(remainder, 60)
        elapsed_str = f"{hours:02}:{minutes:02}:{seconds:02}"
        
        print("\033[H\033[J", end="")
        print(f"Venus OS MemWatch (Sorted by Total Growth) - Uptime: {elapsed_str}")
        print(f"{'PID':<8} {'PROCESS NAME':<25} {'START':<10} {'CURRENT':<10} {'GROWTH':<10} {'RATE/h':<12} {'CPU%'}")
        print("-" * 87)
        
        for c in candidates[:5]:
            print(f"{c['pid']:<8} {c['name']:<25} {c['start_mem']:<10} {c['curr_mem']:<10} {c['growth_str']:<10} {c['rate_h_str']:<12} {c['cpu']:>4.1f}%")

def main():
    watch = MemWatch()
    try:
        while True:
            watch.update_procs()
            watch.process_baselines()
            watch.display()
            time.sleep(UPDATE_INTERVAL)
    except KeyboardInterrupt:
        print("\nStopped.")

if __name__ == "__main__":
    main()

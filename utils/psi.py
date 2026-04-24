#!/usr/bin/env python3
import time
import math
import os

class PSIEmulator:
    def __init__(self):
        # [avg10, avg60, avg300, total_us, last_inst]
        self.state = {
            "cpu":    {"some": [0.0, 0.0, 0.0, 0, 0.0]},
            "memory": {"some": [0.0, 0.0, 0.0, 0, 0.0], "full": [0.0, 0.0, 0.0, 0, 0.0]},
            "io":     {"some": [0.0, 0.0, 0.0, 0, 0.0], "full": [0.0, 0.0, 0.0, 0, 0.0]},
        }
        self.last_time = time.time()
        
    def update_avg(self, old_avg, current_val, window_size, interval):
        if interval <= 0: return old_avg
        alpha = 1 - math.exp(-interval / window_size)
        return old_avg * (1 - alpha) + (current_val * 100.0) * alpha

    def update(self, cpu_usage, io_stall_detected, pgscan_delta, pswp_delta):
        now = time.time()
        interval = now - self.last_time
        if interval <= 0: return
        self.last_time = now

        # Heuristic: Map system metrics to pressure intensity (0.0 to 1.0)
        inst = {
            "cpu":    {"some": min(1.0, cpu_usage / 100.0)},
            "io":     {"some": 0.7 if io_stall_detected else 0.0, "full": 0.2 if io_stall_detected else 0.0},
            "memory": {"some": min(1.0, pgscan_delta / 20.0), "full": min(1.0, pswp_delta / 2.0)}
        }

        for res in self.state:
            for s_f in self.state[res]:
                current_val = inst[res][s_f]
                avgs = self.state[res][s_f]
                avgs[0] = self.update_avg(avgs[0], current_val, 10, interval)
                avgs[1] = self.update_avg(avgs[1], current_val, 60, interval)
                avgs[2] = self.update_avg(avgs[2], current_val, 300, interval)
                avgs[3] += int(current_val * interval * 1000000)
                avgs[4] = current_val

    def render(self, resource, modes=["some", "full"]):
        res = self.state[resource]
        out = []
        for s_f in modes:
            if s_f not in res: continue
            v = res[s_f]
            # total is stored in microseconds, convert to seconds for display
            total_sec = v[3] / 1000000.0
            rate = v[4]
            out.append(f"{s_f:<4} avg10={v[0]:>6.2f} avg60={v[1]:>6.2f} avg300={v[2]:>6.2f} total={total_sec:>10.2f}s rate={rate:>5.2f}s/s")
        return "\n".join(out)

def get_cpu_stat():
    try:
        with open("/proc/stat", "r") as f:
            line = f.readline()
            parts = list(map(int, line.split()[1:]))
            return sum(parts), parts[3], parts[4] # total, idle, iowait
    except: return 0, 0, 0

def get_vmstat():
    try:
        res = {}
        with open("/proc/vmstat", "r") as f:
            for line in f:
                parts = line.split()
                if len(parts) == 2: res[parts[0]] = int(parts[1])
        return res
    except: return {}

def main():
    emu = PSIEmulator()
    start_time = time.time()
    prev_total, prev_idle, prev_iowait = get_cpu_stat()
    prev_vm = get_vmstat()
    
    print("\033[H\033[J", end="")
    
    try:
        while True:
            time.sleep(1.0)
            curr_total, curr_idle, curr_iowait = get_cpu_stat()
            curr_vm = get_vmstat()
            
            diff_total = curr_total - prev_total
            if diff_total > 0:
                cpu_usage = 100 * (1 - (curr_idle - prev_idle) / diff_total)
                io_stall = (curr_iowait > prev_iowait)
            else:
                cpu_usage = 0
                io_stall = False
            
            # Catch all pgscan activities (direct and kswapd)
            pgscan = sum(v for k,v in curr_vm.items() if 'pgscan' in k) - \
                     sum(v for k,v in prev_vm.items() if 'pgscan' in k)
            pswp = (curr_vm.get('pswpin', 0) + curr_vm.get('pswpout', 0)) - \
                   (prev_vm.get('pswpin', 0) + prev_vm.get('pswpout', 0))

            emu.update(cpu_usage, io_stall, pgscan, pswp)
            
            now = time.time()
            elapsed = int(now - start_time)
            hours, remainder = divmod(elapsed, 3600)
            minutes, seconds = divmod(remainder, 60)
            elapsed_str = f"{hours:02}:{minutes:02}:{seconds:02}"

            print("\033[H", end="")
            print(f"Emulated PSI (Pressure Stall Info) - Uptime: {elapsed_str}")
            print("Unit: avg is % of time, total is cumulative seconds.\n")
            
            descriptions = {
                "cpu":    "Some: Contention - Tasks waiting for CPU cycles.",
                "io":     "Full: Blocked - All tasks waiting for storage/network.",
                "memory": "Full: Thrashing - System busy reclaiming/swapping."
            }

            for res in ["cpu", "io", "memory"]:
                print(f"/proc/pressure/{res} ({descriptions[res]})")
                # For CPU show 'some', for others show 'full'
                render_mode = ["some"] if res == "cpu" else ["full"]
                print(emu.render(res, modes=render_mode))
                print()

            prev_total, prev_idle, prev_iowait = curr_total, curr_idle, curr_iowait
            prev_vm = curr_vm
    except KeyboardInterrupt:
        print("\nStopped.")

if __name__ == "__main__":
    main()

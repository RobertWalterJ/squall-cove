#!/usr/bin/env python3
"""Run a build/scan repeatedly until every Overpass group is cached (Overpass is flaky).  python build_all.py"""
import sys, time, realmap as R
JOBS = [('scan', 'scan_mudros', 39.8800, 25.2700, 2500.0),
        ('scan', 'scan_airport', 39.9170, 25.2360, 2500.0),
        ('build', 'lemnos_myrina', 39.87605, 25.05666, 768.0),
        ('build', 'lemnos_mudros', 39.87281, 25.26742, 768.0),
        ('build', 'lemnos_airport', 39.9170, 25.2360, 768.0)]
if __name__ == '__main__':
    jobs = JOBS if len(sys.argv) < 2 else [j for j in JOBS if j[1] in sys.argv[1:]]
    for kind, mid, lat, lon, size in jobs:
        for attempt in range(12):
            try:
                R.build(mid, lat, lon, size, scan=(kind == 'scan')); break
            except RuntimeError as e:
                print('attempt', attempt, 'failed:', str(e)[:150], flush=True); time.sleep(20)

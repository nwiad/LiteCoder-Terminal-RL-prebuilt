#!/usr/bin/env python3
"""Generate realistic CPU utilization data for anomaly detection task."""
import csv
import random
import math
from datetime import datetime, timedelta, timezone

random.seed(12345)

start = datetime(2025, 1, 6, 0, 0, 0, tzinfo=timezone.utc)
interval = timedelta(seconds=30)
num_points = 20160  # 1 week

rows = []
t = start

# Base parameters
base_load = 2.5
noise_std = 0.4

# Pre-select indices for anomalies (spikes and dips)
spike_indices = set(random.sample(range(500, num_points - 500), 35))
dip_indices = set(random.sample(range(500, num_points - 500) , 25))
dip_indices -= spike_indices

# Pre-select indices for missing values (~1% missing)
missing_indices = set(random.sample(range(num_points), 200))
# Make sure missing values don't overlap with anomalies
missing_indices -= spike_indices
missing_indices -= dip_indices

for i in range(num_points):
    ts = (start + interval * i).strftime("%Y-%m-%dT%H:%M:%SZ")

    if i in missing_indices:
        rows.append([ts, ""])
        continue

    # Diurnal pattern: higher during business hours (9-17 UTC)
    hour = (start + interval * i).hour
    diurnal = 1.0 + 0.8 * math.exp(-0.5 * ((hour - 13) / 3.0) ** 2)

    # Weekly pattern: lower on weekends
    day_of_week = (start + interval * i).weekday()
    weekly = 1.0 if day_of_week < 5 else 0.7

    load = base_load * diurnal * weekly + random.gauss(0, noise_std)

    # Inject spikes
    if i in spike_indices:
        load = base_load * diurnal * weekly + random.uniform(5.0, 9.0)

    # Inject dips
    if i in dip_indices:
        load = max(0.0, base_load * diurnal * weekly - random.uniform(4.5, 7.0))

    load = round(max(0.0, load), 4)
    rows.append([ts, str(load)])

with open("/app/input.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["timestamp", "cpu_load"])
    writer.writerows(rows)

print(f"Generated {len(rows)} rows to /app/input.csv")
print(f"Missing values: {len(missing_indices)}")
print(f"Spike anomalies: {len(spike_indices)}")
print(f"Dip anomalies: {len(dip_indices)}")

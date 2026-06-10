#!/usr/bin/env python3
"""Generate small representative test data files for the sensor pipeline task."""
import json
import gzip
import os

def generate():
    raw_dir = "/data/raw"
    os.makedirs(raw_dir, exist_ok=True)

    # 3 devices, 2 hourly files, small number of records per device
    devices = ["SENSOR-001", "SENSOR-002", "SENSOR-003"]
    base_date = "2024-01-15"

    # --- Hour 00 file ---
    records_h00 = []
    for dev in devices:
        for i in range(36):  # 36 records = 3 minutes at 5-sec intervals
            sec = i * 5
            mm = sec // 60
            ss = sec % 60
            ts = f"{base_date}T00:{mm:02d}:{ss:02d}"
            rec = {
                "device_id": dev,
                "timestamp": ts,
                "temperature": round(20.0 + (i % 5) * 0.3, 2),
                "humidity": round(45.0 + (i % 7) * 0.5, 1),
                "power_consumption": round(2.0 + (i % 3) * 0.5, 3),
                "air_quality": 50 + (i % 10) * 5,
                "motion_detected": i % 4 == 0
            }

            # Quality issue: null temperature for SENSOR-001 at record 5
            if dev == "SENSOR-001" and i == 5:
                rec["temperature"] = None

            # Quality issue: null humidity for SENSOR-002 at record 10
            if dev == "SENSOR-002" and i == 10:
                rec["humidity"] = None

            # Quality issue: out-of-range temperature for SENSOR-003 at record 15
            if dev == "SENSOR-003" and i == 15:
                rec["temperature"] = 85.5  # outside [-40, 60]

            # Quality issue: out-of-range humidity for SENSOR-001 at record 20
            if dev == "SENSOR-001" and i == 20:
                rec["humidity"] = 150  # outside [0, 100]

            records_h00.append(rec)

    # Quality issue: duplicate timestamp for SENSOR-001
    dup_rec = {
        "device_id": "SENSOR-001",
        "timestamp": f"{base_date}T00:00:10",
        "temperature": 21.5,
        "humidity": 46.0,
        "power_consumption": 3.0,
        "air_quality": 60,
        "motion_detected": False
    }
    records_h00.append(dup_rec)

    with gzip.open(os.path.join(raw_dir, "sensor_data_20240115_00.json.gz"), "wt", encoding="utf-8") as f:
        for rec in records_h00:
            f.write(json.dumps(rec) + "\n")

    # --- Hour 01 file ---
    records_h01 = []
    for dev in devices:
        for i in range(36):  # 36 records = 3 minutes
            sec = i * 5
            mm = sec // 60
            ss = sec % 60
            ts = f"{base_date}T01:{mm:02d}:{ss:02d}"
            rec = {
                "device_id": dev,
                "timestamp": ts,
                "temperature": round(19.5 + (i % 6) * 0.4, 2),
                "humidity": round(44.0 + (i % 5) * 0.8, 1),
                "power_consumption": round(1.8 + (i % 4) * 0.6, 3),
                "air_quality": 40 + (i % 8) * 7,
                "motion_detected": i % 3 == 0
            }

            # Quality issue: null temperature for SENSOR-002 at record 8
            if dev == "SENSOR-002" and i == 8:
                rec["temperature"] = None

            # Quality issue: out-of-range humidity for SENSOR-003 at record 25
            if dev == "SENSOR-003" and i == 25:
                rec["humidity"] = -5  # outside [0, 100]

            records_h01.append(rec)

    with gzip.open(os.path.join(raw_dir, "sensor_data_20240115_01.json.gz"), "wt", encoding="utf-8") as f:
        for rec in records_h01:
            f.write(json.dumps(rec) + "\n")

    print(f"Generated 2 hourly files in {raw_dir}")
    print(f"  sensor_data_20240115_00.json.gz: {len(records_h00)} records")
    print(f"  sensor_data_20240115_01.json.gz: {len(records_h01)} records")

if __name__ == "__main__":
    generate()

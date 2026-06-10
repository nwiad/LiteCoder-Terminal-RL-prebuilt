#!/usr/bin/env python3
"""California Wildfire & Power Shut-off Analysis"""
import csv
import json
import math
import os
from datetime import datetime, timedelta

EARTH_R = 6371.0
BUFFER_KM = 5.0
TEMP_DAYS = 30
TEMP_KM = 50.0

INPUT_WF = "/app/data/wildfires.csv"
INPUT_TL = "/app/data/transmission_lines.csv"
INPUT_PS = "/app/data/psps_events.csv"
OUT_WF = "/app/output/wildfires_cleaned.csv"
OUT_PS = "/app/output/psps_cleaned.csv"
OUT_SJ = "/app/output/spatial_join.csv"
OUT_SR = "/app/output/summary_report.json"
OUT_MAP = "/app/output/wildfire_psps_map.png"


def haversine(lat1, lon1, lat2, lon2):
    la1, lo1 = math.radians(lat1), math.radians(lon1)
    la2, lo2 = math.radians(lat2), math.radians(lon2)
    dlat = la2 - la1
    dlon = lo2 - lo1
    a = math.sin(dlat / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin(dlon / 2) ** 2
    return EARTH_R * 2 * math.asin(math.sqrt(a))


def sfloat(v):
    if v is None: return None
    v = str(v).strip()
    if v == "" or v.lower() == "nan": return None
    try: return float(v)
    except: return None


def read_csv(fp):
    with open(fp, "r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(fp, rows, fields):
    with open(fp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def parse_date(v):
    if v is None: return None
    v = str(v).strip()
    if v == "": return None
    try: return datetime.strptime(v, "%Y-%m-%d").date()
    except ValueError: return None


def parse_dt(v):
    if v is None: return None
    v = str(v).strip()
    if v == "": return None
    try: return datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
    except ValueError: return None


def step1_clean():
    """Data cleaning for wildfires and PSPS events."""
    # --- Wildfires ---
    raw_wf = read_csv(INPUT_WF)
    total_fires_raw = len(raw_wf)

    cleaned_wf = []
    for r in raw_wf:
        lat = sfloat(r.get("latitude"))
        lon = sfloat(r.get("longitude"))
        if lat is None or lon is None:
            continue
        ab = sfloat(r.get("acres_burned"))
        if ab is None or ab <= 0:
            continue
        sd = parse_date(r.get("start_date"))
        if sd is None:
            continue
        row = dict(r)
        row["is_utility_caused"] = str(r.get("cause", "").strip() == "Electrical")
        row["_sort_date"] = sd
        cleaned_wf.append(row)

    cleaned_wf.sort(key=lambda x: (x["_sort_date"], x["fire_id"]))
    for r in cleaned_wf:
        del r["_sort_date"]

    wf_fields = ["fire_id", "fire_name", "cause", "latitude", "longitude",
                  "start_date", "end_date", "acres_burned", "county", "is_utility_caused"]
    write_csv(OUT_WF, cleaned_wf, wf_fields)

    # --- PSPS ---
    raw_ps = read_csv(INPUT_PS)
    total_psps_raw = len(raw_ps)

    cleaned_ps = []
    for r in raw_ps:
        lat = sfloat(r.get("latitude"))
        lon = sfloat(r.get("longitude"))
        if lat is None or lon is None:
            continue
        sdt = parse_dt(r.get("start_datetime"))
        if sdt is None:
            continue
        row = dict(r)
        ca = sfloat(r.get("customers_affected"))
        row["customers_affected"] = int(ca) if ca is not None else 0
        row["_sort_dt"] = sdt
        cleaned_ps.append(row)

    cleaned_ps.sort(key=lambda x: (x["_sort_dt"], x["event_id"]))
    for r in cleaned_ps:
        del r["_sort_dt"]

    ps_fields = ["event_id", "utility", "start_datetime", "end_datetime",
                  "latitude", "longitude", "customers_affected", "county"]
    write_csv(OUT_PS, cleaned_ps, ps_fields)

    return cleaned_wf, cleaned_ps, total_fires_raw, total_psps_raw


def step2_spatial_join(cleaned_wf):
    """Spatial join: fires within 5km of transmission line endpoints."""
    tl_rows = read_csv(INPUT_TL)
    results = []

    for fire in cleaned_wf:
        f_lat = float(fire["latitude"])
        f_lon = float(fire["longitude"])
        for tl in tl_rows:
            lat_s = float(tl["lat_start"])
            lon_s = float(tl["lon_start"])
            lat_e = float(tl["lat_end"])
            lon_e = float(tl["lon_end"])
            d_start = haversine(f_lat, f_lon, lat_s, lon_s)
            d_end = haversine(f_lat, f_lon, lat_e, lon_e)
            dist = min(d_start, d_end)
            if dist <= BUFFER_KM:
                results.append({
                    "fire_id": fire["fire_id"],
                    "fire_name": fire["fire_name"],
                    "cause": fire["cause"],
                    "is_utility_caused": fire["is_utility_caused"],
                    "line_id": tl["line_id"],
                    "utility": tl["utility"],
                    "distance_km": round(dist, 3)
                })

    results.sort(key=lambda x: (x["fire_id"], x["distance_km"]))
    sj_fields = ["fire_id", "fire_name", "cause", "is_utility_caused",
                  "line_id", "utility", "distance_km"]
    write_csv(OUT_SJ, results, sj_fields)
    return results


def step3_temporal(cleaned_wf, cleaned_ps):
    """Temporal correlation: PSPS events with nearby fire within 30 days."""
    total = len(cleaned_ps)
    if total == 0:
        return total, 0, 0.0

    # Pre-parse fire dates and coords
    fires_parsed = []
    for f in cleaned_wf:
        sd = parse_date(f["start_date"])
        if sd is None:
            continue
        fires_parsed.append({
            "date": sd,
            "lat": float(f["latitude"]),
            "lon": float(f["longitude"])
        })

    count = 0
    for ps in cleaned_ps:
        ps_dt = parse_dt(ps["start_datetime"])
        if ps_dt is None:
            continue
        ps_date = ps_dt.date()
        ps_lat = float(ps["latitude"])
        ps_lon = float(ps["longitude"])
        end_date = ps_date + timedelta(days=TEMP_DAYS)

        found = False
        for fp in fires_parsed:
            if fp["date"] >= ps_date and fp["date"] <= end_date:
                d = haversine(fp["lat"], fp["lon"], ps_lat, ps_lon)
                if d <= TEMP_KM:
                    found = True
                    break
        if found:
            count += 1

    rate = round(count / total, 4) if total > 0 else 0.0
    return total, count, rate


def step4_summary(cleaned_wf, cleaned_ps, sj_results,
                   total_fires_raw, total_psps_raw,
                   total_psps_events, psps_with_nearby, corr_rate):
    """Generate summary report JSON."""
    total_fires_cleaned = len(cleaned_wf)
    utility_caused = sum(1 for f in cleaned_wf if f["is_utility_caused"] == "True")
    total_psps_cleaned = len(cleaned_ps)
    fires_near_tl = len(sj_results)
    unique_fires_sj = len(set(r["fire_id"] for r in sj_results))

    # Top counties by utility-caused fires
    county_counts = {}
    for f in cleaned_wf:
        if f["is_utility_caused"] == "True":
            c = f["county"]
            county_counts[c] = county_counts.get(c, 0) + 1

    top_counties = sorted(county_counts.items(), key=lambda x: (-x[1], x[0]))
    top_counties_list = [{"county": c, "count": n} for c, n in top_counties]

    report = {
        "total_fires_raw": total_fires_raw,
        "total_fires_cleaned": total_fires_cleaned,
        "utility_caused_fires": utility_caused,
        "total_psps_raw": total_psps_raw,
        "total_psps_cleaned": total_psps_cleaned,
        "fires_near_transmission_lines": fires_near_tl,
        "unique_fires_in_spatial_join": unique_fires_sj,
        "total_psps_events": total_psps_events,
        "psps_with_nearby_fire": psps_with_nearby,
        "temporal_correlation_rate": corr_rate,
        "top_counties_by_utility_fires": top_counties_list
    }

    with open(OUT_SR, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report


def step5_visualize(cleaned_wf, cleaned_ps):
    """Generate scatter plot map of wildfires and PSPS events."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(10, 8))  # 1000x800 pixels at 100 dpi

    # Separate utility-caused vs other fires
    util_lats, util_lons = [], []
    other_lats, other_lons = [], []
    for f in cleaned_wf:
        lat, lon = float(f["latitude"]), float(f["longitude"])
        if f["is_utility_caused"] == "True":
            util_lats.append(lat)
            util_lons.append(lon)
        else:
            other_lats.append(lat)
            other_lons.append(lon)

    # PSPS locations
    ps_lats, ps_lons = [], []
    for p in cleaned_ps:
        ps_lats.append(float(p["latitude"]))
        ps_lons.append(float(p["longitude"]))

    ax.scatter(util_lons, util_lats, c="red", marker="^", s=80,
               label="Utility-Caused Fire", zorder=3)
    ax.scatter(other_lons, other_lats, c="orange", marker="o", s=60,
               label="Other Fire", zorder=3)
    ax.scatter(ps_lons, ps_lats, c="blue", marker="s", s=50,
               label="PSPS Event", zorder=2, alpha=0.7)

    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title("California Wildfire & PSPS Event Locations")
    ax.legend(loc="best")
    ax.grid(True, alpha=0.3)

    fig.savefig(OUT_MAP, dpi=100, bbox_inches="tight")
    plt.close(fig)


def main():
    os.makedirs("/app/output", exist_ok=True)

    print("Step 1: Cleaning data...")
    cleaned_wf, cleaned_ps, raw_wf_count, raw_ps_count = step1_clean()
    print(f"  Wildfires: {raw_wf_count} raw -> {len(cleaned_wf)} cleaned")
    print(f"  PSPS: {raw_ps_count} raw -> {len(cleaned_ps)} cleaned")

    print("Step 2: Spatial join...")
    sj_results = step2_spatial_join(cleaned_wf)
    print(f"  {len(sj_results)} fire-line pairs found")

    print("Step 3: Temporal correlation...")
    total_ps, ps_nearby, rate = step3_temporal(cleaned_wf, cleaned_ps)
    print(f"  {ps_nearby}/{total_ps} PSPS events with nearby fire, rate={rate}")

    print("Step 4: Summary report...")
    report = step4_summary(cleaned_wf, cleaned_ps, sj_results,
                           raw_wf_count, raw_ps_count,
                           total_ps, ps_nearby, rate)
    print(f"  Report written to {OUT_SR}")

    print("Step 5: Visualization...")
    step5_visualize(cleaned_wf, cleaned_ps)
    print(f"  Map written to {OUT_MAP}")

    print("Done.")


if __name__ == "__main__":
    main()

"""Generate a realistic NYC Green Taxi input.parquet for the analysis task."""
import random
import datetime
import struct
import os

random.seed(42)

# We'll generate a Parquet file using pyarrow
# This script runs during Docker build to create /app/input.parquet

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
except ImportError:
    print("pyarrow not available, skipping generation")
    exit(1)

NUM_ROWS = 5000

# NYC taxi zone IDs (subset of real ones)
ZONE_IDS = [4, 7, 10, 14, 17, 25, 33, 36, 41, 42, 43, 48, 49, 51, 55, 61, 65,
            66, 70, 74, 75, 76, 80, 82, 83, 85, 87, 89, 92, 95, 97, 100, 112,
            116, 119, 120, 127, 128, 129, 130, 131, 132, 138, 145, 146, 150,
            152, 155, 160, 165, 166, 167, 168, 169, 170, 173, 174, 177, 178,
            179, 180, 181, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197,
            198, 210, 215, 217, 220, 223, 225, 226, 228, 231, 232, 233, 235,
            236, 237, 238, 239, 240, 241, 242, 243, 244, 255, 256, 257, 260]

PAYMENT_TYPES = [1, 2, 3, 4, 5]

pickup_datetimes = []
dropoff_datetimes = []
pu_location_ids = []
do_location_ids = []
trip_distances = []
fare_amounts = []
tip_amounts = []
total_amounts = []
passenger_counts = []
payment_types = []

# Base date range: 2024 calendar year
start_date = datetime.datetime(2024, 1, 1, 0, 0, 0)
end_date = datetime.datetime(2024, 12, 31, 23, 59, 59)
date_range_seconds = int((end_date - start_date).total_seconds())

for i in range(NUM_ROWS):
    # Random pickup time across 2024
    offset_sec = random.randint(0, date_range_seconds)
    pickup = start_date + datetime.timedelta(seconds=offset_sec)

    # Inject some invalid rows (~5% of data)
    is_invalid = random.random() < 0.05
    invalid_type = random.choice(["neg_dist", "zero_dist", "neg_fare", "neg_total",
                                   "null_zone", "zero_zone", "neg_duration", "long_dist",
                                   "long_duration"]) if is_invalid else None

    # Trip duration in minutes
    if invalid_type == "neg_duration":
        duration_min = -random.uniform(1, 30)
    elif invalid_type == "long_duration":
        duration_min = random.uniform(361, 600)
    else:
        # Realistic: 3 to 90 minutes, weighted toward shorter trips
        duration_min = random.expovariate(1/15)
        duration_min = max(1, min(duration_min, 120))

    dropoff = pickup + datetime.timedelta(minutes=duration_min)

    # Trip distance
    if invalid_type == "neg_dist":
        dist = -random.uniform(0.1, 5)
    elif invalid_type == "zero_dist":
        dist = 0.0
    elif invalid_type == "long_dist":
        dist = random.uniform(201, 500)
    else:
        dist = round(random.expovariate(1/4) + 0.1, 2)
        dist = min(dist, 50)

    # Fare
    if invalid_type == "neg_fare":
        fare = -random.uniform(1, 20)
    else:
        fare = round(2.50 + dist * random.uniform(2.0, 3.5) + duration_min * 0.35, 2)
        fare = max(2.50, fare)

    # Tip
    ptype = random.choice(PAYMENT_TYPES)
    if ptype == 1:  # credit card
        tip = round(fare * random.uniform(0, 0.30), 2)
    else:
        tip = 0.0

    # Total
    if invalid_type == "neg_total":
        total = -random.uniform(1, 50)
    else:
        surcharge = round(random.uniform(0.5, 3.0), 2)
        total = round(fare + tip + surcharge, 2)

    # Zones
    if invalid_type == "null_zone":
        pu_zone = 0
        do_zone = random.choice(ZONE_IDS)
    elif invalid_type == "zero_zone":
        pu_zone = random.choice(ZONE_IDS)
        do_zone = 0
    else:
        pu_zone = random.choice(ZONE_IDS)
        do_zone = random.choice(ZONE_IDS)

    # Passenger count (with some nulls)
    if random.random() < 0.03:
        pcount = None
    else:
        pcount = float(random.randint(1, 6))

    pickup_datetimes.append(pickup)
    dropoff_datetimes.append(dropoff)
    pu_location_ids.append(pu_zone)
    do_location_ids.append(do_zone)
    trip_distances.append(dist)
    fare_amounts.append(fare)
    tip_amounts.append(tip)
    total_amounts.append(total)
    passenger_counts.append(pcount)
    payment_types.append(ptype)

# Build pyarrow table
table = pa.table({
    "lpep_pickup_datetime": pa.array(pickup_datetimes, type=pa.timestamp("us")),
    "lpep_dropoff_datetime": pa.array(dropoff_datetimes, type=pa.timestamp("us")),
    "PULocationID": pa.array(pu_location_ids, type=pa.int64()),
    "DOLocationID": pa.array(do_location_ids, type=pa.int64()),
    "trip_distance": pa.array(trip_distances, type=pa.float64()),
    "fare_amount": pa.array(fare_amounts, type=pa.float64()),
    "tip_amount": pa.array(tip_amounts, type=pa.float64()),
    "total_amount": pa.array(total_amounts, type=pa.float64()),
    "passenger_count": pa.array(passenger_counts, type=pa.float64()),
    "payment_type": pa.array(payment_types, type=pa.int64()),
})

pq.write_table(table, "/app/input.parquet")
print(f"Generated /app/input.parquet with {NUM_ROWS} rows")

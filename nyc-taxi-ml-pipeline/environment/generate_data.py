"""Generate synthetic NYC Yellow Taxi Trip Record Parquet file."""
import numpy as np
import pandas as pd
import os

np.random.seed(42)
N = 100_000

# Generate pickup datetimes across January 2022
start = pd.Timestamp("2022-01-01")
end = pd.Timestamp("2022-01-31 23:59:59")
pickup_times = pd.to_datetime(
    np.random.randint(start.value, end.value, size=N)
)

# Trip durations: 2-60 minutes, lognormal-ish
trip_minutes = np.clip(np.random.lognormal(mean=2.5, sigma=0.7, size=N), 2, 120)
dropoff_times = pickup_times + pd.to_timedelta(trip_minutes, unit="m")

# Trip distance: correlated with duration
trip_distance = np.clip(trip_minutes * np.random.uniform(0.15, 0.5, size=N), 0.1, 50)

# Inject some invalid rows (~2% negative/zero distance, ~1% negative amounts)
invalid_dist_mask = np.random.random(N) < 0.02
trip_distance[invalid_dist_mask] = np.random.choice([0, -1, -0.5], size=invalid_dist_mask.sum())

passenger_count = np.random.choice([0, 1, 1, 1, 2, 2, 3, 4, 5, 6], size=N).astype(float)
# Inject some nulls in passenger_count
null_mask_pc = np.random.random(N) < 0.01
passenger_count[null_mask_pc] = np.nan

vendor_id = np.random.choice([1, 2], size=N)
ratecode_id = np.random.choice([1, 1, 1, 1, 2, 3, 4, 5, 99], size=N).astype(float)
store_and_fwd_flag = np.random.choice(["Y", "N", "N", "N", "N"], size=N)
pu_location = np.random.randint(1, 266, size=N)
do_location = np.random.randint(1, 266, size=N)
payment_type = np.random.choice([1, 1, 1, 2, 2, 3, 4], size=N)

# Fare components
fare_amount = np.clip(2.5 + trip_distance * np.random.uniform(2.0, 3.5, size=N), 2.5, 200)
extra = np.random.choice([0.0, 0.5, 1.0, 2.5], size=N)
mta_tax = np.full(N, 0.5)
tip_amount = np.where(payment_type == 1, fare_amount * np.random.uniform(0, 0.3, size=N), 0.0)
tolls_amount = np.where(np.random.random(N) < 0.1, np.random.choice([5.76, 6.55, 11.52], size=N), 0.0)
improvement_surcharge = np.full(N, 0.3)
congestion_surcharge = np.random.choice([0.0, 0.0, 2.5, 2.5, 2.5], size=N)
airport_fee = np.where(np.isin(pu_location, [132, 138]) | np.isin(do_location, [132, 138]),
                       1.25, 0.0)

total_amount = fare_amount + extra + mta_tax + tip_amount + tolls_amount + \
               improvement_surcharge + congestion_surcharge + airport_fee

# Inject some invalid total_amount rows (~1%)
invalid_total_mask = np.random.random(N) < 0.01
total_amount[invalid_total_mask] = np.random.choice([0, -1, -5.0], size=invalid_total_mask.sum())

# Inject some nulls in numeric columns
null_mask_fare = np.random.random(N) < 0.005
fare_amount[null_mask_fare] = np.nan
total_amount[null_mask_fare] = np.nan

df = pd.DataFrame({
    "VendorID": vendor_id,
    "tpep_pickup_datetime": pickup_times,
    "tpep_dropoff_datetime": dropoff_times,
    "passenger_count": passenger_count,
    "trip_distance": trip_distance,
    "RatecodeID": ratecode_id,
    "store_and_fwd_flag": store_and_fwd_flag,
    "PULocationID": pu_location,
    "DOLocationID": do_location,
    "payment_type": payment_type,
    "fare_amount": fare_amount,
    "extra": extra,
    "mta_tax": mta_tax,
    "tip_amount": tip_amount,
    "tolls_amount": tolls_amount,
    "improvement_surcharge": improvement_surcharge,
    "total_amount": total_amount,
    "congestion_surcharge": congestion_surcharge,
    "airport_fee": airport_fee,
})

os.makedirs("/app/data", exist_ok=True)
df.to_parquet("/app/data/yellow_tripdata_2022-01.parquet", index=False, engine="pyarrow")
print(f"Generated {len(df)} rows -> /app/data/yellow_tripdata_2022-01.parquet")
print(f"Columns: {list(df.columns)}")
print(f"Null counts:\n{df.isnull().sum()[df.isnull().sum() > 0]}")
print(f"Invalid trip_distance <= 0: {(df['trip_distance'] <= 0).sum()}")
print(f"Invalid total_amount <= 0: {(df['total_amount'] <= 0).sum()}")

"""Generate GeoPulse's complete synthetic GPS mobility dataset."""

import csv
import gzip
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path


# ---------------------------------------------------------
# PROJECT CONFIGURATION
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_FILE = PROJECT_ROOT / "data" / "raw" / "gps_pings.csv.gz"

RECORD_COUNT = 10_000_000
DEVICE_COUNT = 250_000
SIMULATION_DAYS = 7
RANDOM_SEED = 42

# Synthetic study-area bounds around Lagos, Nigeria.
LAT_MIN = 6.40
LAT_MAX = 6.65
LON_MIN = 3.25
LON_MAX = 3.55

# Synthetic urban activity hubs; these are not verified real-world POIs.
ACTIVITY_HUBS = [
    (6.4540, 3.3940),
    (6.4280, 3.4210),
    (6.4900, 3.3600),
    (6.5200, 3.4000),
    (6.4450, 3.4800),
    (6.5700, 3.3500),
    (6.4050, 3.3000),
    (6.6000, 3.4500),
]

# Hourly weights: higher simulated activity during commute periods.
HOURLY_WEIGHTS = [
    0.15, 0.08, 0.05, 0.04, 0.05, 0.15,
    0.55, 1.00, 0.95, 0.65, 0.50, 0.55,
    0.60, 0.55, 0.50, 0.60, 0.75, 1.00,
    0.95, 0.70, 0.45, 0.35, 0.25, 0.18,
]

FIELDNAMES = [
    "DeviceID",
    "Latitude",
    "Longitude",
    "Timestamp",
]


def generate_coordinates(rng):
    """Generate a location concentrated around a synthetic activity hub."""

    center_lat, center_lon = rng.choice(ACTIVITY_HUBS)

    # Approximate local clustering, not an actual movement trajectory.
    latitude = rng.gauss(center_lat, 0.012)
    longitude = rng.gauss(center_lon, 0.015)

    latitude = max(LAT_MIN, min(LAT_MAX, latitude))
    longitude = max(LON_MIN, min(LON_MAX, longitude))

    return round(latitude, 6), round(longitude, 6)


def generate_timestamp(rng, simulation_start):
    """Generate a timestamp within the seven-day simulation window."""

    day_offset = rng.randrange(SIMULATION_DAYS)
    hour = rng.choices(
        range(24),
        weights=HOURLY_WEIGHTS,
        k=1,
    )[0]

    minute = rng.randrange(60)
    second = rng.randrange(60)

    timestamp = simulation_start + timedelta(
        days=day_offset,
        hours=hour,
        minutes=minute,
        seconds=second,
    )

    return timestamp.isoformat()


def main():
    rng = random.Random(RANDOM_SEED)

    # Begin at midnight UTC to keep all timestamps within the
    # defined seven-day window.
    simulation_start = datetime.now(timezone.utc).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    print("GeoPulse synthetic mobility data generation")
    print(f"Records to generate: {RECORD_COUNT:,}")
    print(f"Simulated devices: {DEVICE_COUNT:,}")
    print(f"Simulation duration: {SIMULATION_DAYS} days")
    print(f"Output: {OUTPUT_FILE}")
    print("Generation started...")

    with gzip.open(
        OUTPUT_FILE,
        mode="wt",
        newline="",
        encoding="utf-8",
        compresslevel=1,
    ) as compressed_file:
        writer = csv.DictWriter(
            compressed_file,
            fieldnames=FIELDNAMES,
        )
        writer.writeheader()

        for record_number in range(1, RECORD_COUNT + 1):
            device_number = rng.randrange(1, DEVICE_COUNT + 1)
            latitude, longitude = generate_coordinates(rng)

            writer.writerow(
                {
                    "DeviceID": f"DEVICE_{device_number:07d}",
                    "Latitude": latitude,
                    "Longitude": longitude,
                    "Timestamp": generate_timestamp(
                        rng,
                        simulation_start,
                    ),
                }
            )

            if record_number % 1_000_000 == 0:
                print(
                    f"Progress: {record_number:,} / "
                    f"{RECORD_COUNT:,} records"
                )

    print("Generation completed successfully.")
    print(f"Total records written: {RECORD_COUNT:,}")
    print(f"Dataset location: {OUTPUT_FILE.resolve()}")
    print("Random seed:", RANDOM_SEED)


if __name__ == "__main__":
    main()

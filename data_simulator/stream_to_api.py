from typing import Optional
"""
GuardX — Stream Simulator Data to API

Reads generated CSV and streams rows to the FastAPI ingestion
endpoint via HTTP POST, simulating real-time ESP32 data transmission.

Hardware-Aligned: Sends 5 raw sensor values per reading.
Derived features (temperature_rate, force_variance) are computed
by the preprocessing pipeline — NOT sent from hardware.
"""

import time
import sys
import os
import argparse
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import httpx
except ImportError:
    import requests as httpx  # fallback


# Raw sensor fields that hardware actually sends (NOT derived features)
HARDWARE_FIELDS = [
    "vibration_rms",
    "temperature",
    "cutting_force",
    "motor_current",
    "speed_command_level",
]

# API Authentication — must match GUARDX_API_KEY in .env / ingest.py
API_KEY = os.getenv("GUARDX_API_KEY", "guardx-secret-key-123")
AUTH_HEADERS = {"X-API-Key": API_KEY}


def stream_to_api(
    csv_path: str = "data/cnc_simulation_data.csv",
    api_url: str = "http://localhost:8000/api/v1/ingest",
    rate: float = 1.0,
    batch_size: int = 1,
    max_rows: Optional[int] = None,
):
    """
    Stream CSV data to API endpoint row by row.

    Only sends raw sensor fields (what real hardware would send).
    Derived features (temperature_rate, force_variance) are computed
    server-side by the preprocessing pipeline for feature symmetry.

    Args:
        csv_path: Path to the CSV dataset
        api_url: Ingestion API endpoint URL
        rate: Seconds between sends (1.0 = real-time)
        batch_size: Number of rows per POST (1 = single, >1 = batch)
        max_rows: Max rows to stream (None = all)
    """
    df = pd.read_csv(csv_path)
    if max_rows:
        df = df.head(max_rows)

    total = len(df)
    print(f"[>] Streaming {total:,} rows to {api_url}")
    print(f"    Rate: {rate}s interval | Batch size: {batch_size}")
    print(f"    Hardware fields: {HARDWARE_FIELDS}")
    print(f"    Press Ctrl+C to stop\n")

    client = httpx.Client(headers=AUTH_HEADERS) if hasattr(httpx, 'Client') else None
    sent = 0
    errors = 0

    def _build_payload(row):
        """Build payload from a single row — only raw hardware fields."""
        payload = {}
        for field in HARDWARE_FIELDS:
            if field in row.index:
                payload[field] = float(row[field])
        return payload

    try:
        i = 0
        while i < total:
            if batch_size == 1:
                row = df.iloc[i]
                payload = _build_payload(row)
                try:
                    if client:
                        r = client.post(api_url, json=payload)
                    else:
                        r = httpx.post(api_url, json=payload, headers=AUTH_HEADERS)
                    if r.status_code == 200:
                        sent += 1
                    else:
                        errors += 1
                        print(f"   [!] Row {i}: HTTP {r.status_code}")
                except Exception as e:
                    errors += 1
                    print(f"   [X] Row {i}: {e}")

                if sent % 100 == 0:
                    print(f"   [+] Sent {sent:,}/{total:,} "
                          f"({sent/total:.1%}) | Errors: {errors}")
                i += 1
            else:
                batch = df.iloc[i:i + batch_size]
                payload = {
                    "readings": [
                        _build_payload(row)
                        for _, row in batch.iterrows()
                    ]
                }
                try:
                    batch_url = api_url + "/batch"
                    if client:
                        r = client.post(batch_url, json=payload)
                    else:
                        r = httpx.post(batch_url, json=payload, headers=AUTH_HEADERS)
                    if r.status_code == 200:
                        sent += len(batch)
                    else:
                        errors += len(batch)
                except Exception as e:
                    errors += len(batch)
                    print(f"   [X] Batch at {i}: {e}")

                if sent % 500 == 0:
                    print(f"   [+] Sent {sent:,}/{total:,} "
                          f"({sent/total:.1%}) | Errors: {errors}")
                i += batch_size

            time.sleep(rate)

    except KeyboardInterrupt:
        print(f"\n[STOP] Stopped by user")
    finally:
        if client:
            client.close()
        print(f"\n[+] Stream Summary:")
        print(f"   Sent:   {sent:,}")
        print(f"   Errors: {errors}")
        print(f"   Total:  {total:,}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stream CNC data to GuardX API")
    parser.add_argument("--csv", default="data/cnc_simulation_data.csv",
                        help="Path to CSV dataset")
    parser.add_argument("--url", default="http://localhost:8000/api/v1/ingest",
                        help="API endpoint URL")
    parser.add_argument("--rate", type=float, default=0.1,
                        help="Seconds between sends (default: 0.1 for fast demo)")
    parser.add_argument("--batch", type=int, default=1,
                        help="Batch size per POST")
    parser.add_argument("--max-rows", type=int, default=None,
                        help="Max rows to stream")
    args = parser.parse_args()

    stream_to_api(
        csv_path=args.csv,
        api_url=args.url,
        rate=args.rate,
        batch_size=args.batch,
        max_rows=args.max_rows,
    )

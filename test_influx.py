from database.influx_client import get_influx_client, write_raw_reading, INFLUX_BUCKET_RAW, INFLUX_ORG
from datetime import datetime

res = write_raw_reading(1.0, 1.0, 1.0, datetime.now().isoformat(), 'TEST-1', 'TEST-S1')
print('Write info:', res)

_, _, q = get_influx_client()
try:
    tables = q.query(f'from(bucket: "{INFLUX_BUCKET_RAW}") |> range(start: -5m)')
    print('Query results rows:', sum(len(t.records) for t in tables) if tables else 0)
except Exception as e:
    print('Query failed:', e)

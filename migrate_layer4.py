import sqlite3
conn = sqlite3.connect('data/guardx.db')
try:
    conn.execute('ALTER TABLE processed_features ADD COLUMN machine_id TEXT NOT NULL DEFAULT "CNC-01"')
    conn.execute('ALTER TABLE processed_features ADD COLUMN sensor_id TEXT NOT NULL DEFAULT "MAIN-01"')
    conn.execute('ALTER TABLE processed_features ADD COLUMN vibration_peak_freq REAL')
    conn.execute('ALTER TABLE processed_features ADD COLUMN vibration_fft_amp REAL')
    print("Migration complete")
except Exception as e:
    print(e)
conn.commit()
conn.close()

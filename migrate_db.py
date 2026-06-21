import sqlite3
import os

DB_PATH = "c:/Users/Keerthi Sridhar/Desktop/GAURDX/data/guardx.db"

def migrate():
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute('ALTER TABLE raw_sensor_data ADD COLUMN machine_id TEXT NOT NULL DEFAULT "CNC-01"')
        print("Added machine_id")
    except Exception as e:
        print("machine_id error:", e)
        
    try:
        conn.execute('ALTER TABLE raw_sensor_data ADD COLUMN sensor_id TEXT NOT NULL DEFAULT "MAIN-01"')
        print("Added sensor_id")
    except Exception as e:
        print("sensor_id error:", e)

    conn.commit()
    conn.close()
    
if __name__ == "__main__":
    migrate()

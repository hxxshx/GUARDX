"""
GuardX - Central Configuration
All tunable parameters for the predictive maintenance system.

Hardware-Aligned for Demo Setup:
  ESP32 + MPU6050 + DS18B20 + HX711 + Load Cell + ACS712 + PWM Motor
"""
import os
from dotenv import load_dotenv

load_dotenv()

# === Database ===
DB_PATH = os.getenv("DB_PATH", "data/guardx.db")

# === Sensor Ranges (for validation & normalization) ===
# Calibrated for demo hardware, NOT industrial CNC
SENSOR_RANGES = {
    "vibration_rms":        {"min": 0.0,  "max": 2.0,   "unit": "g"},
    "temperature":          {"min": 10.0, "max": 120.0, "unit": "°C"},
    "temperature_rate":     {"min": -2.0, "max": 2.0,   "unit": "°C/s"},
    "cutting_force":        {"min": 0.0,  "max": 50.0,  "unit": "N"},
    "force_variance":       {"min": 0.0,  "max": 100.0, "unit": "N²"},
    "motor_current":        {"min": 0.0,  "max": 5.0,   "unit": "A"},
    "speed_command_level":  {"min": 0.0,  "max": 100.0, "unit": "%"},
}

# === Normal Operating Baselines (Demo Motor) ===
# These match a small DC/BLDC motor on a demo rig, NOT an industrial CNC spindle.
NORMAL_BASELINES = {
    "vibration_rms":        {"mean": 0.08, "std": 0.02},    # g — MPU6050 RMS
    "temperature":          {"mean": 32.0, "std": 2.5},     # °C — DS18B20
    "temperature_rate":     {"mean": 0.0,  "std": 0.05},    # °C/s — derived ΔT/Δt
    "cutting_force":        {"mean": 8.0,  "std": 1.5},     # N — HX711 + Load Cell
    "force_variance":       {"mean": 2.0,  "std": 0.8},     # N² — rolling var of force
    "motor_current":        {"mean": 0.5,  "std": 0.08},    # A — ACS712
    "speed_command_level":  {"mean": 65.0, "std": 10.0},    # % — ESP32 PWM duty cycle
}

# === Demo-Motor Thresholds (Warning / Critical) ===
# Calibrated for small motor, NOT real CNC. Judges may question scaling.
DEMO_THRESHOLDS = {
    "vibration_rms":   {"warning": 0.14, "critical": 0.22},  # g
    "temperature":     {"warning": 45.0, "critical": 60.0},  # °C
    "cutting_force":   {"warning": 15.0, "critical": 25.0},  # N
    "motor_current":   {"warning": 1.0,  "critical": 1.8},   # A
}

# === Preprocessing ===
SMOOTHING_WINDOW = int(os.getenv("SMOOTHING_WINDOW", 10))          # Moving average window size
ROLLING_WINDOW = int(os.getenv("ROLLING_WINDOW", 10))             # Rolling statistics window — MUST match simulator
OUTLIER_IQR_MULTIPLIER = float(os.getenv("OUTLIER_IQR_MULTIPLIER", 1.5))

# === Feature Symmetry ===
# CRITICAL: Simulator time-step MUST equal real sampling interval.
# temperature_rate and force_variance depend on this being 1 second.
SIMULATOR_SAMPLE_RATE = 1  # seconds between readings — MUST match live hardware rate

# === ML Engine ===
ML_PHASE_B_THRESHOLD = 50      # Min labeled events to activate Phase B
ML_PHASE_C_THRESHOLD = 200     # Min labeled events to activate Phase C
ISOLATION_FOREST_CONTAMINATION = 0.1
ISOLATION_FOREST_N_ESTIMATORS = 100
ANOMALY_PERSISTENCE_COUNT = 5  # Consecutive anomalies before alert

# === Health Score ===
HEALTH_WEIGHTS = {
    "anomaly":       0.35,
    "vibration_rms": 0.25,
    "temperature":   0.20,
    "force":         0.20,
}
HEALTH_SMOOTHING_WINDOW = 10
HEALTH_VELOCITY_WINDOW = 5
RAPID_DEGRADATION_THRESHOLD = 15
DYNAMIC_ANOMALY_WEIGHT = 0.70

RISK_LEVELS = {
    "healthy": (80, 100),
    "warning": (60, 80),
    "critical": (40, 60),
    "high_risk": (0, 40),
}

# === Alert Thresholds ===
ALERT_HEALTH_THRESHOLD = 60
ALERT_COOLDOWN_SECONDS = 300

# === External Notifications (Layer 8) ===
NOTIFICATIONS_ENABLED = os.getenv("NOTIFICATIONS_ENABLED", "True").lower() == "true"
MQTT_BUZZER_TOPIC = "guardx/buzzer"

# Email Config (smtplib)
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
ALERT_EMAIL_RECIPIENT = os.getenv("ALERT_EMAIL_RECIPIENT", "admin@factory.local")

# Twilio (SMS / WhatsApp) Config
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")
ALERT_PHONE_RECIPIENT = os.getenv("ALERT_PHONE_RECIPIENT", "")

# === API ===
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
INGESTION_INTERVAL = 1  # seconds

# === Simulator ===
SIMULATOR_DEFAULT_ROWS = 5_000_000  # 5M rows (~650MB), scalable via --rows flag

# === Model Storage ===
MODEL_DIR = os.getenv("MODEL_DIR", "models")

# === Scheduler ===
PROCESSING_INTERVAL = 5    # seconds
INFERENCE_INTERVAL = 5     # seconds
HEALTH_INTERVAL = 5        # seconds
ALERT_CHECK_INTERVAL = 10  # seconds
RETRAIN_INTERVAL = 3600    # seconds (1 hour)

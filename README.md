<div align="center">

<img src="https://img.shields.io/badge/GuardX-AI%20Predictive%20Maintenance-blueviolet?style=for-the-badge&logo=robot&logoColor=white"/>

# 🛡️ GUARDX
### *AI-Driven Predictive Maintenance for Industrial CNC Machines*

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![XGBoost](https://img.shields.io/badge/XGBoost-2.0.3-FF6600?style=flat-square&logo=xgboost&logoColor=white)](https://xgboost.readthedocs.io)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-1.4.2-F7931E?style=flat-square&logo=scikitlearn&logoColor=white)](https://scikit-learn.org)
[![InfluxDB](https://img.shields.io/badge/InfluxDB-Time--Series-22ADF6?style=flat-square&logo=influxdb&logoColor=white)](https://www.influxdata.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

> **Catch machine failures before they happen.** GuardX continuously monitors industrial CNC machines in real-time using a self-evolving 3-Phase Hybrid ML Pipeline — from day-one anomaly detection to surgical fault classification — saving thousands of dollars in unplanned downtime.

</div>

---

## 📌 Table of Contents

- [🌟 What is GuardX?](#-what-is-guardx)
- [✨ Key Features](#-key-features)
- [🏗️ System Architecture — 8 Layers](#️-system-architecture--8-layers)
- [🔬 The 3-Phase ML Pipeline](#-the-3-phase-ml-pipeline)
- [📁 Project Structure](#-project-structure)
- [⚙️ Tech Stack](#️-tech-stack)
- [🚀 Getting Started](#-getting-started)
- [📡 Hardware Integration](#-hardware-integration)
- [👥 Who Is This For?](#-who-is-this-for)
- [🔮 Roadmap](#-roadmap)
- [🤝 Contributing](#-contributing)

---

## 🌟 What is GuardX?

GuardX is an **enterprise-grade, 8-layer AI-powered predictive maintenance platform** built for industrial CNC (Computer Numerical Control) machines. Traditional maintenance is reactive — you fix things after they break. GuardX is **proactive** — it detects microscopic anomalies in vibration, temperature, current, spindle speed, and cutting force **before** they cascade into catastrophic mechanical failures.

At its core, GuardX uses a **self-evolving Hybrid ML Pipeline** that starts unsupervised (no labeled data needed on day 1) and intelligently graduates to high-accuracy supervised fault classification as the system learns your machine. Every prediction comes with **Explainable AI (XAI via SHAP)**, telling engineers exactly *which* sensor signal triggered the alert — no black boxes.

---

## ✨ Key Features

| Feature | Description |
|---|---|
| 🤖 **3-Phase Hybrid ML** | Auto-transitions Isolation Forest → XGBoost as labeled data accumulates |
| 🧠 **Explainable AI (SHAP)** | Human-readable fault explanations per sensor feature |
| 📊 **Real-Time Health Score** | Live 0–100% machine health gauge with velocity-aware degradation tracking |
| ⏱️ **RUL Estimation** | Remaining Useful Life countdown with 5-layer noise-hardened prediction pipeline |
| 🔔 **Multi-Channel Alerting** | SMS + WhatsApp (Twilio), Email (SMTP), and **Physical Hardware Buzzer** via MQTT |
| 🎯 **CNC Diagnostics Engine** | 20+ years of domain knowledge encoded — maps sensor patterns to exact fault types |
| 🌐 **Live Web Dashboard** | Glassmorphism UI with real-time FFT charts, anomaly monitor, and ROI tracker |
| 💾 **Hybrid Storage** | InfluxDB (time-series sensor data) + SQLite (operational metadata) |
| 🔄 **Plug-and-Play Hardware** | Swap the Python simulator for real IoT hardware with **zero code changes** |
| 💰 **ROI Tracking** | Estimates USD saved based on $500/hr avoided CNC downtime costs |

---

## 🏗️ System Architecture — 8 Layers

GuardX is designed as **8 strictly decoupled layers** — a microservice-like architecture ensuring that if one layer fails, the others continue operating independently.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        GUARDX ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────────┤
│  Layer 1  │  Data Generation / Hardware Abstraction                 │
│           │  CNC Simulator → 5 sensor channels (Vibration, Temp,   │
│           │  Current, Spindle RPM, Cutting Force)                   │
├─────────────────────────────────────────────────────────────────────┤
│  Layer 2  │  Edge Gateway & Ingestion Engine                        │
│           │  FastAPI REST API + MQTT Listener + Pydantic validation │
├─────────────────────────────────────────────────────────────────────┤
│  Layer 3  │  Preprocessing & Feature Engineering Engine             │
│           │  FFT Spectrum, Spindle Harmonic, Force Gradients, RMS   │
├─────────────────────────────────────────────────────────────────────┤
│  Layer 4  │  Hybrid Storage (Time-Series + Relational)              │
│           │  InfluxDB (sensor streams) + SQLite (alerts, metadata)  │
├─────────────────────────────────────────────────────────────────────┤
│  Layer 5  │  Continuous ML Pipeline (Phase Shifter)                 │
│           │  Auto-transitions between 3 learning phases             │
├─────────────────────────────────────────────────────────────────────┤
│  Layer 6  │  ML Intelligence Engine & XAI                           │
│           │  Isolation Forest + XGBoost + SHAP + CNC Diagnostics   │
├─────────────────────────────────────────────────────────────────────┤
│  Layer 7  │  Health Score & Risk Engine                             │
│           │  Dynamic weighting, velocity tracking, RUL estimation   │
├─────────────────────────────────────────────────────────────────────┤
│  Layer 8  │  Alert & Visualization Layer                            │
│           │  Web Dashboard + SMS/WhatsApp + Email + Hardware Buzzer │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🔬 The 3-Phase ML Pipeline

GuardX's ML engine **self-evolves** based on the amount of labeled operational data available — no manual retraining required.

```
Day 1                    Day 14                   Day 60+
   │                        │                        │
   ▼                        ▼                        ▼
┌──────────┐           ┌──────────┐           ┌──────────┐
│ PHASE A  │           │ PHASE B  │           │ PHASE C  │
│          │  ──────►  │          │  ──────►  │          │
│ Isolation│           │  Hybrid  │           │ XGBoost  │
│  Forest  │           │  Model   │           │Supervised│
│(Anomaly) │           │          │           │(Full     │
│          │           │          │           │Classify) │
└──────────┘           └──────────┘           └──────────┘
  No labels              Few labels             Rich labels
  "What's weird?"    "Guessing fault type"  "Exact fault ID"
```

**Detected Fault Types:**
- 🔩 **Bearing Defect** — Inner/Outer race BPFO/BPFI frequency signatures
- ⚙️ **Spindle Imbalance** — Sinusoidal force bursts locked to RPM
- 🪛 **Tool Chatter** — High-frequency oscillation spikes in vibration
- 🌡️ **Thermal Overload** — Sustained temperature gradient beyond threshold
- ⚡ **Cutting Overload** — High current draw + temperature gradient correlation
- 💧 **Blocked Coolant** — Temperature spike with stable spindle metrics

---

## 📁 Project Structure

```
GUARDX/
│
├── 📄 README.md                        # You are here
├── 📄 requirements.txt                 # Python dependencies
├── 📄 config.py                        # Global configuration & env loading
├── 📄 Architecture_Workflow.md         # Deep-dive system architecture doc
│
├── 📂 api/                             # Layer 2: Edge Gateway
│   ├── main.py                         # FastAPI app entrypoint
│   ├── schemas.py                      # Pydantic data validation schemas
│   ├── mqtt_listener.py                # MQTT subscriber for IoT hardware
│   └── routers/                        # API route handlers
│
├── 📂 data_simulator/                  # Layer 1: CNC Machine Simulator
│   └── simulator.py                    # Hyper-realistic 5-channel sensor sim
│
├── 📂 services/                        # Core Business Logic
│   ├── preprocessing.py                # Layer 3: FFT + feature engineering
│   ├── health_engine.py                # Layer 7: Health score + RUL engine
│   ├── cnc_diagnostics.py              # Layer 6: Domain fingerprint engine
│   ├── notifier.py                     # Layer 8: SMS/Email/MQTT alerts
│   └── scheduler.py                    # APScheduler background jobs
│
├── 📂 ml/                              # Layer 5 & 6: ML Pipeline
│   ├── engine.py                       # Phase-shifting state machine
│   ├── isolation_forest.py             # Phase A: Unsupervised anomaly detection
│   ├── classifier.py                   # Phase C: XGBoost fault classifier
│   └── trainer.py                      # Model training entry point
│
├── 📂 models/                          # Serialized Trained Models
│   ├── isolation_forest.joblib         # Pre-trained Isolation Forest
│   ├── classifier.joblib               # Pre-trained XGBoost classifier
│   └── label_encoder.joblib            # Fault label encoder
│
├── 📂 database/                        # Layer 4: SQLite Storage
│   └── crud.py                         # CRUD operations
│
├── 📂 influx/                          # Layer 4: InfluxDB Time-Series
│   └── client.py                       # InfluxDB read/write client
│
├── 📂 dashboard/                       # Layer 8: Frontend UI
│   ├── index.html                      # Main glassmorphism dashboard
│   ├── css/                            # Stylesheets
│   └── js/                             # Real-time chart logic (Plotly.js)
│
└── 📂 data/                            # Local data storage
```

---

## ⚙️ Tech Stack

### Backend & AI
| Component | Technology |
|---|---|
| API Framework | FastAPI 0.115 + Uvicorn |
| Data Validation | Pydantic v2 |
| ML — Anomaly Detection | scikit-learn (Isolation Forest + GridSearchCV) |
| ML — Fault Classification | XGBoost 2.0 |
| Explainability | SHAP |
| Task Scheduling | APScheduler |
| IoT Messaging | paho-mqtt (MQTT protocol) |

### Data & Storage
| Component | Technology |
|---|---|
| Time-Series DB | InfluxDB (Flux query language) |
| Relational DB | SQLite3 |
| Feature Engineering | Scipy (FFT), NumPy, Pandas |

### Frontend & Alerting
| Component | Technology |
|---|---|
| Dashboard UI | HTML5 / CSS3 / Vanilla JS (Glassmorphism) |
| Charts | Plotly.js |
| SMS & WhatsApp Alerts | Twilio Python SDK |
| Email Alerts | Python smtplib |
| Hardware Buzzer | MQTT → Arduino/ESP8266 |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- InfluxDB instance (local or cloud)
- Twilio account (for SMS/WhatsApp alerts — optional)
- SMTP credentials (for email alerts — optional)

### 1. Clone the Repository

```bash
git clone https://github.com/hxxshx/GUARDX.git
cd GUARDX
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate        # macOS/Linux
# venv\Scripts\activate         # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the root directory:

```env
# InfluxDB Configuration
INFLUX_URL=http://localhost:8086
INFLUX_TOKEN=your_influxdb_token
INFLUX_ORG=your_org
INFLUX_BUCKET=guardx

# Twilio (Optional — for SMS/WhatsApp)
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_FROM_NUMBER=+1XXXXXXXXXX
ALERT_PHONE_NUMBER=+91XXXXXXXXXX

# Email (Optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
ALERT_EMAIL=recipient@example.com
```

### 5. Start the Backend Server

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Start the CNC Data Simulator

Open a second terminal:

```bash
python -m data_simulator.stream_to_api
```

### 7. Open the Dashboard

Open `dashboard/index.html` in your browser, or navigate to:

```
http://localhost:8000/dashboard
```

### 8. View API Docs

Interactive Swagger docs are available at:

```
http://localhost:8000/docs
```

---

## 📡 Hardware Integration

GuardX is **hardware-ready**. Transitioning from the simulator to real IoT sensors requires **zero changes** to Layers 2–8.

**Step 1:** Flash your ESP32 / Raspberry Pi with sensor-reading firmware.

**Step 2:** Format readings as this JSON payload:

```json
{
  "machine_id": "CNC-MACHINE-01",
  "vibration": 0.42,
  "temperature": 41.5,
  "current": 1.78,
  "spindle_speed": 8000.0,
  "cutting_force": 120.0
}
```

**Step 3:** POST to `http://<your-server-ip>:8000/api/v1/ingest`
— **or** — publish to MQTT topic `guardx/sensors`

**Done.** GuardX's pipeline automatically ingests, preprocesses, scores, and alerts — no changes needed.

---

## 👥 Who Is This For?

| Role | How They Use GuardX |
|---|---|
| 🔧 **Floor Operators** | Monitor the Health Gauge on a tablet. Hardware buzzer alerts them to stop the machine before damage occurs. |
| 🛠️ **Maintenance Engineers** | Use SHAP explanations to pinpoint the exact faulty component without blindly disassembling the machine. |
| 📊 **Plant Managers** | Track long-term ROI savings, fleet-wide health trends, and model performance over time. |
| 🔬 **Data Scientists** | Label faults to accelerate the ML pipeline from Phase A → Phase C, improving classification accuracy. |

---

## 🔮 Roadmap

- [ ] **Multi-Machine Fleet Management** — Monitor dozens of CNC machines from a single dashboard
- [ ] **ONNX Model Export** — Deploy ML models on-device for fully offline edge inference
- [ ] **Federated Learning** — Train across machines without sharing raw sensor data
- [ ] **Mobile App** — React Native companion app for on-the-go alerts and monitoring
- [ ] **Digital Twin Integration** — Simulate failure scenarios in a 3D virtual twin
- [ ] **REST API for ERP** — Direct integration with SAP/Oracle for automated maintenance scheduling

---

## 🤝 Contributing

Contributions are welcome! If you have ideas to improve GuardX — whether it's a new fault type fingerprint, a better visualization, or a new alert channel — feel free to open an issue or submit a pull request.

```bash
# Fork the repo, then:
git checkout -b feature/your-feature-name
git commit -m "feat: add your feature"
git push origin feature/your-feature-name
# Open a Pull Request
```

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Built with ❤️ to keep machines running and factories profitable.**

⭐ *If GuardX saved you from a costly breakdown, give it a star!* ⭐

</div>

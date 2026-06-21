# GuardX: AI-Driven Predictive Maintenance System
## Complete Workflow & Software Architecture Document

### 1. System Overview & Purpose
GuardX is a highly specialized, 8-layer enterprise predictive maintenance system designed for industrial CNC (Computer Numerical Control) machines. Rather than simply reacting to machine failures *after* they happen (which causes expensive downtime), GuardX continuously monitors the physical health of a machine in real-time. By applying cutting-edge hybrid Machine Learning (ML) techniques—specifically a 3-Phase transition from Unsupervised (Isolation Forests) to Supervised (XGBoost) learning—GuardX identifies microscopic anomalies in vibration, temperature, and current frequency before they cascade into catastrophic mechanical faults.

### 2. Who is this for? (Users & Stakeholders)
The system is built to serve multiple tiers of factory personnel:

#### A. Factory Floor Operators & Technicians
*   **How they use it:** They monitor the live HTML/JS Dashboard on a tablet or mounted screen next to the CNC machine. They look at the primary "0-100% Health Score Gauge."
*   **Why they use it:** If the gauge drops into the "Warning" (yellow) or "Critical" (red) zones, they know immediately that the machine needs inspection. They rely on the physical **Hardware Buzzer** or Twilio **SMS alerts** to tell them when to stop the machine to prevent damage.

#### B. Maintenance Engineers
*   **How they use it:** When an alert is triggered, they log into the dashboard's "Anomaly Monitor" and "ML Intelligence Screen." 
*   **Why they use it:** They need to know *what* is wrong. GuardX's Explainable AI (XAI) feature (powered by SHAP) provides a human-readable explanation like `"Vibration FFT Amplitude increased by +0.42"`, allowing the engineer to directly inspect the spindle bearings rather than tearing apart the entire machine blindly. They also use the dashboard to **label** faults (e.g., "Yes, this was Bearing Wear").

#### C. Data Scientists & Plant Managers
*   **How they use it:** They analyze long-term trends using the deep-dive analytics screens and monitor the continuous training pipeline.
*   **Why they use it:** They use the historical time-series data (stored in InfluxDB) to continuously improve the Machine Learning models. The system automatically shifts from Phase A (Unsupervised anomaly detection) to Phase C (Supervised fault classification) as the Data Scientists label more and more data correctly. They also track overall plant efficiency and downtime avoidance.

---

### 3. The 8-Layer End-to-End Workflow & Technology Stack

The software architecture is strictly divided into 8 decoupled layers. This microservice-like approach ensures that if the database crashes, the machine learning engine doesn't, and if the UI goes down, the backend alerting engine still fires SMS messages.

#### Layer 1: Data Generation / Hardware Abstraction
*   **What it does:** Generates high-frequency physical sensor data representing the machine's state (Vibration in `g`, Temperature in `°C`, Current in `A`).
*   **Current State:** We built a hyper-realistic Python **CNC Data Simulator** (`data_simulator/simulator.py`) that models fault-specific signatures across 5 channels: **Vibration (g)**, **Temperature (°C)**, **Current (A)**, plus CNC-specific **Spindle Speed (RPM)** and **Cutting Force (N)**. It simulates complex modes like "Spindle Imbalance" (sinusoidal force bursts) or "Tool Chatter" (high-frequency oscillation).
*   **Future Real Hardware State:** You will swap out the simulator for actual IoT edge nodes (like an ESP32 or Raspberry Pi connected to industrial accelerometers and thermocouples).
*   **Tech Stack:** Python, Numpy, Pandas (for mathematical noise/fault generation).

#### Layer 2: Edge Gateway & Ingestion Engine
*   **What it does:** Acts as the bouncer for incoming data. It validates that the sensor readings aren't corrupted (e.g., temperature reading of 5000°C) and handles the network traffic.
*   **How it works:** Real hardware (or our simulator) streams JSON data to this layer. It supports both HTTP REST APIs for batch ingestion and an MQTT Listener for extreme low-latency pub/sub streaming.
*   **Why it was built:** To normalize incoming data from potentially dozens of different machines into a single unified format.
*   **Tech Stack:** `FastAPI` (Python asynchronous framework), `Pydantic` (strict data validation schema), `paho-mqtt` (IoT messaging protocol).

#### Layer 3: Preprocessing & Feature Engineering Engine
*   **What it does:** Cleans the raw data and extracts the "hidden" signals that ML models need to spot faults.
*   **How it works:** It applies Rolling Windows to smooth out random sensor spikes (noise). Most importantly, it extracts **CNC-specific signals**:
    1.  **FFT Spectrum:** Extracts Peak Frequency and Amplitude from vibration to catch micro-scratches.
    2.  **Spindle Vibration Harmonic:** A gold-standard CNC metric (Vibration-to-RPM ratio) that locks vibration energy to the spindle rotation frequency.
    3.  **Force Gradients:** Detects rapid tool wear via the rate of change in cutting force.
*   **Tech Stack:** `Scipy`, `Numpy` (FFT Math).

#### Layer 4: Hybrid Storage (Time-Series & Relational)
*   **What it does:** Safely stores the millions of data points generated every day.
*   **How it works:** We implemented a hybrid dual-database architecture.
    1.  **InfluxDB:** A dedicated Time-Series Database (TSDB). All raw sensor streams and processed FFT features go here because it is mathematically optimized to read/write time-stamped data 100x faster than traditional SQL.
    2.  **SQLite:** A standard relational database. This stores operational metadata like "User Logins," "Active Alerts," and "Human-Labelled Fault Tags."
*   **Tech Stack:** `InfluxDB Client` (Flux query language), `SQLite3`.

#### Layer 5: Continuous ML Pipeline (The Phase Shifter)
*   **What it does:** Manages the lifecycle of the AI. Machines are unique; an AI trained on Machine A won't work on Machine B. GuardX solves this using a 3-Phase approach.
*   **The Workflow:**
    *   **Phase A (Unsupervised - Day 1):** The system has no idea what a "fault" looks like on this specific machine. It uses an Isolation Forest to just learn what "Normal" looks like. It flags anything deeply weird as an "Anomaly."
    *   **Phase B (Hybrid - Day 14):** Operators have labeled a few anomalies ("That weird spike was a blocked coolant pipe"). The system starts trying to guess the fault type using a weak Supervised classifier, but still relies on the Unsupervised model for primary alerts.
    *   **Phase C (Supervised - Day 60):** The dataset is rich with labeled faults. The system fully trusts an XGBoost Supervised Classifier to identify exactly *which* fault is happening with high confidence.
*   **Tech Stack:** Custom Python state-machine (`engine.py`).

#### Layer 6: Machine Learning Intelligence Engine & XAI
*   **What it does:** The actual brain crunching the numbers to predict failures.
*   **How it works:** 
    *   It uses `GridSearchCV` to automatically tune the Isolation Forest parameters (like tree depth) without human intervention. 
    *   **Explainable AI (XAI):** When XGBoost predicts a fault, we pass the decision tree through **SHAP**. SHAP calculates precisely which sensor feature forced the AI to make that prediction (e.g., "Driven 80% by a 0.2g increase in Spindle Harmonic").
    *   **CNC Domain Intelligence Engine:** Unlike generic AI, GuardX includes a rule-based **Diagnostic Fingerprint Layer** (`services/cnc_diagnostics.py`). This encodes 20+ years of CNC engineering knowledge to map patterns:
        *   *High vibration variance + stable RPM* → **Imbalance**
        *   *High current + temperature gradient* → **Cutting Overload**
        *   *Oscillatory vibration spike* → **Tool Chatter**
    *   **Bearing Frequency Calculator:** Dynamically calculates BPFO/BPFI (Ball Pass Frequency Outer/Inner race) signatures based on current spindle RPM for deterministic failure confirmation.
*   **Tech Stack:** `scikit-learn` (Isolation Forest, GridSearchCV), `xgboost`, `shap` (Explainability framework).

#### Layer 7: Health Score & Risk Engine (Dynamic Profiling)
*   **What it does:** Translates complex mathematical ML probabilities into a business-friendly "0-100% Health Score," and tracks the speed at which a machine is dying.
*   **How it works:** 
    *   **Dynamic Weighting:** If the ML Engine is highly confident (Phase C, >85% certainty) that a fault is imminent, this engine dynamically heavily weights the ML prediction (70% weight) over the raw physical sensors, trusting the AI over the naked eye.
    *   **Health Velocity Tracking:** It doesn't just look at the absolute score. It compares current health to a rolling past window. If health drops rapidly, it triggers a `velocity_warning` (Rapid Degradation Alert).
    *   **Hardened RUL Estimation (Predictive):** The engine projects **Remaining Useful Life (RUL)** in minutes using a stable, 5-layer pipeline:
        1.  *Degradation Smoothing:* Rolling average of the slope to ignore sensor spikes.
        2.  *Noise Floor:* Ignores fluctuations below 0.5% slope to prevent runaway values.
        3.  *Clamping:* Prevents RUL from jumping more than ±60 min between cycles, ensuring a smooth, believable countdown for operators.
*   **Tech Stack:** Python math logic (`health_engine.py`).

#### Layer 8: Alert & Visualization Layer (Enterprise Notifier)
*   **What it does:** Makes the insights actionable by getting the right data in front of the right human immediately.
*   **How it works:** 
    *   **Visuals:** A beautiful, responsive Web Dashboard served by FastAPI. Features real-time **CNC Diagnostics Cards**, **RUL Countdown**, and **Business ROI Tracking** (estimating $USD savings based on $500/hr CNC downtime costs).
    *   **External Notifier (`services/notifier.py`):** When Layer 7 generates a critical alert, this microservice blasts the alert to the outside world.
        *   **SMS & WhatsApp:** Pushed directly to operators' phones via the Twilio Cloud API.
        *   **Email:** Sent to plant managers via native `smtplib`.
        *   **Hardware Buzzer:** Pushes a `BEEP` command over MQTT to trigger a physical Arduino/ESP8266 siren on the factory floor (plus a localized Windows Motherboard beep for testing).
*   **Tech Stack:** `HTML5/CSS3/Vanilla JS` (Glassmorphism UI), `Plotly.js` (Charting), `Twilio Python SDK`, `smtplib`, `paho-mqtt`, `winsound`.

---

### 4. How to Transition from Simulator to Real Hardware

The architecture is explicitly designed so that swapping to real hardware requires **Zero changes to Layers 2 through 8**. 

1.  **Stop running** `python -m data_simulator.stream_to_api`.
2.  **Flash your Hardware (ESP32 / Raspberry Pi):** Write a simple C or MicroPython script on your edge device that reads your physical sensors (accelerometer, temperature probe, current clamp).
3.  **Format the Payload:** Have your hardware format the sensor readings into this exact JSON structure:
    ```json
    {
      "machine_id": "REAL-CNC-01",
      "vibration": 0.42,
      "temperature": 41.5,
      "current": 1.78,
      "spindle_speed": 8000.0,
      "cutting_force": 120.0
    }
    ```
4.  **Send the Payload:** Have your hardware POST that JSON to `http://<your-pc-ip>:8000/api/v1/ingest` or publish it to the MQTT broker on topic `guardx/sensors`.
5.  **Result:** GuardX's ingestion engine will process the real physical data exactly identically to the simulated data, passing it through the FFT preprocessor, storing it in InfluxDB, routing it to the ML models, evaluating the Health Velocity, and displaying it on the dashboard seamlessly.

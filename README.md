# ⚡ Autonomous IoT Decision and Alert Management Platform

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30%2B-FF4B4B.svg?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![MQTT](https://img.shields.io/badge/MQTT-EMQX%20%7C%20Mosquitto-660066.svg?logo=mqtt&logoColor=white)](https://mqtt.org/)
[![Node--RED](https://img.shields.io/badge/Node--RED-3.1%2B-8F0000.svg?logo=node-red&logoColor=white)](https://nodered.org/)
[![Grafana](https://img.shields.io/badge/Grafana-Enterprise-F46800.svg?logo=grafana&logoColor=white)](https://grafana.com/)
[![Machine Learning](https://img.shields.io/badge/Machine%20Learning-Isolation%20Forest-green.svg)](https://scikit-learn.org/)

An enterprise-ready, full-stack **Autonomous IoT Decision and Alert Management Platform**. Combines multi-sensor telemetry streaming over **MQTT**, visual flow automation via **Node-RED**, edge machine learning anomaly detection with **Scikit-Learn (Isolation Forest)**, real-time dashboard analytics with **Grafana**, and a responsive web application powered by **Streamlit** that can be accessed globally on any device or link.

---

## 🌟 Key Capabilities

1. **Self-Healing Autonomous Decision Engine**:
   - Analyzes real-time multivariate telemetry: **Temperature**, **Vibration (RMS)**, **Hydraulic Pressure**, **Motor Current**, and **Humidity**.
   - Dispatches automated mitigation commands to actuators (e.g. `ENGAGE_MAX_COOLING_CYCLE`, `OPEN_PRESSURE_RELEASE_VALVE_50%`, `DERATE_RPM_TO_40%`, `EMERGENCY_SAFE_SHUTDOWN`).
2. **Dynamic User Rule Management**:
   - Users can dynamically tune safety envelopes and warning/critical thresholds in real-time directly through the web UI without rebooting the pipeline.
3. **Tri-Mode Operational Authority**:
   - **🤖 Autonomous (Auto-Pilot)**: AI takes immediate, self-correcting protective actions.
   - **🧑‍✈️ Supervised (Human-in-the-Loop)**: AI proposes mitigation plans, waiting for operator 1-click approval.
   - **🛠️ Manual Override**: Full human control with on-demand actuator dispatch consoles.
4. **Machine Learning Anomaly Detection**:
   - Unsupervised **Isolation Forest** detects subtle multivariate drifts and equipment degradation patterns before rigid thresholds trip.
   - Real-time Health Index scoring ($0\% - 100\%$) and live contamination sensitivity recalibration.
5. **Node-RED Flow Pipeline**:
   - Production JSON flow definition included for event-driven orchestration, Slack/Webhook alerting, and distributed routing.
6. **Grafana Dashboards**:
   - Pre-configured Grafana telemetry panels and Docker Compose provisioning for enterprise visualization.
7. **Anywhere, Any-Device Access**:
   - Deployable in 2 minutes to **Streamlit Community Cloud** with a free, persistent public URL.

---

## 🏗️ System Architecture

```
                  +----------------------------------------------+
                  |            Industrial IoT Sensors            |
                  |  (Temperature, Vibration, Pressure, Current) |
                  +----------------------------------------------+
                                         |
                                         v [MQTT Pub/Sub: iot/telemetry/#]
                  +----------------------------------------------+
                  |         MQTT Broker (EMQX / Mosquitto)       |
                  +----------------------------------------------+
                         |                              |
                         v                              v
       +------------------------------------+   +------------------------------------+
       |       Node-RED Orchestration       |   |       Python ML & Decision Hub     |
       |  - Event-driven workflows          |   |  - Isolation Forest ML             |
       |  - Automated webhook alerts        |   |  - Dynamic Health Index (0-100%)   |
       |  - Actuator dispatch logic         |   |  - Tri-Mode Autonomous Controller  |
       +------------------------------------+   +------------------------------------+
                         |                              |
                         +---------------+--------------+
                                         |
                                         v
                  +----------------------------------------------+
                  |    Streamlit Cloud & Grafana Web Platform    |
                  |  - Accessible from any Phone, Tablet, Laptop |
                  |  - Real-time Plotly charts & Digital Twin    |
                  |  - Live Threshold Editor & Manual Overrides  |
                  +----------------------------------------------+
```

---

## 🚀 Quickstart: Local Setup

### 1. Clone & Install Dependencies
```bash
# Clone the repository
git clone https://github.com/<YOUR-USERNAME>/iot-autonomous-decision-platform.git
cd iot-autonomous-decision-platform

# Install Python requirements
pip install -r requirements.txt
```

### 2. Launch the Streamlit Web Platform
```bash
streamlit run app.py
```
Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## 🐳 Full Stack Docker Deployment

Spin up Mosquitto, Node-RED, Grafana, and Streamlit with a single command:

```bash
docker compose up -d --build
```

Access services:
- **Streamlit Platform**: [http://localhost:8501](http://localhost:8501)
- **Node-RED Flow Editor**: [http://localhost:1880](http://localhost:1880)
- **Grafana Dashboards**: [http://localhost:3000](http://localhost:3000) (Login: `admin` / `admin`)
- **Mosquitto MQTT Broker**: Port `1883` (TCP) / `9001` (WebSockets)

---

## 🌐 Deploy to Streamlit Community Cloud (Public Link for Anyone)

You can host this platform completely free so **anyone on any device** can access it via a public HTTPS link:

1. **Push your code to GitHub** (see instructions below).
2. Visit **[share.streamlit.io](https://share.streamlit.io/)** and log in with your GitHub account.
3. Click **"New App"**.
4. Configure:
   - **Repository**: `<YOUR-USERNAME>/iot-autonomous-decision-platform`
   - **Branch**: `main`
   - **Main file path**: `app.py`
5. Click **"Deploy!"**
6. Share your generated public URL (`https://<your-app-name>.streamlit.app`) with team members or clients!

---

## 📦 Pushing to Your GitHub Repository

```bash
git init
git add .
git commit -m "Initial commit: Autonomous IoT Decision Platform"
git branch -M main
git remote add origin https://github.com/<YOUR-USERNAME>/<YOUR-REPO-NAME>.git
git push -u origin main
```

---

## 📁 Repository Directory Structure

```
iot-autonomous-decision-platform/
├── app.py                      # Main Streamlit web application & interactive UI
├── simulator.py                # Industrial multi-sensor telemetry & fault simulator
├── mqtt_client.py              # Robust MQTT manager with automatic failover
├── requirements.txt            # Python dependencies (Streamlit Cloud ready)
├── Dockerfile                  # Container definition for Streamlit platform
├── docker-compose.yml          # Mosquitto + Node-RED + Grafana + Streamlit stack
├── .gitignore                  # Git ignore rules
├── .streamlit/
│   └── config.toml             # Custom high-contrast dark theme settings
├── ml/
│   ├── __init__.py
│   └── model.py                # Isolation Forest, Health Index & Decision Matrix
├── node_red/
│   ├── flows.json              # Importable Node-RED flow definition
│   └── README.md               # Node-RED setup instructions
├── grafana/
│   ├── dashboards/
│   │   └── iot_autonomous_dashboard.json  # Pre-built Grafana dashboard
│   └── provisioning/
│       ├── dashboards/dashboards.yaml
│       └── datasources/datasources.yaml
└── mosquitto/
    └── config/
        └── mosquitto.conf      # Mosquitto broker configuration
```

---

## 📄 License
This project is open-source under the [MIT License](LICENSE).

# SOFTWARE REQUIREMENTS SPECIFICATION (SRS)
## Mini Project Report
### Project Title: Autonomous IoT Decision and Alert Platform

| Student Name | Chinmay Prakash |
|:---|:---|
| **Roll Number** | **2400320310060** |
| **Branch / Department** | **Electronics and Communication Engineering (ECE)** |
| **College Name** | **ABES Engineering College** |
| **Project Guide** | **Ashish Kumar** |
| **Year / Batch** | **B.Tech 3rd Year, Batch 2024–28** |
| **Academic Year** | **2026–27** |

---

## 1. Abstract
The Autonomous IoT Decision and Alert Platform is an end-to-end industrial monitoring system that senses machine behaviour, detects abnormal conditions using machine learning, and takes protective action automatically without waiting for a human. Factory equipment such as a bottle filling machine, a CNC milling machine, a logistics conveyor and an air-quality unit can fail suddenly because of overheating, excess vibration or pressure loss, and manual monitoring is slow and error-prone. The platform simulates four such assets that stream multi-sensor telemetry over an MQTT broker. A Python decision engine combines an Isolation Forest model and a rolling Z-score detector with a rule engine to score risk and issue corrective commands, such as an emergency fault stop with maximum cooling. All telemetry, anomaly scores, decisions and alerts are stored in MongoDB. A web cockpit with live charts, device health cards, an audit log and a fault-injection test lab, together with REST APIs, lets operators observe, acknowledge and resolve incidents. The expected outcome is a working closed-loop system that detects faults within about two seconds and shows every automatic decision with a clear explanation.

---

## 2. Problem Statement
Industrial machines generate large volumes of sensor data, but most plants still depend on operators who watch dashboards or react after a breakdown. A temperature surge or a vibration spike can damage equipment, stop a production line or put people at risk within seconds, which is faster than a human can reliably respond. Fixed-threshold alarms alone also miss unusual combinations of readings that are individually within limits.

The proposed system provides a digital solution that continuously collects data from machines, evaluates it with machine learning and rule-based logic, performs an immediate protective action through actuator commands, and keeps a permanent record of every reading, decision and incident for later analysis.

---

## 3. Objectives
* Collect multi-sensor telemetry from four industrial assets over MQTT in real time.
* Detect anomalies automatically using an Isolation Forest model and rolling Z-scores.
* Automate protective responses (fault stop, safety trip, halt, purge) through closed-loop actuator control.
* Store telemetry, anomaly evaluations, decisions and alerts efficiently in MongoDB.
* Provide a web cockpit and REST API for monitoring, alert handling and fault testing.
* Make every automatic decision explainable through risk scores, sensor contributions and text explanations.

---

## 4. Proposed Solution
* **How the system works**: A simulator publishes telemetry for each asset to an MQTT broker. The decision engine subscribes to these messages, stores each reading in MongoDB and evaluates it. The Isolation Forest, trained on normal baseline data, produces a risk score between $0.0$ and $1.0$, and the rolling Z-score shows which sensor deviates most. If a configured safety limit is crossed, the rule engine publishes a command back to the asset. The simulator applies the command to its actuators (for example cooling to MAXIMUM and conveyor speed to 0), so the readings return to a safe range. The cockpit reads the stored data through the REST API and refreshes the display.
* **Main features**: Live telemetry streaming; ML-based anomaly detection; autonomous protective actions; alert lifecycle (`ACTIVE`, `ACKNOWLEDGED`, `RESOLVED`); decision audit log with explanations; machine health score ($0–100\%$); fault-injection lab (`SPIKE`, `DRIFT`, `OVERLOAD`, `DROP`); manual `START`, `STOP` and `THROTTLE` commands; MongoDB status check.
* **Users of the system**: Plant operators and maintenance engineers use the cockpit. The autonomous decision engine and the edge asset simulator act as system actors that interact through MQTT.
* **Basic workflow**: Sense (telemetry) → Communicate (MQTT) → Evaluate (ML and rules) → Act (actuator command) → Remember (MongoDB) → Display (cockpit and alerts).
* **Expected benefits**: Faster response to faults, fewer breakdowns, less manual monitoring, a full audit trail and transparent, explainable decisions.

---

## 5. Scope of the Project

### 5.1 In Scope (Implemented)
* Four simulated assets: `MCH-007` Bottle Filling Machine, `CNC-003` Precision Milling, `CONV-012` Logistics Conveyor and `ENV-001` Air Quality and Safety unit.
* Telemetry such as temperature, vibration, pressure, energy, fill rate, coolant flow, belt tension, gas and smoke levels, and humidity.
* MQTT messaging on port 1883, including command and acknowledgement topics.
* ML anomaly detection, rule-based autonomous actions, alert management and MongoDB storage in five collections.
* Web cockpit on port 5000 / 8501 and REST API endpoints.

### 5.2 Out of Scope
* Connection to real physical machines or hardware sensors (data is simulated).
* User login and role-based access control.
* Mobile application, cloud deployment and external notification channels (SMS, email).

---

## 6. Functional Requirements

| ID | Functional Requirement |
|:---|:---|
| **FR-01** | The system shall stream multi-sensor telemetry for four assets to the MQTT broker. |
| **FR-02** | The system shall receive telemetry and store every data point in MongoDB with device ID and timestamp. |
| **FR-03** | The system shall detect anomalies using an Isolation Forest model and rolling Z-scores and store the risk score (0.0–1.0) and sensor contributions. |
| **FR-04** | The system shall automatically trigger protective actions when safety limits are exceeded (`EMERGENCY_FAULT_STOP`, `SPINDLE_SAFETY_TRIP`, `EMERGENCY_CONVEYOR_HALT`, `HAZMAT_EVACUATION_PURGE`). |
| **FR-05** | The system shall send actuator commands over MQTT and the assets shall respond with feedback (acknowledgement). |
| **FR-06** | The system shall create alerts and let the user mark them `ACKNOWLEDGED` or `RESOLVED`. |
| **FR-07** | The cockpit shall show a real-time telemetry chart, machine status and health score for each asset. |
| **FR-08** | The cockpit shall show a decision audit log with action, severity and explanation. |
| **FR-09** | The user shall be able to inject test faults (`SPIKE`, `DRIFT`, `OVERLOAD`, `DROP`) on a sensor. |
| **FR-10** | The system shall provide REST APIs for overview, MongoDB status, latest device telemetry and device commands (`START`, `STOP`, `THROTTLE`). |

---

## 7. Non-Functional Requirements
* **Performance**: A fault should be visible on the chart and acted upon within about 2 seconds of occurring.
* **Security**: The current version has no login; it is intended to run on a local machine (localhost). Authentication is listed as future work.
* **Usability**: The dark-mode cockpit shows charts, status cards and one-click test buttons so that operators need no technical setup after launch.
* **Reliability**: All readings, decisions and alerts are persisted in MongoDB, and indexing on `(device_id, timestamp)` keeps queries fast.
* **Compatibility**: The cockpit runs in a standard web browser; the platform starts on Windows through a single launcher (`start_platform.bat`).

---

## 8. Technology Stack

| Component | Technology |
|:---|:---|
| **Frontend** | HTML, CSS, JavaScript, Chart.js / Streamlit / Plotly (web cockpit) |
| **Backend** | Python (REST API server on port 5000 / 8501) |
| **Messaging** | MQTT broker (`127.0.0.1:1883`) |
| **Machine Learning** | Scikit-Learn (**Isolation Forest**), rolling Z-score |
| **Database** | MongoDB (database: `aiot_platform`, port 27017) |
| **Programming Language** | Python, JavaScript |
| **IDE** | VS Code / Antigravity IDE |
| **Version Control** | Git / GitHub |

---

## 9. Autonomous Protective Actions Matrix

| Asset | Trigger Condition | Autonomous Action |
|:---|:---|:---|
| **`MCH-007`** (Bottle Filling Machine) | Temperature $\ge 88^\circ\text{C}$ or vibration $\ge 4.0\text{ mm/s}$; pressure $\le 4.0\text{ bar}$ | **`EMERGENCY_FAULT_STOP`**: fill valve closed, conveyor to 0, cooling to MAXIMUM; low-pressure trip |
| **`CNC-003`** (Precision Milling) | Spindle temp $> 85^\circ\text{C}$ or vibration $> 5.5\text{ mm/s}$ | **`SPINDLE_SAFETY_TRIP`**: flood coolant engaged, spindle brake active |
| **`CONV-012`** (Logistics Conveyor) | Motor temp $> 80^\circ\text{C}$ or belt tension $> 620\text{ N}$ | **`EMERGENCY_CONVEYOR_HALT`**: conveyor motor halted, diverter bypass |
| **`ENV-001`** (Air Quality & Safety) | Gas $> 250\text{ ppm}$ or smoke $> 80\text{ ppm}$ | **`HAZMAT_EVACUATION_PURGE`**: exhaust fan flush 100%, evacuation siren active |

---

## 10. Database Design (`aiot_platform` in MongoDB)

| Collection | Important Fields | Purpose |
|:---|:---|:---|
| **`telemetry`** | `device_id`, `timestamp`, `state`, `readings`, `units` | Every streamed data point; indexed by `(device_id, timestamp)` |
| **`anomalies`** | `risk_score`, `is_anomaly`, `anomaly_type`, `feature_contributors` | Audit trail of ML evaluations |
| **`decisions`** | `decision_id`, `action_taken`, `actuator_updates`, `explanation`, `severity`, `timestamp` | Log of autonomous interventions |
| **`alerts`** | `alert_id`, `severity`, `message`, `status`, `timestamps` | Incident lifecycle tracking |
| **`device_states`** | `latest_state`, `health_score` (0–100%), `actuator_configuration` | Live status cards on the cockpit |

---

## 11. Testing

| Test ID | Test Case | Expected Result | Status |
|:---:|:---|:---|:---:|
| **TC01** | Launch platform (`start_platform.bat`) | MQTT, MongoDB, ML engine, simulator and web server start; cockpit opens at `localhost:5000` / `localhost:8501` | **Pass** |
| **TC02** | Telemetry storage | Live readings are stored in the telemetry collection and appear on the chart | **Pass** |
| **TC03** | MongoDB status check (`GET /api/mongodb/status`) | Connection state, database name and collection counts are returned | **Pass** |
| **TC04** | Inject Capping Thermal Surge on `MCH-007` | Temperature rises above $88^\circ\text{C}$ within about 2 seconds, health score drops, status shows FAULT | **Pass** |
| **TC05** | Autonomous decision after fault | `EMERGENCY_FAULT_STOP` with explanation appears in audit log; cooling MAXIMUM, conveyor 0% | **Pass** |
| **TC06** | Acknowledge and resolve alert | Alert status changes to `ACKNOWLEDGED` and then `RESOLVED` in MongoDB | **Pass** |
| **TC07** | Latest telemetry API (`GET /api/devices/MCH-007/latest`) | Most recent `MCH-007` telemetry document is returned | **Pass** |
| **TC08** | Send manual command (`POST .../command`) | `START`, `STOP` or `THROTTLE` is sent over MQTT and recorded in the database | **Pass** |

---

## 12. References
1. HCL Career Shaper AIoT Curriculum (Lectures 4–7) and the project guide, *Autonomous IoT Platform – User & Architecture Guide*.
2. Scikit-learn documentation, IsolationForest: [https://scikit-learn.org](https://scikit-learn.org)
3. MongoDB official documentation: [https://www.mongodb.com/docs](https://www.mongodb.com/docs)
4. MQTT specification and broker documentation: [https://mqtt.org](https://mqtt.org)
5. Chart.js documentation: [https://www.chartjs.org/docs](https://www.chartjs.org/docs)
6. Liu, F. T., Ting, K. M., Zhou, Z.-H., “Isolation Forest,” IEEE ICDM, 2008.

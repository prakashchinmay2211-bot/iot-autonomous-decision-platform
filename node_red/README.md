# Node-RED Autonomous IoT Pipeline

This directory contains the production Node-RED workflow for the **Autonomous IoT Decision and Alert Management Platform**.

## Flow Architecture
- **MQTT In Node**: Listens to topic `iot/telemetry/#` from EMQX or Mosquitto.
- **Decision Engine (Function Node)**: Evaluates temperature, vibration, and pressure against dynamic safe operating envelopes.
- **Actuator Dispatch (MQTT Out)**: Automatically sends control payloads to:
  - `iot/actuators/cooling` (Emergency cooling cycle / aux fans)
  - `iot/actuators/valves` (Pressure relief valve control)
  - `iot/actuators/motors` (RPM derating to protect bearings)
- **Alert Dispatch & Webhooks**:
  - `iot/alerts/critical` and `iot/alerts/warning`
  - Automated HTTP POST Webhook (connects to Slack, Discord, PagerDuty, or SMS gateway).

## Quick Import Guide
1. Launch Node-RED (locally `node-red` or via `docker compose up -d`).
2. Open your browser at `http://localhost:1880`.
3. In top right menu, select **Import** -> **Select a file to import**.
4. Choose `flows.json` from this folder.
5. Click **Import** and then **Deploy**.

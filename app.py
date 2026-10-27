import time
import json
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

from ml.model import (
    DEVICE_SPECS,
    AssetReading,
    IsolationForestAnomalyDetector,
    AutonomousDecisionEngine
)
from simulator import MultiAssetSimulator
from database import MongoStorageManager
from mqtt_client import MQTTManager

# Page Configuration
st.set_page_config(
    page_title="Autonomous IoT Decision and Alert Platform - ABESEC",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom High-Tech Industrial Dark Styling
st.markdown("""
<style>
    .report-badge {
        background: linear-gradient(135deg, #1A1C24, #2A2D3A);
        border: 1px solid #3A3F50;
        border-radius: 8px;
        padding: 10px 16px;
        margin-bottom: 12px;
    }
    .metric-card {
        background-color: #1A1C24;
        border: 1px solid #2D3139;
        border-radius: 8px;
        padding: 12px;
    }
    .status-badge-running {
        background-color: rgba(0, 255, 163, 0.15);
        color: #00FFA3;
        border: 1px solid #00FFA3;
        padding: 3px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.85em;
    }
    .status-badge-fault {
        background-color: rgba(255, 75, 75, 0.2);
        color: #FF4B4B;
        border: 1px solid #FF4B4B;
        padding: 3px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.85em;
        animation: pulse 1.5s infinite;
    }
    @keyframes pulse {
        0% { opacity: 0.6; }
        50% { opacity: 1.0; }
        100% { opacity: 0.6; }
    }
    .decision-card {
        background: #131722;
        border-left: 4px solid #FF4B4B;
        padding: 12px 16px;
        margin-bottom: 10px;
        border-radius: 0 8px 8px 0;
    }
</style>
""", unsafe_allow_html=True)


# Initialize Session State
if "engine" not in st.session_state:
    st.session_state.engine = AutonomousDecisionEngine()

if "simulator" not in st.session_state:
    st.session_state.simulator = MultiAssetSimulator()

if "db" not in st.session_state:
    st.session_state.db = MongoStorageManager()

if "mqtt" not in st.session_state:
    mgr = MQTTManager(broker="broker.emqx.io", port=1883)
    mgr.connect(timeout=1.5)
    st.session_state.mqtt = mgr

if "telemetry_buffer" not in st.session_state:
    st.session_state.telemetry_buffer = {dev_id: [] for dev_id in DEVICE_SPECS}

if "auto_stream" not in st.session_state:
    st.session_state.auto_stream = True

if "selected_device" not in st.session_state:
    st.session_state.selected_device = "MCH-007"


# Student & Project Academic Header
with st.container():
    col_hdr1, col_hdr2 = st.columns([2.5, 1.2])
    with col_hdr1:
        st.title("⚡ Autonomous IoT Decision and Alert Platform")
        st.markdown("**Closed-Loop Industrial AIoT System with ML Anomaly Detection & Actuator Protection**")
    with col_hdr2:
        st.markdown("""
        <div class="report-badge">
            <small style="color: #00FFA3;"><b>MINI PROJECT REPORT | ECE DEPT</b></small><br/>
            <b>Student:</b> Chinmay Prakash (Roll: <code>2400320310060</code>)<br/>
            <b>College:</b> ABES Engineering College | <b>Guide:</b> Ashish Kumar<br/>
            <small style="color: #A0AEC0;">B.Tech 3rd Year (Batch 2024–28) • Academic Year 2026–27</small>
        </div>
        """, unsafe_allow_html=True)

# Generate Cycle
latest_evals = {}
for d_id in DEVICE_SPECS:
    reading = st.session_state.simulator.generate_reading(d_id)
    eval_res = st.session_state.engine.process_telemetry(reading)
    latest_evals[d_id] = eval_res
    
    # Store in MongoDB Collections
    st.session_state.db.insert("telemetry", reading.to_dict())
    st.session_state.db.insert("anomalies", {
        "device_id": d_id,
        "timestamp": reading.timestamp,
        **eval_res["ml_evaluation"]
    })
    if eval_res["decision"]:
        st.session_state.db.insert("decisions", eval_res["decision"])
        # Apply feedback to simulator closed loop!
        st.session_state.simulator.apply_actuator_feedback(d_id, eval_res["decision"]["actuator_updates"])
    if eval_res["alert"]:
        st.session_state.db.insert("alerts", eval_res["alert"])

    # Update device states collection
    st.session_state.db.insert("device_states", {
        "device_id": d_id,
        "state": reading.state,
        "health_score": eval_res["health_score"],
        "actuators": eval_res["actuators"],
        "timestamp": reading.timestamp
    })

    # Buffer for live charts
    row = {"timestamp": datetime.fromtimestamp(reading.timestamp).strftime("%H:%M:%S"), **reading.readings}
    st.session_state.telemetry_buffer[d_id].append(row)
    if len(st.session_state.telemetry_buffer[d_id]) > 30:
        st.session_state.telemetry_buffer[d_id].pop(0)

    # Publish to MQTT topics
    st.session_state.mqtt.publish(f"iot/telemetry/{d_id}", reading.to_dict())


# Sidebar Controls
st.sidebar.title("🎛️ Asset & Test Lab")

selected_dev = st.sidebar.selectbox(
    "Select Industrial Asset:",
    list(DEVICE_SPECS.keys()),
    format_func=lambda x: f"{x} - {DEVICE_SPECS[x]['name']}"
)
st.session_state.selected_device = selected_dev

st.sidebar.markdown("---")
st.sidebar.subheader("🧪 Fault-Injection Test Lab")
st.sidebar.caption("Simulate critical industrial anomalies (SRS Section 6 & 11):")

fault_type = st.sidebar.selectbox(
    "Fault Profile:",
    ["NONE", "SPIKE", "DRIFT", "OVERLOAD", "DROP"],
    help="SPIKE: Critical jump; DRIFT: Creeping rise; OVERLOAD: Extreme power & temp surge; DROP: Sudden pressure/coolant loss."
)

col_f1, col_f2 = st.sidebar.columns(2)
with col_f1:
    if st.button("💥 Inject Fault", use_container_width=True):
        st.session_state.simulator.inject_fault(selected_dev, fault_type)
        st.toast(f"Injected {fault_type} on {selected_dev}")
with col_f2:
    if st.button("🔄 Clear / Reset", use_container_width=True):
        st.session_state.simulator.reset_machine(selected_dev)
        st.toast(f"Reset {selected_dev} to Normal")

st.sidebar.markdown("---")
st.sidebar.subheader("📡 Streaming Controls")
auto_stream = st.sidebar.toggle("Auto-Stream Telemetry (2s)", value=st.session_state.auto_stream)
st.session_state.auto_stream = auto_stream

if st.sidebar.button("⚡ Single Step Pulse", use_container_width=True):
    st.rerun()

# 4 Asset Health Status Cards (Top Overview)
st.markdown("### 🏭 Asset Fleet Health Overview")
card_cols = st.columns(4)

for idx, (dev_id, spec) in enumerate(DEVICE_SPECS.items()):
    ev = latest_evals.get(dev_id, {})
    health = ev.get("health_score", 100.0)
    sev = ev.get("severity", "NORMAL")
    state = st.session_state.simulator.device_states.get(dev_id, "RUNNING")
    badge_cls = "status-badge-running" if state == "RUNNING" else "status-badge-fault"

    with card_cols[idx]:
        st.markdown(f"""
        <div class="metric-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <b>{dev_id}</b>
                <span class="{badge_cls}">{state}</span>
            </div>
            <small style="color: #A0AEC0;">{spec['name']}</small>
            <div style="font-size: 1.8em; font-weight: bold; color: {'#00FFA3' if health >= 70 else ('#FFAA00' if health >= 40 else '#FF4B4B')}; margin: 8px 0;">
                {health}%
            </div>
            <small>Active Severity: <b>{sev}</b></small>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# Main Navigation Tabs
main_tabs = st.tabs([
    "📊 Live Cockpit & Telemetry",
    "🧠 Autonomous Decision Audit Log",
    "🚨 Alert Lifecycle Manager",
    "🔬 Machine Learning & Z-Score Analysis",
    "🗄️ MongoDB Database (aiot_platform)",
    "⚙️ Manual Actuator Command Console",
    "📄 Project Report & SRS Specifications"
])


# TAB 1: Live Cockpit & Telemetry
with main_tabs[0]:
    cur_spec = DEVICE_SPECS[selected_dev]
    cur_eval = latest_evals[selected_dev]
    cur_readings = cur_eval["readings"]
    units = cur_spec["units"]

    st.subheader(f"{selected_dev} - {cur_spec['name']} Telemetry Cockpit")

    # Sensor Metric Cards
    sensor_cols = st.columns(len(cur_spec["primary_sensors"]))
    for i, s_name in enumerate(cur_spec["primary_sensors"]):
        val = cur_readings.get(s_name, 0.0)
        unit = units.get(s_name, "")
        with sensor_cols[i]:
            st.metric(label=s_name.replace("_", " ").title(), value=f"{val} {unit}")

    # Live Real-Time Charts
    buf = st.session_state.telemetry_buffer[selected_dev]
    if len(buf) > 1:
        df_plot = pd.DataFrame(buf)
        c_left, c_right = st.columns(2)

        with c_left:
            primary_sensor = cur_spec["primary_sensors"][0]
            fig1 = px.line(
                df_plot, x="timestamp", y=primary_sensor,
                title=f"{primary_sensor.replace('_', ' ').title()} ({units.get(primary_sensor, '')})",
                color_discrete_sequence=["#FF7675"]
            )
            # Add threshold line if exists
            crit_lim = cur_spec["limits"].get("temp_critical") or cur_spec["limits"].get("gas_critical")
            if crit_lim:
                fig1.add_hline(y=crit_lim, line_dash="dash", line_color="#FF4B4B", annotation_text=f"Critical Limit ({crit_lim})")
            fig1.update_layout(template="plotly_dark", height=280, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig1, use_container_width=True)

        with c_right:
            secondary_sensor = cur_spec["primary_sensors"][1]
            fig2 = px.line(
                df_plot, x="timestamp", y=secondary_sensor,
                title=f"{secondary_sensor.replace('_', ' ').title()} ({units.get(secondary_sensor, '')})",
                color_discrete_sequence=["#74B9FF"]
            )
            crit_lim2 = cur_spec["limits"].get("vib_critical") or cur_spec["limits"].get("tension_critical") or cur_spec["limits"].get("smoke_critical")
            if crit_lim2:
                fig2.add_hline(y=crit_lim2, line_dash="dash", line_color="#FF4B4B", annotation_text=f"Limit ({crit_lim2})")
            fig2.update_layout(template="plotly_dark", height=280, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Gathering live telemetry data packets...")


# TAB 2: Decision Audit Log
with main_tabs[1]:
    st.subheader("📜 Explainable Autonomous Decision Audit Log")
    st.caption("Closed-loop automatic interventions executed to protect machinery without human delay.")

    decisions = list(st.session_state.engine.decision_history)
    if decisions:
        for dec in decisions[-8:][::-1]:
            st.markdown(f"""
            <div class="decision-card">
                <div style="display:flex; justify-content:space-between;">
                    <b>⚡ {dec['action_taken']}</b> on <code>{dec['device_id']}</code>
                    <small>{time.strftime('%H:%M:%S', time.localtime(dec['timestamp']))}</small>
                </div>
                <p style="margin: 6px 0; color: #E2E8F0;"><b>Explanation:</b> {dec['explanation']}</p>
                <small style="color: #00FFA3;"><b>Actuator Updates:</b> {json.dumps(dec['actuator_updates'])}</small>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.success("All systems nominal. No autonomous protective trips triggered.")


# TAB 3: Alert Lifecycle Manager
with main_tabs[2]:
    st.subheader("🚨 Incident & Alert Lifecycle Management (ACTIVE → ACKNOWLEDGED → RESOLVED)")
    
    active_alerts = st.session_state.engine.active_alerts
    if active_alerts:
        for a_id, alt in list(active_alerts.items()):
            col_a1, col_a2, col_a3 = st.columns([3, 1, 1])
            with col_a1:
                st.error(f"🔴 **[{alt['status']}] {alt['device_id']}**: {alt['message']}")
                st.caption(f"Alert ID: `{alt['alert_id']}` | Timestamp: {alt['timestamp']}")
            with col_a2:
                if alt["status"] == "ACTIVE":
                    if st.button("Acknowledge", key=f"ack_{a_id}"):
                        st.session_state.engine.update_alert_status(a_id, "ACKNOWLEDGED")
                        st.rerun()
            with col_a3:
                if st.button("Resolve Incident", key=f"res_{a_id}"):
                    st.session_state.engine.update_alert_status(a_id, "RESOLVED")
                    st.session_state.simulator.reset_machine(alt["device_id"])
                    st.rerun()
    else:
        st.success("Zero unresolved incidents. Incident queue is empty.")

    st.markdown("---")
    st.markdown("#### Historical Alert Log")
    all_alerts = list(st.session_state.engine.alert_history)
    if all_alerts:
        st.dataframe(pd.DataFrame(all_alerts).tail(15), use_container_width=True)


# TAB 4: ML & Rolling Z-Score
with main_tabs[3]:
    st.subheader("🔬 Machine Learning Anomaly Detection (Isolation Forest & Rolling Z-Score)")
    cur_ml = cur_eval["ml_evaluation"]
    
    col_m1, col_m2 = st.columns([1, 1.5])
    with col_m1:
        st.metric(label="Calculated ML Risk Score", value=f"{cur_ml['risk_score']:.3f} / 1.000")
        st.write(f"**Anomaly Classification:** `{'ANOMALY' if cur_ml['is_anomaly'] else 'NORMAL'}`")
        st.write(f"**Top Deviating Contributor:** `{cur_ml.get('top_contributor') or 'None'}`")

    with col_m2:
        st.markdown("##### Rolling Z-Scores (Sensor Deviations from Baseline)")
        contribs = cur_ml.get("feature_contributors", {})
        if contribs:
            z_df = pd.DataFrame({"Sensor": list(contribs.keys()), "Z-Score": list(contribs.values())})
            fig_z = px.bar(z_df, x="Sensor", y="Z-Score", color="Z-Score", color_continuous_scale="RdYlGn_r", title="Sensor Z-Score Contributions")
            fig_z.update_layout(template="plotly_dark", height=260, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig_z, use_container_width=True)
        else:
            st.caption("Collecting rolling buffer to compute Z-scores...")


# TAB 5: MongoDB Status
with main_tabs[4]:
    st.subheader("🗄️ MongoDB Database Inspection (`aiot_platform`)")
    db_status = st.session_state.db.get_status()
    
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        st.write(f"**Database Name:** `{db_status['database']}`")
        st.write(f"**Storage Engine Status:** `{db_status['status']}`")
        st.write(f"**Connected to Local MongoDB (Port 27017):** `{db_status['connected_to_mongodb_daemon']}`")
    with col_d2:
        st.markdown("##### Five Collection Document Counts:")
        for col_name, cnt in db_status["collection_counts"].items():
            st.write(f"- Collection `{col_name}`: **{cnt}** documents")

    st.markdown("---")
    st.markdown("##### Recent Documents from `telemetry` Collection")
    recent_docs = st.session_state.db.get_latest("telemetry", limit=5)
    st.json(recent_docs)


# TAB 6: Manual Command Console
with main_tabs[5]:
    st.subheader(f"⚙️ Operator Control Console: {selected_dev}")
    st.caption("Send manual START, STOP, or THROTTLE commands over MQTT.")

    c_b1, c_b2, c_b3, c_b4 = st.columns(4)
    with c_b1:
        if st.button("🟢 START Machine", use_container_width=True):
            st.session_state.simulator.device_states[selected_dev] = "RUNNING"
            st.session_state.mqtt.publish(f"iot/commands/{selected_dev}", {"command": "START", "user": "Chinmay Prakash"})
            st.toast(f"Sent START command to {selected_dev}")
    with c_b2:
        if st.button("🔴 STOP Machine", use_container_width=True):
            st.session_state.simulator.device_states[selected_dev] = "STOPPED"
            st.session_state.mqtt.publish(f"iot/commands/{selected_dev}", {"command": "STOP", "user": "Chinmay Prakash"})
            st.toast(f"Sent STOP command to {selected_dev}")
    with c_b3:
        if st.button("🟡 THROTTLE (50%)", use_container_width=True):
            st.session_state.mqtt.publish(f"iot/commands/{selected_dev}", {"command": "THROTTLE_50%", "user": "Chinmay Prakash"})
            st.toast(f"Sent THROTTLE command to {selected_dev}")
    with c_b4:
        if st.button("🔄 Emergency Reset", use_container_width=True):
            st.session_state.simulator.reset_machine(selected_dev)
            st.toast(f"Reset {selected_dev}")


# TAB 7: SRS Document
with main_tabs[6]:
    st.subheader("📄 Mini Project Report & SRS Specifications")
    st.markdown("""
    | Field | Detail |
    |---|---|
    | **Project Title** | Autonomous IoT Decision and Alert Platform |
    | **Student Name** | Chinmay Prakash |
    | **Roll Number** | 2400320310060 |
    | **Department** | Electronics and Communication Engineering (ECE) |
    | **College** | ABES Engineering College |
    | **Project Guide** | Ashish Kumar |
    | **Year / Batch** | B.Tech 3rd Year, Batch 2024–28 |
    | **Academic Year** | 2026–27 |

    #### Autonomous Protective Actions
    - **`MCH-007` (Bottle Filling Machine)**: Temp ≥ 88°C, Vibration ≥ 4.0 mm/s, Pressure ≤ 4.0 bar &rarr; `EMERGENCY_FAULT_STOP`
    - **`CNC-003` (Precision Milling)**: Spindle Temp > 85°C, Vibration > 5.5 mm/s &rarr; `SPINDLE_SAFETY_TRIP`
    - **`CONV-012` (Logistics Conveyor)**: Motor Temp > 80°C, Belt Tension > 620 N &rarr; `EMERGENCY_CONVEYOR_HALT`
    - **`ENV-001` (Air Quality & Safety Unit)**: Gas > 250 ppm, Smoke > 80 ppm &rarr; `HAZMAT_EVACUATION_PURGE`
    """)

# Streaming Loop
if st.session_state.auto_stream:
    time.sleep(2.0)
    st.rerun()

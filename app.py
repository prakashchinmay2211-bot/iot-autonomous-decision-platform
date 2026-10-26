import time
import json
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

from ml.model import IoTDecisionEngine, SensorReading
from simulator import IoTSensorSimulator
from mqtt_client import MQTTManager

# Page Configuration
st.set_page_config(
    page_title="Autonomous IoT Decision & Alert Platform",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for Dark Industrial Cyberpunk / High-Tech Telemetry Look
st.markdown("""
<style>
    .metric-card {
        background-color: #1A1C24;
        border: 1px solid #2D3139;
        border-radius: 10px;
        padding: 16px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    .status-badge-nominal {
        background-color: rgba(0, 255, 163, 0.15);
        color: #00FFA3;
        border: 1px solid #00FFA3;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        display: inline-block;
    }
    .status-badge-warning {
        background-color: rgba(255, 170, 0, 0.15);
        color: #FFAA00;
        border: 1px solid #FFAA00;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        display: inline-block;
    }
    .status-badge-critical {
        background-color: rgba(255, 75, 75, 0.15);
        color: #FF4B4B;
        border: 1px solid #FF4B4B;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        display: inline-block;
        animation: pulse 1.5s infinite;
    }
    @keyframes pulse {
        0% { opacity: 0.7; }
        50% { opacity: 1; }
        100% { opacity: 0.7; }
    }
    .actuator-box {
        background: #131722;
        border-left: 4px solid #00FFA3;
        padding: 12px 16px;
        margin-bottom: 8px;
        border-radius: 0 8px 8px 0;
    }
</style>
""", unsafe_allow_html=True)


# Initialize Session State Singletons
if "engine" not in st.session_state:
    st.session_state.engine = IoTDecisionEngine()

if "simulator" not in st.session_state:
    st.session_state.simulator = IoTSensorSimulator(device_id="TURBINE_PUMP_ALPHA")

if "mqtt_manager" not in st.session_state:
    mqtt_mgr = MQTTManager(broker="broker.emqx.io", port=1883)
    mqtt_mgr.connect(timeout=1.5)
    st.session_state.mqtt_manager = mqtt_mgr

if "stream_active" not in st.session_state:
    st.session_state.stream_active = True

if "last_reading" not in st.session_state:
    st.session_state.last_reading = None

if "last_evaluation" not in st.session_state:
    st.session_state.last_evaluation = None

if "pending_actions" not in st.session_state:
    st.session_state.pending_actions = []


# Sidebar Controls
st.sidebar.image("https://img.icons8.com/isometric/100/circuit.png", width=64)
st.sidebar.title("IoT Autonomous Control")
st.sidebar.caption("MQTT • Node-RED • ML • Grafana • Streamlit")

# Broker Connection Status Badge
mqtt_status = "Connected (EMQX)" if (st.session_state.mqtt_manager.connected and not st.session_state.mqtt_manager.using_internal_broker) else "Active (In-Memory Failover)"
st.sidebar.markdown(f"**Broker Status:** `{mqtt_status}`")

st.sidebar.markdown("---")
st.sidebar.subheader("📡 Telemetry Simulation")

stream_toggle = st.sidebar.toggle("Auto-Stream Telemetry", value=st.session_state.stream_active)
st.session_state.stream_active = stream_toggle

stream_speed = st.sidebar.slider("Stream Refresh Interval (s)", min_value=1.0, max_value=5.0, value=2.0, step=0.5)

st.sidebar.markdown("---")
st.sidebar.subheader("⚠️ Fault Injection Suite")
fault_option = st.sidebar.selectbox(
    "Inject Operating Condition:",
    [
        ("NONE", "🟢 Normal Operation (Nominal)"),
        ("THERMAL_RUNAWAY", "🔥 Thermal Runaway (>85°C)"),
        ("BEARING_DAMAGE", "⚙️ Bearing Vibration Spikes (>7.0 mm/s)"),
        ("PRESSURE_SURGE", "💥 Hydraulic Overpressure (>8.0 bar)"),
        ("MOTOR_OVERLOAD", "⚡ Electrical Overcurrent (>45A)"),
        ("ML_CORRELATED_DRIFT", "🧠 Subtle Multivariate Drift (ML Anomaly)")
    ],
    format_func=lambda x: x[1]
)[0]

st.session_state.simulator.inject_fault(fault_option)

st.sidebar.markdown("---")
st.sidebar.subheader("🎛️ Operation Mode")
op_mode = st.sidebar.radio(
    "Decision Authority:",
    ["autonomous", "supervised", "manual"],
    format_func=lambda x: {
        "autonomous": "🤖 Autonomous (Auto-Pilot)",
        "supervised": "🧑‍✈️ Supervised (Human-in-Loop)",
        "manual": "🛠️ Manual Override Only"
    }[x],
    index=0
)
st.session_state.engine.set_decision_mode(op_mode)

# Manual Step Generation Trigger
manual_step = st.sidebar.button("⚡ Generate Single Telemetry Step", use_container_width=True)

# Generate Reading if Streaming or Manually Triggered
if st.session_state.stream_active or manual_step or st.session_state.last_reading is None:
    reading = st.session_state.simulator.generate_next_reading()
    evaluation = st.session_state.engine.evaluate(reading)
    
    # Publish to MQTT Pipeline
    st.session_state.mqtt_manager.publish(f"iot/telemetry/{reading.device_id}", evaluation)
    
    # If autonomous actions triggered, publish to actuator topics
    for action in evaluation.get("actuator_actions", []):
        topic = action.get("target_topic", "iot/actuators/general")
        st.session_state.mqtt_manager.publish(topic, action)
        
    # If alerts present, publish to alerts topic
    for alert in evaluation.get("alerts", []):
        st.session_state.mqtt_manager.publish(f"iot/alerts/{alert['type'].lower()}", alert)
        
    st.session_state.last_reading = reading
    st.session_state.last_evaluation = evaluation
    
    if op_mode == "supervised" and evaluation.get("severity") in ["WARNING", "CRITICAL"]:
        st.session_state.pending_actions = evaluation.get("actuator_actions", [])

eval_res = st.session_state.last_evaluation or {}
reading_res = st.session_state.last_reading


# Top Header Status Bar
header_col1, header_col2, header_col3 = st.columns([2, 1, 1])

with header_col1:
    st.title("⚡ Autonomous IoT Decision & Alert Platform")
    st.caption("Self-Healing Telemetry Pipeline • Edge Intelligence • Dynamic Policy Tuning")

with header_col2:
    health = eval_res.get("health_index", 100.0)
    health_color = "#00FFA3" if health >= 75 else ("#FFAA00" if health >= 50 else "#FF4B4B")
    st.metric(label="Asset Health Index", value=f"{health}%", delta=f"{health - 100:.1f}%")

with header_col3:
    sev = eval_res.get("severity", "NORMAL")
    badge_class = f"status-badge-{sev.lower()}"
    st.markdown(f"<div style='margin-top: 15px;'><span class='{badge_class}'>STATE: {sev}</span></div>", unsafe_allow_html=True)
    st.markdown(f"<small>Mode: <b>{op_mode.upper()}</b></small>", unsafe_allow_html=True)


# Main Tabs
tabs = st.tabs([
    "📡 Live Telemetry & Digital Twin",
    "🧠 Autonomous Decision Console",
    "⚙️ Dynamic Rules & User Controls",
    "🔬 Machine Learning Studio",
    "🔀 Node-RED & MQTT Pipeline",
    "📊 Grafana Analytics",
    "🚀 Cloud & GitHub Guide"
])


# TAB 1: Live Telemetry
with tabs[0]:
    st.subheader(f"Asset Telemetry: {st.session_state.simulator.device_id}")

    # Top Metric Gauges
    m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
    
    temp_val = reading_res.temperature if reading_res else 55.0
    vib_val = reading_res.vibration if reading_res else 2.2
    press_val = reading_res.pressure if reading_res else 4.2
    curr_val = reading_res.current if reading_res else 22.0
    humid_val = reading_res.humidity if reading_res else 48.0

    thresholds = st.session_state.engine.thresholds
    
    with m_col1:
        st.metric(
            "Temperature",
            f"{temp_val} °C",
            delta=f"{temp_val - thresholds['temp_warning']:.1f}° vs Warn" if temp_val > thresholds['temp_warning'] else "Normal",
            delta_color="inverse"
        )
    with m_col2:
        st.metric(
            "Vibration (RMS)",
            f"{vib_val} mm/s",
            delta=f"{vib_val - thresholds['vibration_warning']:.2f} mm/s" if vib_val > thresholds['vibration_warning'] else "Normal",
            delta_color="inverse"
        )
    with m_col3:
        st.metric(
            "Pressure",
            f"{press_val} bar",
            delta=f"{press_val - thresholds['pressure_warning']:.2f} bar" if press_val > thresholds['pressure_warning'] else "Normal",
            delta_color="inverse"
        )
    with m_col4:
        st.metric(
            "Motor Current",
            f"{curr_val} A",
            delta=f"{curr_val - thresholds['current_warning']:.1f} A" if curr_val > thresholds['current_warning'] else "Normal",
            delta_color="inverse"
        )
    with m_col5:
        st.metric(
            "Humidity",
            f"{humid_val} %",
            delta="Normal"
        )

    # Historical Telemetry Time Series
    df_hist = st.session_state.mqtt_manager.get_telemetry_df()
    
    if not df_hist.empty and len(df_hist) > 1:
        c1, c2 = st.columns(2)
        
        with c1:
            fig_temp = px.line(
                df_hist.tail(40),
                y="temperature",
                title="Temperature (°C) with Safety Envelopes",
                color_discrete_sequence=["#FF7675"]
            )
            fig_temp.add_hline(y=thresholds["temp_warning"], line_dash="dash", line_color="#FFAA00", annotation_text="Warning")
            fig_temp.add_hline(y=thresholds["temp_critical"], line_dash="solid", line_color="#FF4B4B", annotation_text="Critical")
            fig_temp.update_layout(template="plotly_dark", margin=dict(l=20, r=20, t=40, b=20), height=280)
            st.plotly_chart(fig_temp, use_container_width=True)

        with c2:
            fig_vib = px.line(
                df_hist.tail(40),
                y="vibration",
                title="Bearing Vibration (mm/s RMS)",
                color_discrete_sequence=["#74B9FF"]
            )
            fig_vib.add_hline(y=thresholds["vibration_warning"], line_dash="dash", line_color="#FFAA00", annotation_text="Warning")
            fig_vib.add_hline(y=thresholds["vibration_critical"], line_dash="solid", line_color="#FF4B4B", annotation_text="Critical")
            fig_vib.update_layout(template="plotly_dark", margin=dict(l=20, r=20, t=40, b=20), height=280)
            st.plotly_chart(fig_vib, use_container_width=True)

        c3, c4 = st.columns(2)
        with c3:
            fig_press = px.line(
                df_hist.tail(40),
                y="pressure",
                title="Hydraulic Line Pressure (bar)",
                color_discrete_sequence=["#A29BFE"]
            )
            fig_press.add_hline(y=thresholds["pressure_warning"], line_dash="dash", line_color="#FFAA00", annotation_text="Warning")
            fig_press.add_hline(y=thresholds["pressure_critical"], line_dash="solid", line_color="#FF4B4B", annotation_text="Critical")
            fig_press.update_layout(template="plotly_dark", margin=dict(l=20, r=20, t=40, b=20), height=280)
            st.plotly_chart(fig_press, use_container_width=True)

        with c4:
            fig_health = px.line(
                df_hist.tail(40),
                y="health_index",
                title="Asset Health Index Degradation Curve",
                color_discrete_sequence=["#00FFA3"]
            )
            fig_health.add_hline(y=50.0, line_dash="dash", line_color="#FF4B4B", annotation_text="Critical Trip")
            fig_health.update_layout(template="plotly_dark", margin=dict(l=20, r=20, t=40, b=20), height=280)
            st.plotly_chart(fig_health, use_container_width=True)
    else:
        st.info("Accumulating telemetry samples... Toggle simulation or click 'Generate Single Telemetry Step' to view historical charts.")


# TAB 2: Autonomous Decision Console
with tabs[1]:
    st.subheader("🤖 Autonomous Decision Engine & Actuator Dispatches")
    
    col_act, col_alert = st.columns([1.2, 1])

    with col_act:
        st.markdown("#### Active Actuator Commands")
        actions = eval_res.get("actuator_actions", [])
        if actions:
            for act in actions:
                st.markdown(f"""
                <div class="actuator-box">
                    <span style="font-size: 1.1em; font-weight: bold; color: #00FFA3;">⚡ {act.get('actuator')}</span> &rarr; <code>{act.get('action')}</code><br/>
                    <small style="color: #A0AEC0;">Rationale: {act.get('reason')}</small><br/>
                    <small style="color: #63B3ED;">MQTT Topic: <code>{act.get('target_topic')}</code></small>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("All systems operating within nominal envelopes. No actuator intervention needed.")

        # Supervised Mode Operator Approval UI
        if op_mode == "supervised" and st.session_state.pending_actions:
            st.warning("⚠️ Supervised Mode: Operator confirmation required before actuator deployment.")
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.button("✅ Approve & Dispatch All Actions", use_container_width=True):
                    for pa in st.session_state.pending_actions:
                        st.session_state.mqtt_manager.publish(pa.get("target_topic", "iot/actuators/approved"), pa)
                    st.success("Operator approved! Commands dispatched over MQTT.")
                    st.session_state.pending_actions = []
            with btn_col2:
                if st.button("❌ Reject / Dismiss", use_container_width=True):
                    st.session_state.pending_actions = []
                    st.info("Actions dismissed by operator.")

        # Manual Override Panel
        if op_mode == "manual":
            st.markdown("#### 🛠️ Manual Actuator Override Console")
            btn1, btn2, btn3, btn4 = st.columns(4)
            with btn1:
                if st.button("❄️ Start Cooling", use_container_width=True):
                    st.session_state.mqtt_manager.publish("iot/actuators/cooling", {"command": "MANUAL_COOLING_CYCLE", "source": "USER_OVERRIDE"})
                    st.toast("Dispatched: MANUAL_COOLING_CYCLE")
            with btn2:
                if st.button("💨 Open Valve", use_container_width=True):
                    st.session_state.mqtt_manager.publish("iot/actuators/valves", {"command": "MANUAL_VALVE_RELEASE", "source": "USER_OVERRIDE"})
                    st.toast("Dispatched: MANUAL_VALVE_RELEASE")
            with btn3:
                if st.button("🛑 Derate Motor", use_container_width=True):
                    st.session_state.mqtt_manager.publish("iot/actuators/motors", {"command": "MANUAL_DERATE_50%", "source": "USER_OVERRIDE"})
                    st.toast("Dispatched: MANUAL_DERATE_50%")
            with btn4:
                if st.button("🔄 Reset Alerts", use_container_width=True):
                    st.session_state.mqtt_manager.publish("iot/control/reset", {"command": "SYSTEM_ALERTS_RESET", "source": "USER_OVERRIDE"})
                    st.toast("Dispatched: SYSTEM_ALERTS_RESET")

    with col_alert:
        st.markdown("#### 🚨 Real-Time Alerts")
        alerts = eval_res.get("alerts", [])
        if alerts:
            for al in alerts:
                alert_type = al.get("type", "ALERT")
                if "CRITICAL" in alert_type:
                    st.error(f"🔴 **{alert_type}**: {al.get('msg')}")
                elif "WARNING" in alert_type:
                    st.warning(f"🟡 **{alert_type}**: {al.get('msg')}")
                else:
                    st.info(f"🔵 **{alert_type}**: {al.get('msg')}")
        else:
            st.success("No active alerts. Zero critical anomalies detected.")

    st.markdown("---")
    st.markdown("#### 📜 Autonomous Decision Audit Log")
    if len(st.session_state.mqtt_manager.decision_history) > 0:
        decision_df = pd.DataFrame(list(st.session_state.mqtt_manager.decision_history)).tail(15)
        st.dataframe(decision_df, use_container_width=True)
    else:
        st.caption("No decision events logged yet.")


# TAB 3: Dynamic Rules & User Controls
with tabs[2]:
    st.subheader("⚙️ Dynamic Operating Envelopes & User Threshold Customization")
    st.markdown("Customize autonomous trigger thresholds in real-time. Changes apply instantly without restarting the pipeline.")

    with st.form("threshold_form"):
        col_t1, col_t2 = st.columns(2)
        
        with col_t1:
            st.markdown("##### 🌡️ Thermal Limits")
            new_temp_warn = st.slider("Temperature Warning Threshold (°C)", 40.0, 95.0, float(thresholds["temp_warning"]), 1.0)
            new_temp_crit = st.slider("Temperature Critical Threshold (°C)", 50.0, 110.0, float(thresholds["temp_critical"]), 1.0)

            st.markdown("##### ⚙️ Vibration Limits")
            new_vib_warn = st.slider("Vibration Warning (mm/s RMS)", 1.0, 10.0, float(thresholds["vibration_warning"]), 0.1)
            new_vib_crit = st.slider("Vibration Critical (mm/s RMS)", 2.0, 15.0, float(thresholds["vibration_critical"]), 0.1)

        with col_t2:
            st.markdown("##### 💥 Hydraulic Pressure Limits")
            new_press_warn = st.slider("Pressure Warning Threshold (bar)", 3.0, 9.0, float(thresholds["pressure_warning"]), 0.1)
            new_press_crit = st.slider("Pressure Critical Threshold (bar)", 4.0, 12.0, float(thresholds["pressure_critical"]), 0.1)

            st.markdown("##### ⚡ Motor Current Limits")
            new_curr_warn = st.slider("Motor Current Warning (A)", 15.0, 50.0, float(thresholds["current_warning"]), 1.0)
            new_curr_crit = st.slider("Motor Current Critical (A)", 25.0, 70.0, float(thresholds["current_critical"]), 1.0)

        st.markdown("---")
        st.markdown("##### 🔔 Alert Escalation Webhook Integration")
        webhook_url = st.text_input("Dispatch Webhook URL (Slack / Discord / Custom Endpoint):", value="https://httpbin.org/post")

        submitted = st.form_submit_button("💾 Save & Apply Dynamic Policy to IoT Network", use_container_width=True)
        if submitted:
            new_rules = {
                "temp_warning": new_temp_warn,
                "temp_critical": new_temp_crit,
                "vibration_warning": new_vib_warn,
                "vibration_critical": new_vib_crit,
                "pressure_warning": new_press_warn,
                "pressure_critical": new_press_crit,
                "current_warning": new_curr_warn,
                "current_critical": new_curr_crit,
            }
            st.session_state.engine.update_thresholds(new_rules)
            # Publish policy update to MQTT network
            st.session_state.mqtt_manager.publish("iot/control/policy_update", {
                "updated_by": "USER",
                "timestamp": datetime.utcnow().isoformat(),
                "thresholds": new_rules,
                "webhook_url": webhook_url
            })
            st.success("✅ Threshold rules updated successfully and broadcasted across MQTT mesh!")


# TAB 4: Machine Learning Studio
with tabs[3]:
    st.subheader("🔬 Machine Learning Studio & Anomaly Detection")
    st.markdown("Unsupervised multivariate anomaly detection utilizing **Isolation Forest** to identify subtle equipment degradation before hard thresholds are breached.")

    col_ml1, col_ml2 = st.columns([1, 2])
    
    with col_ml1:
        st.markdown("##### Model Configuration")
        st.write(f"**Algorithm:** `Isolation Forest` (Scikit-Learn)")
        st.write(f"**Estimators:** `100 Trees`")
        st.write(f"**Current Contamination Factor:** `{st.session_state.engine.contamination:.2f}`")
        
        ml_score = eval_res.get("ml_confidence_score", 0.5)
        is_ano = eval_res.get("ml_anomaly", False)
        
        st.metric(
            label="Live Anomaly Probability Score",
            value=f"{ml_score:.3f}",
            delta="Anomaly Detected!" if is_ano else "Nominal Distribution",
            delta_color="inverse" if is_ano else "normal"
        )

        st.markdown("##### Retune Sensitivity")
        new_contamination = st.slider("Contamination (Expected Anomaly %)", 0.01, 0.20, float(st.session_state.engine.contamination), 0.01)
        if st.button("⚡ Retrain & Recalibrate Baseline Model", use_container_width=True):
            st.session_state.engine.contamination = new_contamination
            st.session_state.engine.train_baseline_model(n_samples=1000)
            st.success(f"Model recalibrated with contamination factor = {new_contamination}!")

    with col_ml2:
        st.markdown("##### Multivariate Anomaly Scatter Space (Temperature vs. Vibration)")
        # Create synthetic evaluation dataset to plot decision boundary
        np.random.seed(42)
        n_pts = 200
        normal_t = np.random.normal(55, 4.5, n_pts)
        normal_v = np.random.normal(2.2, 0.5, n_pts)
        
        plot_df = pd.DataFrame({
            "temperature": normal_t,
            "vibration": normal_v,
            "category": ["Baseline Normal"] * n_pts
        })
        
        # Add current live telemetry point
        if reading_res:
            cur_cat = "🚨 Anomaly" if is_ano else "🟢 Live Telemetry"
            plot_df = pd.concat([
                plot_df,
                pd.DataFrame({
                    "temperature": [reading_res.temperature],
                    "vibration": [reading_res.vibration],
                    "category": [cur_cat]
                })
            ], ignore_index=True)

        fig_scatter = px.scatter(
            plot_df,
            x="temperature",
            y="vibration",
            color="category",
            color_discrete_map={
                "Baseline Normal": "#636EFA",
                "🟢 Live Telemetry": "#00FFA3",
                "🚨 Anomaly": "#FF4B4B"
            },
            title="Isolation Forest Multivariate Clustering",
            labels={"temperature": "Temperature (°C)", "vibration": "Vibration (mm/s)"}
        )
        fig_scatter.update_traces(marker=dict(size=8, opacity=0.8))
        if reading_res:
            fig_scatter.add_trace(go.Scatter(
                x=[reading_res.temperature],
                y=[reading_res.vibration],
                mode="markers+text",
                marker=dict(size=18, color="#00FFA3" if not is_ano else "#FF4B4B", symbol="diamond"),
                text=["Current Asset"],
                textposition="top center",
                name="Live Asset Position"
            ))
        fig_scatter.update_layout(template="plotly_dark", height=350, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_scatter, use_container_width=True)


# TAB 5: Node-RED & MQTT Pipeline
with tabs[4]:
    st.subheader("🔀 Node-RED Event Orchestration & MQTT Message Bus")
    
    col_n1, col_n2 = st.columns([1, 1])
    
    with col_n1:
        st.markdown("##### Node-RED Architecture Flow")
        st.info("""
        **Pipeline Flow:**
        1. **`iot/telemetry/#` Ingest**: Sensor packets received from Edge brokers.
        2. **Autonomous Matrix Function Node**: Analyzes envelopes & ML flags.
        3. **Actuator Topic Dispatch**: Dispatches targeted mitigation payloads.
        4. **Alert Webhook**: Triggers immediate external notifications.
        """)
        
        with open("node_red/flows.json", "r") as f:
            flows_content = f.read()
            
        st.download_button(
            label="📥 Download Production Node-RED Flow (`flows.json`)",
            data=flows_content,
            file_name="node_red_iot_autonomous_flows.json",
            mime="application/json",
            use_container_width=True
        )

        st.markdown("##### Manual MQTT Publish Sandbox")
        with st.form("mqtt_test_form"):
            sandbox_topic = st.text_input("Target Topic:", value="iot/control/manual_override")
            sandbox_payload = st.text_area("JSON Payload:", value='{"action": "COOLING_TEST", "power_pct": 80}')
            if st.form_submit_button("🚀 Publish Test Message to MQTT"):
                try:
                    payload_json = json.loads(sandbox_payload)
                    st.session_state.mqtt_manager.publish(sandbox_topic, payload_json)
                    st.success(f"Published to `{sandbox_topic}`!")
                except Exception as e:
                    st.error(f"Invalid JSON: {e}")

    with col_n2:
        st.markdown("##### Live MQTT Packet Stream")
        raw_msgs = list(st.session_state.mqtt_manager.raw_message_log)
        if raw_msgs:
            recent_msgs = raw_msgs[-10:][::-1]
            for msg in recent_msgs:
                with st.expander(f"Topic: {msg['topic']} [{msg['timestamp']}]", expanded=False):
                    st.json(msg["data"])
        else:
            st.caption("Waiting for incoming MQTT packets...")


# TAB 6: Grafana Analytics
with tabs[5]:
    st.subheader("📊 Grafana Telemetry Dashboard Integration")
    st.markdown("High-resolution telemetry dashboards powered by Grafana panels.")

    g_col1, g_col2 = st.columns([1.5, 1])
    
    with g_col1:
        st.markdown("##### Live Embedded Grafana-Style Gauges")
        # Visual interactive gauge using Plotly
        fig_g1 = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=health,
            title={'text': "Asset Health Score (%)"},
            delta={'reference': 100},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': health_color},
                'steps': [
                    {'range': [0, 50], 'color': "rgba(255, 75, 75, 0.2)"},
                    {'range': [50, 75], 'color': "rgba(255, 170, 0, 0.2)"},
                    {'range': [75, 100], 'color': "rgba(0, 255, 163, 0.2)"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 50
                }
            }
        ))
        fig_g1.update_layout(template="plotly_dark", height=280, margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig_g1, use_container_width=True)

    with g_col2:
        st.markdown("##### Export Grafana Dashboard Config")
        st.write("Import this pre-configured JSON dashboard directly into your enterprise Grafana instance.")
        
        with open("grafana/dashboards/iot_autonomous_dashboard.json", "r") as gf:
            grafana_json = gf.read()

        st.download_button(
            label="📥 Download Grafana Dashboard JSON",
            data=grafana_json,
            file_name="grafana_iot_autonomous_dashboard.json",
            mime="application/json",
            use_container_width=True
        )

        st.markdown("##### Quick Docker Launch Command")
        st.code("docker compose up -d\n# Opens Grafana at http://localhost:3000 (admin/admin)", language="bash")


# TAB 7: Cloud Deployment & GitHub Setup Guide
with tabs[6]:
    st.subheader("🚀 Upload to GitHub & Deploy to Streamlit Community Cloud")
    st.markdown("Deploy this platform to the cloud so **anyone can access it from any phone, tablet, or laptop via a public URL**!")

    step_c1, step_c2 = st.columns(2)

    with step_c1:
        st.markdown("### Step 1: Push to GitHub")
        st.markdown("""
        1. Create a new repository on [GitHub](https://github.com/new), e.g. `iot-autonomous-decision-platform`.
        2. In your terminal inside this project directory, run:
        """)
        st.code("""git init
git add .
git commit -m "Initial commit: Autonomous IoT Decision Platform"
git branch -M main
git remote add origin https://github.com/<YOUR-USERNAME>/<YOUR-REPO-NAME>.git
git push -u origin main""", language="bash")

    with step_c2:
        st.markdown("### Step 2: Deploy to Streamlit Cloud (Free & Instant)")
        st.markdown("""
        1. Go to [share.streamlit.io](https://share.streamlit.io/) and log in with your GitHub account.
        2. Click **New App**.
        3. Select your repository: `<YOUR-USERNAME>/<YOUR-REPO-NAME>`.
        4. Main file path: `app.py`.
        5. Click **Deploy!**
        
        🎉 **Your app is now live with a public HTTPS link accessible on any browser, mobile phone, or desktop worldwide!**
        """)

    st.markdown("---")
    st.markdown("### 🐳 Optional: Local Full-Stack Docker Deployment")
    st.markdown("To run **Mosquitto + Node-RED + Grafana + Streamlit** all together locally:")
    st.code("docker compose up --build", language="bash")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #718096; font-size: 0.9em;'>"
    "Autonomous IoT Decision & Alert Management Platform • Built with MQTT, Node-RED, Python, ML, Grafana & Streamlit"
    "</div>",
    unsafe_allow_html=True
)

# Rerun loop for live streaming telemetry if active
if st.session_state.stream_active:
    time.sleep(stream_speed)
    st.rerun()

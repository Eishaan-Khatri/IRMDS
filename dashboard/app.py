"""
IRMDS dashboard command center.
"""

import json
import os
import time

import httpx
import streamlit as st

from dashboard.components.css_injector import inject_custom_css
from dashboard.components.ws_client import get_or_create_event_queue, start_websocket_thread

API_URL = os.getenv("IRMDS_API_URL", "http://127.0.0.1:8000").rstrip("/")


st.set_page_config(
    page_title="IRMDS | Command Center",
    page_icon="IRMDS",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_custom_css()

get_or_create_event_queue()
start_websocket_thread()

with st.sidebar:
    st.markdown(
        "<h1 style='text-align: center; color: white;'>IRMDS</h1>",
        unsafe_allow_html=True,
    )

    status_color = "#00f3ff" if st.session_state.ws_connected else "#ff0055"
    st.markdown(
        (
            "<div style='text-align: center; margin-bottom: 2rem;'>"
            f"<span class='status-pulse' style='background-color: {status_color}; "
            f"box-shadow: 0 0 10px {status_color};'></span> "
            "<b>SYSTEM ONLINE</b></div>"
        ),
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.page_link("app.py", label="COMMAND CENTER", icon=":material/monitoring:")
    st.page_link("pages/01_visual.py", label="VISUAL HUD", icon=":material/visibility:")

try:
    health_res = httpx.get(f"{API_URL}/health", timeout=2)
    api_status = health_res.status_code == 200
except Exception:
    api_status = False

if not api_status:
    st.error("CORE DISCONNECTED: FastAPI backend unreachable.")
    st.stop()

st.markdown("## SYSTEM INTEGRITY COMMAND CENTER")

col1, col2, col3 = st.columns(3)

try:
    metrics_res = httpx.get(f"{API_URL}/metrics", timeout=2).json()
    uptime = metrics_res.get("system_uptime_seconds", 0)
    uptime_hrs = uptime / 3600
    uptime_str = f"{uptime_hrs:.1f}h" if uptime_hrs > 1 else f"{uptime / 60:.1f}m"
    running_modules = len(metrics_res.get("modules", []))
except Exception:
    uptime_str = "OFFLINE"
    running_modules = 0

with col1:
    st.metric(label="KERNEL UPTIME", value=uptime_str)
with col2:
    st.metric(label="ACTIVE MODULES", value=f"{running_modules}/4")
with col3:
    st.metric(label="LIVE TELEMETRY", value=len(st.session_state.event_queue))

st.markdown("---")
st.markdown("## SIMULATED COMMAND PLANE")

ctrl_col1, ctrl_col2 = st.columns([1, 2])

with ctrl_col1:
    st.markdown("### PROPOSE COMMAND")
    with st.form("propose_cmd_form", clear_on_submit=True):
        target_device = st.selectbox(
            "TARGET SYSTEM",
            ["CNC_01", "HVAC_SYS", "SERVER_RACK", "MAIN_VALVE"],
        )
        action = st.selectbox(
            "ACTION PROTOCOL",
            ["SHUTDOWN_MACHINE", "REBOOT", "EMERGENCY_STOP", "SET_MAINTENANCE_MODE"],
        )
        reason = st.text_input("AUTHORIZATION REASON")
        dry_run = st.checkbox("SIMULATION MODE", value=True)
        submitted = st.form_submit_button("PROPOSE DRY-RUN COMMAND")

        if submitted:
            payload = {
                "action": action,
                "target_device": target_device,
                "payload": {"reason": reason},
                "dry_run": dry_run,
            }
            try:
                res = httpx.post(f"{API_URL}/commands", json=payload, timeout=5)
                if res.status_code == 200:
                    st.toast("DRY-RUN COMMAND PROPOSED")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error(f"PROTOCOL FAILURE: {res.text}")
            except Exception as exc:
                st.error(f"COMMUNICATION ERROR: {exc}")

with ctrl_col2:
    st.markdown("### COMMAND LEDGER")
    try:
        cmd_res = httpx.get(f"{API_URL}/commands", params={"limit": 5}, timeout=5)
        if cmd_res.status_code == 200:
            commands = cmd_res.json().get("commands", [])
            if not commands:
                st.caption("NO ACTIVE COMMANDS IN LEDGER")
            else:
                for cmd in commands:
                    state_labels = {
                        "pending": "PENDING",
                        "approved": "APPROVED",
                        "executing": "EXECUTING",
                        "completed": "COMPLETED",
                        "failed": "FAILED",
                    }
                    state_label = state_labels.get(cmd["state"], cmd["state"].upper())

                    with st.container(border=True):
                        c_a, c_b, c_c = st.columns([3, 1, 1])
                        with c_a:
                            st.markdown(f"**{cmd['action']}** -> `{cmd['target_device']}`")
                            if cmd["payload"].get("reason"):
                                st.caption(f"AUTH: {cmd['payload']['reason']}")
                        with c_b:
                            st.markdown(f"`{state_label}`")
                        with c_c:
                            if cmd["state"] == "pending" and st.button(
                                "AUTHORIZE", key=f"auth_{cmd['id']}"
                            ):
                                httpx.post(
                                    f"{API_URL}/commands/{cmd['id']}/approve",
                                    timeout=5,
                                )
                                st.rerun()
        else:
            st.error("LEDGER OFFLINE")
    except Exception as exc:
        st.error(f"SYNC ERROR: {exc}")

st.markdown("---")
st.markdown("### LIVE TELEMETRY STREAM")
st.markdown('<div class="live-feed-container">', unsafe_allow_html=True)
if not st.session_state.event_queue:
    st.markdown(
        "<p style='color: #888; text-align: center; padding: 20px;'>AWAITING TELEMETRY...</p>",
        unsafe_allow_html=True,
    )
else:
    for evt in list(st.session_state.event_queue)[-20:]:
        sev = evt.get("severity", "INFO")
        timestamp = evt.get("timestamp", "")
        time_str = timestamp.split("T")[1][:8] if "T" in timestamp else ""

        if evt.get("type") == "COMMAND_EXECUTED":
            st.markdown(
                f"<div class='alert-entry alert-severity-INFO'>[{time_str}] "
                f"<b>DRY-RUN COMMAND</b>: {evt.get('data', {}).get('action')} on "
                f"{evt.get('data', {}).get('target_device')} COMPLETED</div>",
                unsafe_allow_html=True,
            )
        else:
            module = evt.get("module", "unknown")
            st.markdown(
                f"<div class='alert-entry alert-severity-{sev}'>[{time_str}] "
                f"<b>{module.upper()}</b>: {evt.get('type')} "
                f"<span style='color: #666;'>| {json.dumps(evt.get('data'))}</span></div>",
                unsafe_allow_html=True,
            )
st.markdown("</div>", unsafe_allow_html=True)

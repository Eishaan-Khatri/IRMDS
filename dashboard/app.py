"""
IRMDS dashboard command center.
"""

from __future__ import annotations

import json
import os
import time

import streamlit as st

from dashboard.components.api_client import get_json, post_json
from dashboard.components.css_injector import inject_custom_css
from dashboard.components.ws_client import get_or_create_event_queue, start_websocket_thread

API_URL = os.getenv("IRMDS_API_URL", "http://127.0.0.1:8000").rstrip("/")
DEMO_MODE = os.getenv("IRMDS_DEMO_MODE", "").lower() in {"1", "true", "yes", "on"}


def _format_uptime(seconds: float) -> str:
    if seconds >= 3600:
        return f"{seconds / 3600:.1f}h"
    if seconds >= 60:
        return f"{seconds / 60:.1f}m"
    return f"{seconds:.0f}s"


def _render_status_badge(status: str) -> str:
    colors = {
        "running": "#2ea043",
        "stopped": "#8b949e",
        "starting": "#d29922",
        "stopping": "#d29922",
        "error": "#f85149",
    }
    color = colors.get(status, "#8b949e")
    return (
        f"<span style='display:inline-block; padding:2px 8px; border-radius:999px; "
        f"background:{color}22; color:{color}; border:1px solid {color}66; "
        f"font-size:0.75rem; font-weight:700;'>{status.upper()}</span>"
    )


st.set_page_config(
    page_title="IRMDS | Command Center",
    page_icon="IRMDS",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_custom_css()

get_or_create_event_queue()
start_websocket_thread()

health_data, health_error = get_json(API_URL, "/health")
api_status = health_error is None

with st.sidebar:
    st.markdown(
        "<h1 style='text-align: center; color: white;'>IRMDS</h1>",
        unsafe_allow_html=True,
    )

    status_color = "#00f3ff" if api_status else "#ff0055"
    status_text = "API ONLINE" if api_status else "API OFFLINE"
    st.markdown(
        (
            "<div style='text-align: center; margin-bottom: 1rem;'>"
            f"<span class='status-pulse' style='background-color: {status_color}; "
            f"box-shadow: 0 0 10px {status_color};'></span> "
            f"<b>{status_text}</b></div>"
        ),
        unsafe_allow_html=True,
    )

    ws_color = "#00f3ff" if st.session_state.ws_connected else "#8b949e"
    ws_text = "EVENT STREAM CONNECTED" if st.session_state.ws_connected else "EVENT STREAM WAITING"
    st.markdown(
        (
            "<div style='text-align: center; margin-bottom: 1rem;'>"
            f"<span class='status-pulse' style='background-color: {ws_color}; "
            f"box-shadow: 0 0 10px {ws_color};'></span> "
            f"<b>{ws_text}</b></div>"
        ),
        unsafe_allow_html=True,
    )

    if DEMO_MODE:
        st.info("Demo Mode: sample data and simulated commands only.")

    st.markdown("---")
    st.page_link("app.py", label="COMMAND CENTER", icon=":material/monitoring:")
    st.page_link("pages/01_visual.py", label="VISUAL HUD", icon=":material/visibility:")

if not api_status:
    st.error(f"Core disconnected: FastAPI backend unreachable at {API_URL}.")
    if health_error:
        st.caption(health_error)
    st.stop()

modules_data, modules_error = get_json(API_URL, "/modules")
metrics_data, metrics_error = get_json(API_URL, "/metrics")
commands_data, commands_error = get_json(API_URL, "/commands", params={"limit": 5})
alerts_data, alerts_error = get_json(API_URL, "/alerts/latest", params={"limit": 8})

modules = modules_data if isinstance(modules_data, list) else []
metric_modules = metrics_data.get("modules", []) if metrics_error is None else []
commands = commands_data.get("commands", []) if commands_error is None else []
latest_alerts = alerts_data if isinstance(alerts_data, list) else []

running_modules = [module for module in modules if module.get("status") == "running"]

st.markdown("## SYSTEM INTEGRITY COMMAND CENTER")

if DEMO_MODE:
    st.success("Demo Mode active: deterministic sample data, local API, and dry-run commands.")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Kernel Uptime", _format_uptime(float(health_data.get("uptime_seconds", 0))))
with col2:
    st.metric("Registered Modules", f"{len(modules)}/4")
with col3:
    st.metric("Running Modules", f"{len(running_modules)}/{len(modules) or 4}")
with col4:
    st.metric("Live Events", len(st.session_state.event_queue))

st.markdown("---")
status_col, metrics_col = st.columns([1, 1])

with status_col:
    st.markdown("### Module Status")
    if modules_error:
        st.error(f"Module list unavailable: {modules_error}")
    elif not modules:
        st.caption("No modules discovered. The plugin registry may not have completed startup.")
    else:
        for module in modules:
            with st.container(border=True):
                left, right = st.columns([3, 1])
                with left:
                    st.markdown(f"**{module['display_name']}**")
                    st.caption(f"ID: {module['id']} | v{module['version']}")
                with right:
                    st.markdown(_render_status_badge(module["status"]), unsafe_allow_html=True)

with metrics_col:
    st.markdown("### Current Metrics")
    if metrics_error:
        st.error(f"Metrics unavailable: {metrics_error}")
    elif not metric_modules:
        st.caption("No current module metrics yet. Start a module or run demo mode to populate metrics.")
    else:
        for item in metric_modules:
            module_id = item.get("module_id", "unknown")
            metrics = item.get("metrics", {})
            with st.container(border=True):
                st.markdown(f"**{module_id.upper()}**")
                if not metrics:
                    st.caption("No metrics reported.")
                else:
                    st.json(metrics, expanded=False)

st.markdown("---")
st.markdown("## SIMULATED COMMAND PLANE")

ctrl_col1, ctrl_col2 = st.columns([1, 2])

with ctrl_col1:
    st.markdown("### Propose Command")
    with st.form("propose_cmd_form", clear_on_submit=True):
        target_device = st.selectbox(
            "Target system",
            ["CNC_01", "HVAC_SYS", "SERVER_RACK", "MAIN_VALVE"],
        )
        action = st.selectbox(
            "Action protocol",
            ["SHUTDOWN_MACHINE", "REBOOT", "EMERGENCY_STOP", "SET_MAINTENANCE_MODE"],
        )
        reason = st.text_input("Authorization reason")
        dry_run = st.checkbox("Simulation mode", value=True)
        submitted = st.form_submit_button("Propose dry-run command")

        if submitted:
            payload = {
                "action": action,
                "target_device": target_device,
                "payload": {"reason": reason},
                "dry_run": dry_run,
            }
            data, error = post_json(API_URL, "/commands", payload)
            if error:
                st.error(f"Command proposal failed: {error}")
            elif data.get("status") == "accepted":
                st.toast("Dry-run command proposed")
                time.sleep(0.5)
                st.rerun()

with ctrl_col2:
    st.markdown("### Dry-Run Command Status")
    if commands_error:
        st.error(f"Command ledger unavailable: {commands_error}")
    elif not commands:
        st.caption("No commands in the ledger. Propose one to test the simulated command path.")
    else:
        for command in commands:
            with st.container(border=True):
                c_a, c_b, c_c = st.columns([3, 1, 1])
                with c_a:
                    st.markdown(f"**{command['action']}** on `{command['target_device']}`")
                    reason = command.get("payload", {}).get("reason")
                    if reason:
                        st.caption(f"Reason: {reason}")
                    st.caption(f"Dry-run: {command.get('dry_run', True)}")
                with c_b:
                    st.markdown(
                        _render_status_badge(command.get("state", "unknown")),
                        unsafe_allow_html=True,
                    )
                with c_c:
                    if command.get("state") == "pending" and st.button(
                        "Authorize", key=f"auth_{command['id']}"
                    ):
                        post_json(API_URL, f"/commands/{command['id']}/approve")
                        st.rerun()

st.markdown("---")
event_col, alert_col = st.columns([1, 1])

with event_col:
    st.markdown("### Latest Live Events")
    st.markdown('<div class="live-feed-container">', unsafe_allow_html=True)
    if not st.session_state.event_queue:
        st.markdown(
            "<p style='color: #888; text-align: center; padding: 20px;'>"
            "Awaiting WebSocket telemetry. Start demo mode or a module to stream events."
            "</p>",
            unsafe_allow_html=True,
        )
    else:
        for event in list(st.session_state.event_queue)[:20]:
            severity = event.get("severity", "INFO")
            timestamp = event.get("timestamp", "")
            time_str = timestamp.split("T")[1][:8] if "T" in timestamp else ""
            module = event.get("module", "unknown")
            data = json.dumps(event.get("data", {}), sort_keys=True)
            st.markdown(
                f"<div class='alert-entry alert-severity-{severity}'>[{time_str}] "
                f"<b>{module.upper()}</b>: {event.get('type')} "
                f"<span style='color: #666;'>| {data}</span></div>",
                unsafe_allow_html=True,
            )
    st.markdown("</div>", unsafe_allow_html=True)

with alert_col:
    st.markdown("### Latest Persisted Alerts")
    if alerts_error:
        st.error(f"Alert feed unavailable: {alerts_error}")
    elif not latest_alerts:
        st.caption("No persisted alerts yet. Demo events may appear in the live stream first.")
    else:
        for alert in latest_alerts:
            severity = alert.get("severity", "INFO")
            with st.container(border=True):
                st.markdown(f"**{alert.get('type')}**")
                st.caption(
                    f"{alert.get('module', 'unknown')} | {severity} | {alert.get('timestamp', '')}"
                )

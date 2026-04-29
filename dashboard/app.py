"""
Main Streamlit Application Entry Point.
"""

import json
import os

import httpx
import streamlit as st

from dashboard.components.css_injector import inject_custom_css
from dashboard.components.ws_client import get_or_create_event_queue, start_websocket_thread

API_URL = os.getenv("IRMDS_API_URL", "http://127.0.0.1:8000").rstrip("/")

# ─────────────────────────────────────────────────────────────
# 1. Page Configuration
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="IRMDS | Real-Time Anomaly Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Injects the dark mode, glassmorphism, and hides Streamlit headers
inject_custom_css()

# ─────────────────────────────────────────────────────────────
# 2. State & Background Threads
# ─────────────────────────────────────────────────────────────
get_or_create_event_queue()
start_websocket_thread()

# Auto-refresh timer to keep UI synced with the background WebSocket thread
# In Streamlit 1.30+, st_autorefresh or similar patterns are common, but
# we can use the native fragment/rerun or just rely on user interaction +
# a slight manual refresh hook if needed. For now, we will add a small
# refresh button in the sidebar, or pages can poll.
# In a true edge production setting, st.rerun() in a loop works, but can flicker.

# ─────────────────────────────────────────────────────────────
# 3. Sidebar Navigation & Global State
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        "<h2 style='text-align: center; color: white; tracking: 2px;'>🛡️ IRMDS</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align: center; color: #8b949e; font-size: 0.8em; margin-bottom: 2rem;'>Intelligent Real-Time Monitoring</p>",
        unsafe_allow_html=True,
    )

    status_text = "🟢 Connected" if st.session_state.ws_connected else "🔴 Disconnected"
    st.markdown(f"**WebSocket Status:** {status_text}")

    # We use Streamlit 1.30+ native multi-page apps (the `pages/` folder).
    st.markdown("---")
    st.markdown("### Navigation")

    st.page_link("app.py", label="Overview", icon="📊")
    st.page_link("pages/01_visual.py", label="Visual Detection", icon="👁️")
    # st.page_link("pages/02_network.py", label="Network Monitor", icon="🌐")
    # st.page_link("pages/03_finance.py", label="Financial Engine", icon="📈")
    # st.page_link("pages/04_infra.py", label="Infrastructure", icon="🖥️")

# ─────────────────────────────────────────────────────────────
# 4. Main Index Page Logic (Fallback if hit directly)
# ─────────────────────────────────────────────────────────────

# Fetch high-level API status
try:
    health_res = httpx.get(f"{API_URL}/health", timeout=2)
    api_status = health_res.status_code == 200
except Exception:
    api_status = False

st.title("System Overview")

if not api_status:
    st.error(
        "FastAPI Backend is unreachable. Please start the backend (`irmds start`) to view the dashboard."
    )
    st.stop()

# Actually, the user should be automatically routed to 01_overview.py or we can render overview here
# To keep it clean, we will just render the overview logic here instead of a separate 01_overview.py
# Or we can just import it. Let's build the overview right here.

col1, col2, col3 = st.columns(3)

# Fetch latest metrics
try:
    metrics_res = httpx.get(f"{API_URL}/metrics").json()
    uptime = metrics_res.get("system_uptime_seconds", 0)
    uptime_hrs = uptime / 3600
    uptime_str = f"{uptime_hrs:.1f}h" if uptime_hrs > 1 else f"{uptime / 60:.1f}m"
    running_modules = len(metrics_res.get("modules", []))
except Exception:
    uptime_str = "Error"
    running_modules = 0

with col1:
    st.metric(label="System Uptime", value=uptime_str, delta="Online", delta_color="normal")

with col2:
    st.metric(label="Active Modules", value=f"{running_modules}/4", delta="Running")

with col3:
    st.metric(label="Events Processed", value=len(st.session_state.event_queue), delta="Live")

st.markdown("### Real-Time Alert Feed")

st.markdown('<div class="live-feed-container">', unsafe_allow_html=True)
if not st.session_state.event_queue:
    st.markdown(
        "<p style='color: #8b949e; text-align: center; padding: 20px;'>Waiting for events from EventBus...</p>",
        unsafe_allow_html=True,
    )
else:
    for evt in st.session_state.event_queue:
        sev = evt.get("severity", "INFO")
        time_str = evt.get("timestamp", "")
        # Parse timestamp to just time if possible to make it compact
        if "T" in time_str:
            time_str = time_str.split("T")[1][:8]

        color_class = f"alert-severity-{sev}"
        text = f"[{time_str}] <span class='{color_class}'>[{sev}]</span> <b>{evt.get('module')}</b>: {evt.get('type')}"
        if evt.get("data"):
            text += f" <span style='color: #8b949e;'>| {json.dumps(evt.get('data'))}</span>"

        st.markdown(f"<div class='alert-entry'>{text}</div>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

"""
Visual Pipeline Dashboard Page.
"""

import httpx
import streamlit as st

from dashboard.components.chart_builders import build_gauge_chart, build_occupancy_bar, build_sparkline
from dashboard.components.css_injector import inject_custom_css

st.set_page_config(page_title="IRMDS | Visual Engine", layout="wide")
inject_custom_css()

st.title("👁️ Visual Anomaly Engine")

# Fetch latest visual metrics
try:
    metrics_res = httpx.get("http://127.0.0.1:8000/metrics/visual", timeout=2)
    api_online = metrics_res.status_code == 200
    if api_online:
        v_metrics = metrics_res.json().get("metrics", {})
    else:
        v_metrics = {}
except Exception:
    api_online = False
    v_metrics = {}

if not api_online:
    st.warning("Visual Module is currently offline. Start it via the API to view live telemetry.")
    st.stop()


# ─────────────────────────────────────────────────────────────
# Live Analytics Row
# ─────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)

# Real time stats extracted from the backend metrics dictionary
active_tracks = v_metrics.get("active_tracks", 0)
latency = v_metrics.get("latency_ms", 0)
avg_speed = v_metrics.get("avg_speed_ms", 0.0)
loiter_alerts = v_metrics.get("loiter_alerts", 0)
zone_counts = v_metrics.get("zone_occupancy", {"Entry_Gate": 2, "Lobby": 5}) # fallback demo data if empty

with col1:
    st.plotly_chart(
        build_gauge_chart(latency, "Inference Latency", 100, suffix="ms", color="#f2cc60"),
        use_container_width=True,
        config={'displayModeBar': False}
    )

with col2:
    st.plotly_chart(
        build_gauge_chart(avg_speed, "Avg Movement", 5.0, suffix="m/s", color="#58a6ff"),
        use_container_width=True,
        config={'displayModeBar': False}
    )

with col3:
    st.metric("Active Tracks", value=active_tracks, delta=f"{loiter_alerts} Loitering", delta_color="inverse")
    st.write("")
    st.metric("System Load", value="Nominal", delta="YOLOv8-Nano")


# ─────────────────────────────────────────────────────────────
# Dynamic Charts & Feed
# ─────────────────────────────────────────────────────────────
st.markdown("---")
c1, c2 = st.columns((2, 1))

with c1:
    st.markdown("### Real-Time Velocity Variance")
    # For a real stream, we'd store a rolling window in st.session_state
    # Because we're polling /metrics instantly, we simulate a small timeline based on event history
    
    # We will grab history of SPEED metrics if available, otherwise just mock a history
    if "speed_history" not in st.session_state:
        st.session_state.speed_history = [0]*30
    
    st.session_state.speed_history.append(avg_speed)
    st.session_state.speed_history = st.session_state.speed_history[-30:]
    
    st.plotly_chart(
        build_sparkline(list(range(30)), st.session_state.speed_history, "Population Velocity (m/s)"),
        use_container_width=True,
        config={'displayModeBar': False}
    )

with c2:
    st.markdown("### Zone Analytics")
    st.plotly_chart(
        build_occupancy_bar(zone_counts),
        use_container_width=True,
        config={'displayModeBar': False}
    )

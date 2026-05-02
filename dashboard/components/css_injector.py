"""
Premium "Deep Space" CSS Injector for IRMDS Dashboard.

Applies a high-fidelity, glassmorphic aesthetic with glowing accents,
custom animations, and refined typography.
"""

import streamlit as st


def inject_custom_css():
    """Injects premium CSS into the Streamlit app."""

    css = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    :root {
        --bg-deep: #050508;
        --glass-bg: rgba(17, 17, 25, 0.7);
        --glass-border: rgba(255, 255, 255, 0.1);
        --primary-glow: rgba(0, 243, 255, 0.5);
        --accent-cyan: #00f3ff;
        --accent-violet: #bd00ff;
        --text-main: #e0e0e0;
        --text-dim: #888888;
    }

    /* 1. Global Reset & Background */
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif !important;
        background-color: var(--bg-deep) !important;
        color: var(--text-main) !important;
    }

    .stApp {
        background: radial-gradient(circle at 50% -20%, #1a1a2e 0%, var(--bg-deep) 100%) !important;
    }

    /* Hide Streamlit elements */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    div[data-testid="stDecoration"] {display: none;}

    /* 2. Glassmorphic Cards */
    div[data-testid="stMetric"], div.stForm, .premium-card {
        background: var(--glass-bg) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        border: 1px solid var(--glass-border) !important;
        border-radius: 12px !important;
        padding: 1.5rem !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.8) !important;
        transition: all 0.3s ease !important;
    }

    div[data-testid="stMetric"]:hover {
        border-color: var(--accent-cyan) !important;
        box-shadow: 0 0 20px rgba(0, 243, 255, 0.2) !important;
        transform: translateY(-2px);
    }

    /* 3. Metrics Overhaul */
    div[data-testid="stMetricLabel"] {
        font-family: 'Outfit', sans-serif !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        color: var(--text-dim) !important;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-bottom: 0.5rem;
    }

    div[data-testid="stMetricValue"] {
        font-family: 'Outfit', sans-serif !important;
        font-size: 2.5rem !important;
        font-weight: 700 !important;
        color: #ffffff !important;
        text-shadow: 0 0 10px rgba(255, 255, 255, 0.3);
    }

    /* 4. Sidebar - Elegant Glow */
    section[data-testid="stSidebar"] {
        background-color: rgba(5, 5, 8, 0.95) !important;
        backdrop-filter: blur(10px);
        border-right: 1px solid var(--glass-border) !important;
    }

    /* 5. Custom Control Plane Styling */
    .stButton > button {
        background: linear-gradient(135deg, #00f3ff 0%, #0070f3 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        padding: 0.6rem 1.5rem !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 4px 15px rgba(0, 112, 243, 0.3) !important;
    }

    .stButton > button:hover {
        transform: scale(1.02);
        box-shadow: 0 6px 20px rgba(0, 243, 255, 0.5) !important;
    }

    /* 6. Terminal HUD */
    .live-feed-container {
        max-height: 400px;
        overflow-y: auto;
        background: rgba(0, 0, 0, 0.4);
        border: 1px solid var(--glass-border);
        border-radius: 12px;
        padding: 1rem;
        font-family: 'JetBrains Mono', monospace;
    }

    .alert-entry {
        margin-bottom: 8px;
        padding: 8px;
        border-radius: 6px;
        background: rgba(255, 255, 255, 0.02);
        border-left: 3px solid transparent;
        transition: background 0.2s ease;
    }

    .alert-entry:hover {
        background: rgba(255, 255, 255, 0.05);
    }

    .alert-severity-INFO { border-left-color: var(--accent-cyan); }
    .alert-severity-WARNING { border-left-color: #f5a623; }
    .alert-severity-CRITICAL { border-left-color: #ff0055; box-shadow: inset 50px 0 30px -30px rgba(255, 0, 85, 0.1); }

    /* 7. Typography */
    h1, h2, h3 {
        font-family: 'Outfit', sans-serif !important;
        background: linear-gradient(to bottom right, #fff 30%, #888 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -0.03em !important;
    }

    /* 8. Pulsing Status Indicator */
    .status-pulse {
        width: 10px;
        height: 10px;
        background-color: var(--accent-cyan);
        border-radius: 50%;
        display: inline-block;
        margin-right: 8px;
        box-shadow: 0 0 10px var(--accent-cyan);
        animation: pulse 2s infinite;
    }

    @keyframes pulse {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(0, 243, 255, 0.7); }
        70% { transform: scale(1); box-shadow: 0 0 0 10px rgba(0, 243, 255, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(0, 243, 255, 0); }
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

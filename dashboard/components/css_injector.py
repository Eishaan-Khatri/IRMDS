"""
Minimalist Enterprise CSS Injector for Streamlit Dashboard.

Applies clean, high-contrast, border-driven aesthetic inspired by 
Vercel, GitHub, and Stripe dashboards. Strict layout principles.
"""

import streamlit as st


def inject_custom_css():
    """Injects global CSS into the Streamlit app to apply standard enterprise styling."""
    
    css = """
    <style>
    /* 1. Global Typography & Background */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, system-ui, sans-serif !important;
        background-color: #000000 !important; /* Vercel/Stripe stark black */
        color: #ededed !important;
    }

    /* Solid black background for main app */
    .stApp {
        background: #0a0a0a !important; 
    }

    /* 2. Hide Streamlit Cruft safely */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* 3. Clean Cards (No Glass, No Blur) */
    div[data-testid="stMetric"], div.css-1r6slb0, div.stForm {
        background-color: #111111 !important;
        border: 1px solid #333333 !important;
        border-radius: 6px !important;
        padding: 1.2rem !important;
        box-shadow: none !important;
    }
    
    /* Hover effect is structural, not flashy */
    div[data-testid="stMetric"]:hover {
        border-color: #555555 !important;
    }

    /* metric labels (clean, uppercase) */
    div[data-testid="stMetricLabel"] {
        font-size: 0.75rem !important;
        font-weight: 500 !important;
        color: #888888 !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.5rem;
    }

    /* metric values (big, readable) */
    div[data-testid="stMetricValue"] {
        font-size: 2rem !important;
        font-weight: 600 !important;
        color: #ffffff !important;
        line-height: 1.1 !important;
    }
    
    /* delta indicator */
    div[data-testid="stMetricDelta"] {
        font-size: 0.85rem !important;
        margin-top: 0.25rem;
    }

    /* 4. Sidebar Styling (Minimal) */
    section[data-testid="stSidebar"] {
        background-color: #000000 !important;
        border-right: 1px solid #333333 !important;
    }
    
    /* 5. Terminal Feed (Monospace, Clean) */
    .live-feed-container {
        max-height: 400px;
        overflow-y: auto;
        background-color: #111111;
        border: 1px solid #333333;
        border-radius: 6px;
        padding: 12px;
        font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
        font-size: 0.8rem;
    }
    
    .alert-entry {
        margin-bottom: 4px;
        padding-bottom: 4px;
        border-bottom: 1px solid #222222;
        color: #cccccc;
    }
    
    /* Clean enterprise colors: strict blue, yellow, red */
    .alert-severity-INFO { color: #0070f3; font-weight: 600; }
    .alert-severity-WARNING { color: #f5a623; font-weight: 600; }
    .alert-severity-CRITICAL { color: #ff0000; font-weight: 600; }
    
    /* Standard Flat Scrollbar */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }
    ::-webkit-scrollbar-track {
        background: transparent; 
    }
    ::-webkit-scrollbar-thumb {
        background: #333333; 
        border-radius: 3px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #555555; 
    }

    /* Typography */
    h1, h2, h3 {
        font-weight: 600 !important;
        letter-spacing: -0.02em !important;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

"""
WebSocket client for Streamlit.

Runs an asyncio loop in a background thread to continuously stream events
from the FastAPI backend and sink them into st.session_state so the UI can
render them on a timer.
"""

import asyncio
import json
import threading

import streamlit as st
import websockets
from websockets.exceptions import ConnectionClosed

WS_URL = "ws://127.0.0.1:8000/ws/events"


def get_or_create_event_queue():
    """Ensure the event queue exists in session state."""
    if "event_queue" not in st.session_state:
        st.session_state.event_queue = []
    if "ws_connected" not in st.session_state:
        st.session_state.ws_connected = False
    return st.session_state


async def _ws_consumer_loop(url: str, max_events: int = 100):
    """The async loop that connects to the backend and fetches events."""
    while True:
        try:
            # We connect without filters to get everything for the dashboard
            async with websockets.connect(url) as websocket:
                # Update connection state securely
                if hasattr(st, "session_state"):
                    st.session_state.ws_connected = True
                
                while True:
                    message_str = await websocket.recv()
                    event_data = json.loads(message_str)
                    
                    # Push to session state if it exists
                    if hasattr(st, "session_state") and "event_queue" in st.session_state:
                        # Append to front (newest first)
                        st.session_state.event_queue.insert(0, event_data)
                        # Truncate
                        st.session_state.event_queue = st.session_state.event_queue[:max_events]

        except (ConnectionClosed, OSError, TimeoutError):
            if hasattr(st, "session_state"):
                st.session_state.ws_connected = False
            # Sleep before reconnect attempt
            await asyncio.sleep(2)
        except Exception as e:
            # Catch all to prevent thread death
            await asyncio.sleep(2)


def start_websocket_thread():
    """Mounts the WebSocket consumer in a global background thread.
    
    Streamlit reruns the main script constantly. We only want exactly
    one websocket thread running for the lifetime of this server process.
    """
    
    # We use a primitive way to ensure single instantiation across reruns
    if "ws_thread_started" not in st.session_state:
        st.session_state.ws_thread_started = True
        
        def run_loop():
            # Create a new event loop for this background thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_ws_consumer_loop(WS_URL))
            
        thread = threading.Thread(target=run_loop, daemon=True, name="IRMDS_WS_Thread")
        thread.start()

"""
Integration tests for the FastAPI application endpoints.
"""

import time
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from core.database import AlertRecord, SessionRecord, get_session_factory
from core.event_bus import Event, Severity


@pytest.fixture(scope="module")
def app():
    """Create a FastAPI app for testing."""
    return create_app()


@pytest.fixture(scope="module")
def client(app):
    """Create a TestClient with triggered lifespan (startup/shutdown)."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def clean_db():
    """Clear database tables before each test."""
    SessionFactory = get_session_factory()
    with SessionFactory() as session:
        session.query(AlertRecord).delete()
        session.query(SessionRecord).delete()
        session.commit()


def test_system_root(client: TestClient):
    """Test the root endpoint returns system identity."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["name"] == "IRMDS API"


def test_system_health(client: TestClient):
    """Test health endpoint reports overall status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("healthy", "degraded")
    assert "uptime_seconds" in data
    assert isinstance(data["modules"], list)


def test_list_modules(client: TestClient):
    """Test modules endpoint lists registered plugins."""
    response = client.get("/modules")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    
    # We expect our visual module to be discovered
    module_ids = [m["id"] for m in data]
    assert "visual" in module_ids


@patch("modules.visual.pipeline.VisualPipeline.start")
@patch("modules.visual.pipeline.VisualPipeline.stop")
def test_module_start_stop(mock_stop, mock_start, client: TestClient):
    """Test starting and stopping a module via API."""
    # Simulate successful start/stop returns
    mock_start.return_value = True
    mock_stop.return_value = True

    # Start module
    res = client.post("/modules/visual/start")
    assert res.status_code == 200
    assert res.json()["success"] is True
    assert res.json()["action"] == "start"

    # Stop module
    res = client.post("/modules/visual/stop")
    assert res.status_code == 200
    assert res.json()["success"] is True
    assert res.json()["action"] == "stop"


def test_session_lifecycle(client: TestClient):
    """Test creating and stopping a monitoring session."""
    # Create session
    start_res = client.post("/sessions/start", json={"description": "Test session"})
    assert start_res.status_code == 200
    session_data = start_res.json()
    assert session_data["status"] == "active"
    sess_id = session_data["id"]

    # Try creating another while active (should fail)
    fail_res = client.post("/sessions/start", json={"description": "Another"})
    assert fail_res.status_code == 400

    # Stop session
    stop_res = client.post("/sessions/stop")
    assert stop_res.status_code == 200
    ended_data = stop_res.json()
    assert ended_data["status"] == "completed"
    assert "duration_seconds" in ended_data["summary"]

    # Retrieve session
    get_res = client.get(f"/sessions/{sess_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == sess_id


def test_alerts_pagination(client: TestClient):
    """Test alert retrieval with pagination and filtering."""
    # Insert dummy alerts into the DB
    SessionFactory = get_session_factory()
    with SessionFactory() as session:
        for i in range(15):
            alert = AlertRecord(
                id=f"alert_{i}",
                timestamp=str(time.time() - i),
                module="visual",
                type="SPEED_ANOMALY" if i % 2 == 0 else "LOITERING",
                severity="CRITICAL" if i % 2 == 0 else "WARNING",
                data={"test": True}
            )
            session.add(alert)
        session.commit()

    # Get page 1 (default limit 50)
    res = client.get("/alerts")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 15
    assert len(data["items"]) == 15

    # Test limit and offset
    res2 = client.get("/alerts?limit=5&offset=5")
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["total"] == 15
    assert len(data2["items"]) == 5
    assert data2["page"] == 2

    # Test filtering by type
    res3 = client.get("/alerts?type=SPEED_ANOMALY")
    data3 = res3.json()
    assert all(item["type"] == "SPEED_ANOMALY" for item in data3["items"])


def test_websocket_event_streaming(client: TestClient, app):
    """Test real-time event pushing over WebSockets."""
    # Connect via websocket
    with client.websocket_connect("/ws/events?min_severity=WARNING") as websocket:
        
        # Publish a dummy event to the EventBus directly
        event_bus = app.state.event_bus
        test_event = Event(
            module="network",
            type="PORT_SCAN",
            severity=Severity.CRITICAL,
            data={"ip": "192.168.1.100"}
        )
        
        # We must give the async loop a moment to drain the sync queue thread callback
        # Because we're in a synchronous TestClient, we simulate the thread publishing
        event_bus.publish(test_event)

        # Receive from websocket
        data = websocket.receive_json()
        assert data["id"] == test_event.id
        assert data["module"] == "network"
        assert data["type"] == "PORT_SCAN"
        assert data["severity"] == "CRITICAL"

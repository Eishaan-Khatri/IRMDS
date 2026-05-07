"""Tests for dashboard API client helpers."""

from __future__ import annotations

import httpx

from dashboard.components import api_client


class FakeResponse:
    def __init__(self, status_code: int, payload=None, text: str = ""):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.text = text

    def json(self):
        return self._payload


def test_get_json_returns_payload(monkeypatch):
    """Dashboard GET helper should return JSON payloads for HTTP 200."""

    def fake_get(url, params=None, timeout=3.0):
        assert url == "http://api.test/health"
        assert params is None
        assert timeout == 3.0
        return FakeResponse(200, {"status": "healthy"})

    monkeypatch.setattr(api_client.httpx, "get", fake_get)

    data, error = api_client.get_json("http://api.test", "/health")

    assert data == {"status": "healthy"}
    assert error is None


def test_get_json_returns_http_error(monkeypatch):
    """Dashboard GET helper should surface non-200 responses."""

    def fake_get(url, params=None, timeout=3.0):
        return FakeResponse(503, text="offline")

    monkeypatch.setattr(api_client.httpx, "get", fake_get)

    data, error = api_client.get_json("http://api.test", "/health")

    assert data == {}
    assert error == "HTTP 503: offline"


def test_get_json_returns_connection_error(monkeypatch):
    """Dashboard GET helper should not raise connection failures into Streamlit."""

    def fake_get(url, params=None, timeout=3.0):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(api_client.httpx, "get", fake_get)

    data, error = api_client.get_json("http://api.test", "/health")

    assert data == {}
    assert "connection refused" in str(error)


def test_post_json_returns_payload(monkeypatch):
    """Dashboard POST helper should return JSON payloads for HTTP 200."""

    def fake_post(url, json=None, timeout=5.0):
        assert url == "http://api.test/commands"
        assert json == {"dry_run": True}
        assert timeout == 5.0
        return FakeResponse(200, {"status": "accepted"})

    monkeypatch.setattr(api_client.httpx, "post", fake_post)

    data, error = api_client.post_json("http://api.test", "/commands", {"dry_run": True})

    assert data == {"status": "accepted"}
    assert error is None

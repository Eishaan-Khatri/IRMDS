"""Small API helpers for the Streamlit dashboard."""

from __future__ import annotations

from typing import Any

import httpx


def get_json(
    api_url: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    timeout: float = 3.0,
) -> tuple[Any, str | None]:
    """Fetch JSON from the API and return data plus an optional error."""
    try:
        response = httpx.get(f"{api_url.rstrip('/')}{path}", params=params, timeout=timeout)
        if response.status_code != 200:
            return {}, f"HTTP {response.status_code}: {response.text}"
        return response.json(), None
    except Exception as exc:  # noqa: BLE001 - dashboard should render connection errors.
        return {}, str(exc)


def post_json(
    api_url: str,
    path: str,
    payload: dict[str, Any] | None = None,
    *,
    timeout: float = 5.0,
) -> tuple[Any, str | None]:
    """Post JSON to the API and return data plus an optional error."""
    try:
        response = httpx.post(f"{api_url.rstrip('/')}{path}", json=payload, timeout=timeout)
        if response.status_code != 200:
            return {}, f"HTTP {response.status_code}: {response.text}"
        return response.json(), None
    except Exception as exc:  # noqa: BLE001 - dashboard should render connection errors.
        return {}, str(exc)

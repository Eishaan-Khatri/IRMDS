"""
IRMDS one-command local demo.

This script starts a sample-safe demo stack without requiring a webcam, YOLO
weights, or real hardware. It launches the FastAPI backend, optionally launches
the Streamlit dashboard, starts sample-friendly modules, and proposes one
dry-run command so the command ledger has visible activity.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _request_json(
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
    timeout: float = 5.0,
) -> dict[str, Any]:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
    return json.loads(body) if body else {}


def _wait_for_api(base_url: str, timeout_seconds: float = 30.0) -> None:
    deadline = time.time() + timeout_seconds
    last_error: Exception | None = None

    while time.time() < deadline:
        try:
            _request_json("GET", f"{base_url}/health", timeout=2.0)
            return
        except Exception as exc:  # noqa: BLE001 - report final connection issue.
            last_error = exc
            time.sleep(0.5)

    raise RuntimeError(f"API did not become healthy at {base_url}: {last_error}")


def _wait_for_url(url: str, timeout_seconds: float = 30.0) -> None:
    """Wait until a URL responds successfully."""
    deadline = time.time() + timeout_seconds
    last_error: Exception | None = None

    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2.0) as response:
                if response.status < 500:
                    return
        except Exception as exc:  # noqa: BLE001 - report final connection issue.
            last_error = exc
        time.sleep(0.5)

    raise RuntimeError(f"URL did not become reachable at {url}: {last_error}")


def _start_process(command: list[str], env: dict[str, str]) -> subprocess.Popen:
    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    return subprocess.Popen(command, cwd=ROOT, env=env, creationflags=creationflags)


def _stop_processes(processes: list[subprocess.Popen]) -> None:
    for proc in processes:
        if proc.poll() is None:
            try:
                if os.name == "nt":
                    proc.terminate()
                else:
                    proc.send_signal(signal.SIGTERM)
            except Exception:
                proc.terminate()

    for proc in processes:
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            proc.kill()


def _start_modules(base_url: str, modules: list[str]) -> None:
    discovered = _request_json("GET", f"{base_url}/modules")
    discovered_ids = {item["id"] for item in discovered}
    print(f"[demo] discovered modules: {', '.join(sorted(discovered_ids))}")

    for module_id in modules:
        if module_id not in discovered_ids:
            print(f"[demo] skip missing module: {module_id}")
            continue

        try:
            _request_json("POST", f"{base_url}/modules/{module_id}/start")
            print(f"[demo] started module: {module_id}")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            print(f"[demo] module {module_id} did not start: HTTP {exc.code} {body}")
        except Exception as exc:  # noqa: BLE001 - demo should keep going.
            print(f"[demo] module {module_id} did not start: {exc}")


def _seed_command(base_url: str) -> None:
    payload = {
        "action": "SET_MAINTENANCE_MODE",
        "target_device": "demo_line_01",
        "payload": {"reason": "sample demo command"},
        "dry_run": True,
    }
    proposed = _request_json("POST", f"{base_url}/commands", payload)
    command_id = proposed["command"]["id"]
    _request_json("POST", f"{base_url}/commands/{command_id}/approve")
    print(f"[demo] proposed and approved dry-run command: {command_id}")


def _wait_for_demo_surfaces(base_url: str, timeout_seconds: float = 15.0) -> None:
    """Wait until the dashboard's core API surfaces have useful demo data."""
    deadline = time.time() + timeout_seconds
    last_error: Exception | None = None

    while time.time() < deadline:
        try:
            modules = _request_json("GET", f"{base_url}/modules")
            metrics = _request_json("GET", f"{base_url}/metrics")
            commands = _request_json("GET", f"{base_url}/commands?limit=5")
            _request_json("GET", f"{base_url}/alerts/latest?limit=5")

            if modules and metrics.get("modules") and commands.get("commands"):
                print("[demo] dashboard data surfaces ready: modules, metrics, commands, alerts")
                return
        except Exception as exc:  # noqa: BLE001 - report final readiness issue.
            last_error = exc
        time.sleep(0.5)

    raise RuntimeError(f"Demo data surfaces did not become ready: {last_error}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the IRMDS sample demo stack.")
    parser.add_argument("--api-host", default="127.0.0.1", help="Host used for local API URL.")
    parser.add_argument("--api-bind", default="0.0.0.0", help="Host uvicorn binds to.")
    parser.add_argument("--api-port", type=int, default=8000, help="FastAPI port.")
    parser.add_argument("--dashboard-port", type=int, default=8501, help="Streamlit dashboard port.")
    parser.add_argument(
        "--modules",
        default="network,timeseries,infrastructure",
        help="Comma-separated modules to auto-start. Visual is opt-in.",
    )
    parser.add_argument(
        "--with-visual",
        action="store_true",
        help="Also attempt to start the visual module. Requires camera/video/model availability.",
    )
    parser.add_argument("--no-dashboard", action="store_true", help="Start API only.")
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Start, probe, seed one command, then shut down instead of staying attached.",
    )
    return parser.parse_args()


def main() -> int:
    from scripts.generate_sample_data import main as generate_sample_data

    args = parse_args()
    base_url = f"http://{args.api_host}:{args.api_port}"
    processes: list[subprocess.Popen] = []

    print("[demo] generating deterministic sample data")
    generate_sample_data()

    env = os.environ.copy()
    env.setdefault("IRMDS_DATABASE_URL", "sqlite:///data/irmds_demo.db")
    env.setdefault("IRMDS_NETWORK_BASELINE_WINDOWS", "5")
    env.setdefault("IRMDS_FINANCE_REPLAY_SPEED", "1000")
    env.setdefault("IRMDS_INFRA_POLL_INTERVAL", "1.0")
    env.setdefault("IRMDS_API_URL", base_url)
    env.setdefault("IRMDS_DEMO_MODE", "true")

    api_command = [
        sys.executable,
        "-m",
        "uvicorn",
        "api.main:irmds_api",
        "--host",
        args.api_bind,
        "--port",
        str(args.api_port),
    ]
    print(f"[demo] starting API: {base_url}")
    processes.append(_start_process(api_command, env))

    try:
        _wait_for_api(base_url)

        modules = [item.strip() for item in args.modules.split(",") if item.strip()]
        if args.with_visual and "visual" not in modules:
            modules.append("visual")
        _start_modules(base_url, modules)
        _seed_command(base_url)
        _wait_for_demo_surfaces(base_url)

        if not args.no_dashboard:
            dashboard_url = f"http://127.0.0.1:{args.dashboard_port}"
            dashboard_command = [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                "dashboard/app.py",
                "--global.developmentMode=false",
                "--server.address",
                "0.0.0.0",
                "--server.port",
                str(args.dashboard_port),
            ]
            print(f"[demo] starting dashboard: {dashboard_url}")
            processes.append(_start_process(dashboard_command, env))
            _wait_for_url(dashboard_url)

        print("[demo] API docs:      " + f"{base_url}/docs")
        print("[demo] health:        " + f"{base_url}/health")
        if not args.no_dashboard:
            print("[demo] dashboard:     " + dashboard_url)
        print("[demo] press Ctrl+C to stop")

        if args.smoke:
            time.sleep(2)
            return 0

        while True:
            for proc in processes:
                if proc.poll() is not None:
                    raise RuntimeError(f"demo process exited early with code {proc.returncode}")
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[demo] stopping")
        return 0
    finally:
        _stop_processes(processes)


if __name__ == "__main__":
    raise SystemExit(main())

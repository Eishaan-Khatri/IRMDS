"""Tests for the IRMDS Typer CLI."""

from __future__ import annotations

from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()


def test_cli_version():
    """`irmds version` should print the package version."""
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert "IRMDS 0.1.0" in result.output


def test_cli_demo_builds_expected_command(monkeypatch):
    """`irmds demo` should delegate to scripts/demo.py with selected flags."""
    captured = {}

    def fake_call(command, cwd=None):
        captured["command"] = command
        captured["cwd"] = cwd
        return 0

    monkeypatch.setattr("cli.main.subprocess.call", fake_call)

    result = runner.invoke(
        app,
        [
            "demo",
            "--smoke",
            "--no-dashboard",
            "--with-visual",
            "--api-port",
            "8780",
            "--dashboard-port",
            "8580",
        ],
    )

    assert result.exit_code == 0
    command = [str(part) for part in captured["command"]]
    assert command[1].endswith("scripts\\demo.py") or command[1].endswith("scripts/demo.py")
    assert "--smoke" in command
    assert "--no-dashboard" in command
    assert "--with-visual" in command
    assert command[-4:] == ["--api-port", "8780", "--dashboard-port", "8580"]


def test_cli_demo_returns_subprocess_exit_code(monkeypatch):
    """`irmds demo` should return the demo subprocess exit code."""

    def fake_call(command, cwd=None):
        return 7

    monkeypatch.setattr("cli.main.subprocess.call", fake_call)

    result = runner.invoke(app, ["demo", "--smoke"])

    assert result.exit_code == 7

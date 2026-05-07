"""Tests for the local demo entry point."""

from __future__ import annotations

import builtins
from types import SimpleNamespace

from scripts import demo


def test_demo_reports_missing_dependency(monkeypatch, capsys):
    """Missing demo dependencies should produce setup guidance, not a traceback."""
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "scripts.generate_sample_data":
            raise ModuleNotFoundError("No module named 'numpy'", name="numpy")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.setattr(demo, "parse_args", lambda: SimpleNamespace())

    result = demo.main()

    captured = capsys.readouterr()
    assert result == 2
    assert "missing Python dependency: numpy" in captured.err
    assert "python -m pip install -r requirements.txt -r requirements-dev.txt" in captured.err
    assert ".\\.venv\\Scripts\\python.exe scripts\\demo.py --smoke --no-dashboard" in captured.err


def test_demo_reports_incompatible_dependency_wheel(monkeypatch, capsys):
    """Binary dependency ABI mismatches should point users at Python 3.12."""
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "scripts.generate_sample_data":
            raise ImportError("compiled module is incompatible with cpython-314")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.setattr(demo, "parse_args", lambda: SimpleNamespace())

    result = demo.main()

    captured = capsys.readouterr()
    assert result == 2
    assert "Python dependency import failed" in captured.err
    assert "installed for a different Python version" in captured.err
    assert "py -3.12 -m venv .venv" in captured.err

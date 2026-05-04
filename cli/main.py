"""Command-line interface for IRMDS."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import typer

app = typer.Typer(
    name="irmds",
    help="IRMDS command-line tools for local development and demos.",
    no_args_is_help=True,
)


@app.command()
def version() -> None:
    """Print the current IRMDS package version."""
    typer.echo("IRMDS 0.1.0")


@app.command()
def demo(
    no_dashboard: bool = typer.Option(False, help="Start only the API demo."),
    with_visual: bool = typer.Option(
        False,
        help="Attempt to start the visual module. Requires camera/video/model availability.",
    ),
    smoke: bool = typer.Option(False, help="Run a short smoke demo and exit."),
    api_port: int = typer.Option(8000, help="FastAPI demo port."),
    dashboard_port: int = typer.Option(8501, help="Streamlit demo port."),
) -> None:
    """Run the sample-safe local demo stack."""
    root = Path(__file__).resolve().parents[1]
    command = [sys.executable, str(root / "scripts" / "demo.py")]

    if no_dashboard:
        command.append("--no-dashboard")
    if with_visual:
        command.append("--with-visual")
    if smoke:
        command.append("--smoke")
    command.extend(["--api-port", str(api_port), "--dashboard-port", str(dashboard_port)])

    raise typer.Exit(subprocess.call(command, cwd=root))


if __name__ == "__main__":
    app()

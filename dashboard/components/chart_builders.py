"""
Premium Plotly chart builders for the IRMDS dashboard.
"""

from typing import Any

import plotly.graph_objects as go


def get_dark_layout(title: str = "") -> dict[str, Any]:
    """Return a transparent layout scheme for Plotly."""
    return dict(
        title=title,
        paper_bgcolor="rgba(0,0,0,0)",  # Fully transparent
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#888888", family="Outfit, sans-serif"),
        margin=dict(l=20, r=20, t=40 if title else 20, b=20),
        xaxis=dict(showgrid=False, zeroline=False, visible=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", zeroline=False),
    )


def build_gauge_chart(
    value: float,
    title: str,
    max_val: float,
    suffix: str = "",
    color: str = "#00f3ff",
) -> go.Figure:
    """Build a circular gauge chart."""
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            title={
                "text": title,
                "font": {"size": 14, "color": "#888", "family": "Outfit"},
            },
            number={
                "suffix": suffix,
                "font": {
                    "size": 36,
                    "color": "white",
                    "weight": "bold",
                    "family": "Outfit",
                },
            },
            gauge={
                "axis": {"range": [0, max_val], "visible": False},
                "bar": {"color": color},
                "bgcolor": "rgba(255,255,255,0.05)",
                "borderwidth": 0,
            },
        )
    )
    fig.update_layout(**get_dark_layout(), height=200)
    return fig


def build_sparkline(
    x_data: list[Any],
    y_data: list[Any],
    title: str,
    color: str = "#00f3ff",
) -> go.Figure:
    """Build a sleek sparkline chart for real-time streaming data."""
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=x_data,
            y=y_data,
            mode="lines",
            line=dict(color=color, width=3, shape="spline"),
            fill="tozeroy",
            fillcolor="rgba(0, 243, 255, 0.1)",
        )
    )

    layout = get_dark_layout(title)
    # Tweak axes for sparkline look
    layout["yaxis"]["visible"] = False
    fig.update_layout(**layout, height=150)
    return fig


def build_occupancy_bar(zones: dict[str, int]) -> go.Figure:
    """Build a horizontal bar chart showing zone occupancy."""
    if not zones:
        fig = go.Figure()
        fig.update_layout(**get_dark_layout("Zone Occupancy"), height=200)
        return fig

    names = list(zones.keys())
    counts = list(zones.values())

    fig = go.Figure(
        go.Bar(
            x=counts,
            y=names,
            orientation="h",
            marker=dict(
                color=counts,
                colorscale=[
                    [0, "rgba(0, 243, 255, 0.2)"],
                    [1, "rgba(0, 243, 255, 0.8)"],
                ],
                line=dict(width=0),
            ),
        )
    )

    layout = get_dark_layout("Zone Occupancy")
    layout["xaxis"]["visible"] = True
    layout["xaxis"]["gridcolor"] = "rgba(255,255,255,0.05)"
    fig.update_layout(**layout, height=250)
    return fig

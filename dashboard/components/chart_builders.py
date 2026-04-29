"""
Plotly chart builders for the IRMDS dashboard.

Generates beautiful, dark-mode native Plotly figures for Streamlit injection.
"""

import plotly.graph_objects as go


def get_dark_layout(title: str = "") -> dict:
    """Returns a universal dark-mode layout scheme for Plotly."""
    return dict(
        title=title,
        paper_bgcolor="#0a0a0a",  # Solid black/dark background matching Vercel theme
        plot_bgcolor="#0a0a0a",
        font=dict(color="#888888", family="Inter, -apple-system, system-ui, sans-serif"),
        margin=dict(l=20, r=20, t=40 if title else 20, b=20),
        xaxis=dict(showgrid=False, zeroline=False, visible=False),
        yaxis=dict(showgrid=True, gridcolor="#333333", zeroline=False),
    )


def build_gauge_chart(
    value: float, title: str, max_val: float, suffix: str = "", color: str = "#58a6ff"
):
    """Build a premium circular gauge chart."""
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            title={"text": title, "font": {"size": 14, "color": "#8b949e"}},
            number={"suffix": suffix, "font": {"size": 36, "color": "white", "weight": "bold"}},
            gauge={
                "axis": {"range": [0, max_val], "visible": False},
                "bar": {"color": color},
                "bgcolor": "#111111",
                "borderwidth": 0,
            },
        )
    )
    fig.update_layout(**get_dark_layout(), height=200)
    return fig


def build_sparkline(x_data: list, y_data: list, title: str, color: str = "#3fb950"):
    """Build a sleek sparkline chart for real-time streaming data."""
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=x_data, y=y_data, mode="lines", line=dict(color=color, width=2, shape="spline")
        )
    )

    layout = get_dark_layout(title)
    # Tweak axes for sparkline look
    layout["yaxis"]["visible"] = False
    fig.update_layout(**layout, height=150)
    return fig


def build_occupancy_bar(zones: dict):
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
            marker=dict(color=counts, colorscale="Blues", line=dict(width=0)),
        )
    )

    layout = get_dark_layout("Zone Occupancy")
    layout["xaxis"]["visible"] = True
    layout["xaxis"]["gridcolor"] = "#333333"
    fig.update_layout(**layout, height=250)
    return fig

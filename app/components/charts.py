from datetime import datetime
from typing import Any, Dict, List, Optional
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Chart Theme Palette
COLOR_VIB = "#38bdf8"    # Sky Blue
COLOR_TEMP = "#f43f5e"   # Rose Red
COLOR_RPM = "#a855f7"    # Purple
COLOR_CURR = "#f59e0b"   # Amber
COLOR_OEE = "#10b981"    # Emerald
COLOR_GRID = "#1e293b"
COLOR_PLOT_BG = "#0f172a"
COLOR_PAPER_BG = "#151e2e"

def render_sensor_telemetry_chart(
    df: pd.DataFrame,
    predicted_window_start: Optional[datetime] = None,
    predicted_window_end: Optional[datetime] = None,
    replay_ts: Optional[datetime] = None
) -> go.Figure:
    """
    Renders 4 synchronized sensor subplots (Vibration, Temperature, RPM, Motor Current)
    with shaded predicted failure window and vertical replay clock line.
    """
    fig = make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.06,
        subplot_titles=(
            "Vibration (mm/s) — ISO 10816 Velocity",
            "Temperature (°C) — Bearing & Housing",
            "Operating Speed (RPM)",
            "Motor Current (A)"
        )
    )

    if df.empty:
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor=COLOR_PAPER_BG,
            plot_bgcolor=COLOR_PLOT_BG,
            height=600,
            title_text="No telemetry readings available for the selected window"
        )
        return fig

    # 1. Vibration
    fig.add_trace(
        go.Scatter(
            x=df["ts"],
            y=df["vibration_mm_s"],
            name="Vibration",
            line=dict(color=COLOR_VIB, width=2),
            hovertemplate="%{y:.2f} mm/s<extra></extra>"
        ),
        row=1, col=1
    )
    # Baseline threshold line for vibration
    fig.add_hline(y=4.5, line_dash="dot", line_color="#fda4af", row=1, col=1, annotation_text="ISO Warning (4.5 mm/s)")

    # 2. Temperature
    fig.add_trace(
        go.Scatter(
            x=df["ts"],
            y=df["temperature_c"],
            name="Temperature",
            line=dict(color=COLOR_TEMP, width=2),
            hovertemplate="%{y:.1f} °C<extra></extra>"
        ),
        row=2, col=1
    )
    fig.add_hline(y=80.0, line_dash="dot", line_color="#fda4af", row=2, col=1, annotation_text="Thermal Alert (80°C)")

    # 3. RPM
    fig.add_trace(
        go.Scatter(
            x=df["ts"],
            y=df["rpm"],
            name="RPM",
            line=dict(color=COLOR_RPM, width=2),
            hovertemplate="%{y:.0f} RPM<extra></extra>"
        ),
        row=3, col=1
    )

    # 4. Motor Current
    fig.add_trace(
        go.Scatter(
            x=df["ts"],
            y=df["motor_current_a"],
            name="Current",
            line=dict(color=COLOR_CURR, width=2),
            hovertemplate="%{y:.1f} A<extra></extra>"
        ),
        row=4, col=1
    )

    # Shaded failure window across all subplots
    if predicted_window_start and predicted_window_end:
        for r in range(1, 5):
            fig.add_vrect(
                x0=predicted_window_start,
                x1=predicted_window_end,
                fillcolor="rgba(244, 63, 94, 0.18)",
                layer="below",
                line_width=1,
                line_color="rgba(244, 63, 94, 0.6)",
                annotation_text="Predicted Failure Window" if r == 1 else None,
                annotation_position="top left",
                row=r, col=1
            )

    # Replay clock marker
    if replay_ts:
        for r in range(1, 5):
            fig.add_vline(
                x=replay_ts,
                line_width=2,
                line_dash="dash",
                line_color="#38bdf8",
                annotation_text="Replay Clock (As-Of)" if r == 1 else None,
                annotation_position="bottom right",
                row=r, col=1
            )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=COLOR_PAPER_BG,
        plot_bgcolor=COLOR_PLOT_BG,
        height=680,
        margin=dict(l=50, r=30, t=40, b=40),
        hovermode="x unified",
        showlegend=False
    )
    fig.update_xaxes(showgrid=True, gridcolor=COLOR_GRID)
    fig.update_yaxes(showgrid=True, gridcolor=COLOR_GRID)

    return fig

def render_oee_trend_chart(df: pd.DataFrame) -> go.Figure:
    """Renders OEE trend with Availability, Performance, Quality, and overall OEE."""
    fig = go.Figure()
    if df.empty:
        fig.update_layout(template="plotly_dark", paper_bgcolor=COLOR_PAPER_BG, plot_bgcolor=COLOR_PLOT_BG, height=350)
        return fig

    # Group if multiple plants/lines
    if "group_name" in df.columns and df["group_id"].nunique() > 1:
        for grp in df["group_name"].unique():
            sub = df[df["group_name"] == grp]
            fig.add_trace(
                go.Scatter(
                    x=sub["period_start"],
                    y=sub["oee"] * 100.0,
                    mode="lines+markers",
                    name=str(grp),
                    line=dict(width=2.5),
                    hovertemplate=f"<b>{grp}</b>: %{{y:.1f}}%<extra></extra>"
                )
            )
    else:
        # APQ Component Breakdown
        fig.add_trace(
            go.Bar(
                x=df["period_start"],
                y=df["availability"] * 100.0,
                name="Availability",
                marker_color="rgba(56, 189, 248, 0.7)",
                hovertemplate="Availability: %{y:.1f}%<extra></extra>"
            )
        )
        fig.add_trace(
            go.Bar(
                x=df["period_start"],
                y=df["performance"] * 100.0,
                name="Performance",
                marker_color="rgba(168, 85, 247, 0.7)",
                hovertemplate="Performance: %{y:.1f}%<extra></extra>"
            )
        )
        fig.add_trace(
            go.Bar(
                x=df["period_start"],
                y=df["quality"] * 100.0,
                name="Quality",
                marker_color="rgba(245, 158, 11, 0.7)",
                hovertemplate="Quality: %{y:.1f}%<extra></extra>"
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df["period_start"],
                y=df["oee"] * 100.0,
                name="Overall OEE",
                mode="lines+markers",
                line=dict(color=COLOR_OEE, width=3),
                hovertemplate="<b>Fleet OEE: %{y:.1f}%</b><extra></extra>"
            )
        )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=COLOR_PAPER_BG,
        plot_bgcolor=COLOR_PLOT_BG,
        barmode="group",
        height=380,
        margin=dict(l=40, r=30, t=30, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis=dict(title="Percentage (%)", range=[50, 105], gridcolor=COLOR_GRID),
        xaxis=dict(gridcolor=COLOR_GRID)
    )
    return fig

def render_top_signals_chart(signals: List[Dict[str, Any]]) -> go.Figure:
    """Renders a horizontal bar chart of top anomaly signals and contribution."""
    fig = go.Figure()
    if not signals:
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor=COLOR_PAPER_BG,
            plot_bgcolor=COLOR_PLOT_BG,
            height=200,
            title_text="No anomaly signals detected"
        )
        return fig

    labels = [s.get("signal", "Signal") for s in signals]
    values = [s.get("contribution", 0.5) * 100.0 for s in signals]
    colors = ["#f43f5e" if s.get("direction") == "+" else "#38bdf8" for s in signals]

    fig.add_trace(
        go.Bar(
            y=labels,
            x=values,
            orientation="h",
            marker=dict(color=colors, line=dict(color="#1e293b", width=1)),
            hovertemplate="%{y}: %{x:.1f}% contribution<extra></extra>"
        )
    )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=COLOR_PAPER_BG,
        plot_bgcolor=COLOR_PLOT_BG,
        height=220,
        margin=dict(l=10, r=20, t=20, b=30),
        xaxis=dict(title="Relative Anomaly Contribution (%)", range=[0, 100], gridcolor=COLOR_GRID),
        yaxis=dict(autorange="reversed")
    )
    return fig

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from plotly.graph_objects import Figure
import numpy as np

from viz_utils import TEAM_COLORS, COMPOUND_COLORS, apply_plot_style


def format_time_axis(seconds_series):
    """Format seconds to MM:SS.mmm for axis labels."""
    if seconds_series.empty:
        return []
    return [f"{int(s//60)}:{s%60:06.3f}" if pd.notna(s) else "" for s in seconds_series]


# Phase 1 visualizers
def plot_lap_trend(df: pd.DataFrame) -> Figure:
    """Plot lap time trend with enhanced styling."""
    if df.empty:
        return go.Figure().add_annotation(
            text="No data available",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
        )

    # Convert lap_duration to seconds if needed
    if "lap_duration" in df.columns:
        df = df.copy()
        if df["lap_duration"].dtype == "object":
            df["lap_duration_seconds"] = df["lap_duration"].apply(
                lambda x: (
                    float(x.split(":")[0]) * 60 + float(x.split(":")[1])
                    if ":" in str(x)
                    else float(x)
                )
            )
        else:
            df["lap_duration_seconds"] = df["lap_duration"]

    fig = px.line(
        df,
        x="lap_number",
        y="lap_duration_seconds",
        title="🏁 Lap Time Trend",
        labels={
            "lap_number": "Lap Number",
            "lap_duration_seconds": "Lap Time (seconds)",
        },
    )

    # Add moving average
    if len(df) > 3:
        df["moving_avg"] = (
            df["lap_duration_seconds"].rolling(window=3, center=True).mean()
        )
        fig.add_scatter(
            x=df["lap_number"],
            y=df["moving_avg"],
            mode="lines",
            name="3-lap moving average",
            line=dict(dash="dash", color="orange"),
        )

    apply_plot_style(fig, showlegend=True)

    return fig


def plot_distribution(df: pd.DataFrame) -> Figure:
    """Plot lap time distribution with statistics."""
    if df.empty:
        return go.Figure().add_annotation(
            text="No data available",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
        )

    # Convert to seconds
    df = df.copy()
    if df["lap_duration"].dtype == "object":
        df["lap_duration_seconds"] = df["lap_duration"].apply(
            lambda x: (
                float(x.split(":")[0]) * 60 + float(x.split(":")[1])
                if ":" in str(x)
                else float(x)
            )
        )
    else:
        df["lap_duration_seconds"] = df["lap_duration"]

    # Filter out outliers
    valid_times = df["lap_duration_seconds"].dropna()
    if valid_times.empty:
        return go.Figure().add_annotation(
            text="No valid lap times",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
        )

    fig = px.histogram(
        df,
        x="lap_duration_seconds",
        nbins=20,
        title="📊 Lap Time Distribution",
        labels={"lap_duration_seconds": "Lap Time (seconds)"},
    )

    # Add statistical lines
    mean_time = valid_times.mean()
    median_time = valid_times.median()

    fig.add_vline(
        x=mean_time,
        line_dash="dash",
        line_color="red",
        annotation_text=f"Mean: {mean_time:.3f}s",
    )
    fig.add_vline(
        x=median_time,
        line_dash="dot",
        line_color="blue",
        annotation_text=f"Median: {median_time:.3f}s",
    )

    apply_plot_style(fig, showlegend=False)
    return fig


def plot_delta(df: pd.DataFrame) -> Figure:
    """Plot lap-by-lap delta vs teammate."""
    if df.empty:
        return go.Figure().add_annotation(
            text="No teammate comparison data",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
        )

    # Create color based on positive/negative delta
    colors = ["red" if x > 0 else "green" for x in df["delta"]]

    fig = go.Figure()
    fig.add_bar(
        x=df["lap_number"], y=df["delta"], marker_color=colors, name="Delta vs Teammate"
    )

    # Add zero line
    fig.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.5)

    fig.update_layout(
        title="⚖️ Lap-by-Lap Delta vs. Teammate",
        xaxis_title="Lap Number",
        yaxis_title="Delta (seconds)",
        annotations=[
            dict(
                text="Faster",
                x=0.02,
                y=0.98,
                xref="paper",
                yref="paper",
                showarrow=False,
                font=dict(color="green"),
            ),
            dict(
                text="Slower",
                x=0.02,
                y=0.02,
                xref="paper",
                yref="paper",
                showarrow=False,
                font=dict(color="red"),
            ),
        ],
    )
    apply_plot_style(fig)

    return fig


# Phase 2 visualizers
def plot_team_comparison(df: pd.DataFrame) -> Figure:
    """Enhanced team comparison with multiple metrics."""
    if df.empty:
        return go.Figure().add_annotation(
            text="No team data available",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
        )

    # Calculate team averages
    team_avg = (
        df.groupby("team_name")
        .agg({"avg_lap": "mean", "fastest_lap": "min", "consistency": "mean"})
        .reset_index()
    )

    # Sort by average lap time
    team_avg = team_avg.sort_values("avg_lap")

    # Create colors based on team
    colors = [TEAM_COLORS.get(team, "#888888") for team in team_avg["team_name"]]

    fig = go.Figure()
    fig.add_bar(
        x=team_avg["team_name"],
        y=team_avg["avg_lap"],
        marker_color=colors,
        name="Average Lap Time",
        text=[f"{t:.3f}s" for t in team_avg["avg_lap"]],
        textposition="outside",
    )

    fig.update_layout(
        title="🏆 Average Lap Time by Team",
        xaxis_title="Team",
        yaxis_title="Average Lap Time (seconds)",
        xaxis_tickangle=-45,
    )
    apply_plot_style(fig)

    return fig


def plot_team_pace(df: pd.DataFrame) -> Figure:
    """Bar chart ranking teams by average pace."""
    if df.empty or "team_name" not in df.columns:
        return go.Figure().add_annotation(
            text="No team pace data available",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
        )

    colors = [TEAM_COLORS.get(team, "#888888") for team in df["team_name"]]
    fig = go.Figure()
    fig.add_bar(
        x=df["team_name"],
        y=df["lap_duration_seconds"],
        marker_color=colors,
        text=[f"{t:.3f}s" for t in df["lap_duration_seconds"]],
        textposition="outside",
    )
    fig.update_layout(
        title="🚥 Team Pace Ranking",
        xaxis_title="Team",
        yaxis_title="Average Lap Time (seconds)",
        xaxis_tickangle=-45,
    )
    apply_plot_style(fig)
    return fig


def plot_pace_by_compound(df: pd.DataFrame) -> Figure:
    """Box plot showing pace by tyre compound."""
    if df.empty:
        return go.Figure().add_annotation(
            text="No tyre compound data",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
        )

    fig = px.box(
        df,
        x="compound",
        y="lap_duration_seconds",
        title="🏎️ Lap Time by Tyre Compound",
        labels={
            "compound": "Tyre Compound",
            "lap_duration_seconds": "Lap Time (seconds)",
        },
        color="compound",
        color_discrete_map=COMPOUND_COLORS,
    )

    apply_plot_style(fig, showlegend=False)
    return fig


def plot_degradation_curves(df: pd.DataFrame) -> Figure:
    """Plot tyre degradation curves by compound."""
    if df.empty:
        return go.Figure().add_annotation(
            text="No degradation data available",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
        )

    fig = px.scatter(
        df,
        x="tyre_age",
        y="lap_duration_seconds",
        color="compound",
        title="📉 Tyre Degradation Curves",
        labels={
            "tyre_age": "Tyre Age (laps)",
            "lap_duration_seconds": "Lap Time (seconds)",
        },
        color_discrete_map=COMPOUND_COLORS,
        trendline="lowess",
    )

    apply_plot_style(fig)
    return fig


def plot_stint_timeline(stints: pd.DataFrame) -> Figure:
    """Gantt-style timeline showing driver stints."""
    if stints.empty:
        return go.Figure().add_annotation(
            text="No stint data available",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
        )

    fig = px.timeline(
        stints,
        x_start="lap_start",
        x_end="lap_end",
        y="driver_number",
        color="compound",
        title="🔄 Driver Stint Timeline",
        labels={"driver_number": "Driver #"},
        color_discrete_map=COMPOUND_COLORS,
    )

    fig.update_yaxes(title="Driver Number", type="category")
    fig.update_xaxes(title="Lap Number")
    apply_plot_style(fig, showlegend=False)

    return fig


# Phase 3 visualizers
def plot_sector_table(df: pd.DataFrame) -> Figure:
    """Sector performance comparison table/chart."""
    if df.empty:
        return go.Figure().add_annotation(
            text="No sector data available",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
        )

    # Create subplots for each sector
    fig = make_subplots(
        rows=1,
        cols=3,
        subplot_titles=("Sector 1", "Sector 2", "Sector 3"),
        shared_yaxes=True,
    )

    sectors = ["best_s1", "best_s2", "best_s3"]
    colors = ["red", "yellow", "green"]

    for i, (sector, color) in enumerate(zip(sectors, colors)):
        if sector in df.columns:
            fig.add_bar(
                x=df["driver_number"],
                y=df[sector],
                name=f"Sector {i+1}",
                marker_color=color,
                row=1,
                col=i + 1,
            )

    fig.update_layout(
        title="⏱️ Best Sector Times by Driver",
    )
    apply_plot_style(fig, showlegend=False)

    return fig


def plot_pit_durations(df: pd.DataFrame) -> Figure:
    """Plot pit stop duration analysis."""
    if df.empty:
        return go.Figure().add_annotation(
            text="No pit stop data available",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
        )

    fig = go.Figure()

    # Average pit time bars
    fig.add_bar(
        x=df["driver_number"],
        y=df["avg_pit"],
        name="Average Pit Time",
        marker_color="lightblue",
        error_y=dict(
            type="data",
            array=df["max_pit"] - df["avg_pit"],
            arrayminus=df["avg_pit"] - df["min_pit"],
            visible=True,
        ),
    )

    # Best pit time line
    fig.add_scatter(
        x=df["driver_number"],
        y=df["min_pit"],
        mode="markers+lines",
        name="Best Pit Time",
        marker=dict(color="green", size=8),
        line=dict(color="green", dash="dot"),
    )

    fig.update_layout(
        title="🔧 Pit Stop Duration Analysis",
        xaxis_title="Driver Number",
        yaxis_title="Pit Duration (seconds)",
        legend=dict(x=0.7, y=0.95),
    )
    apply_plot_style(fig)

    return fig


def plot_performance_radar(driver_stats: dict, teammate_stats: dict = None) -> Figure:
    """Create a radar chart comparing driver performance metrics."""
    if not driver_stats:
        return go.Figure().add_annotation(
            text="No performance data available",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
        )

    categories = [
        "Pace",
        "Consistency",
        "Sector 1",
        "Sector 2",
        "Sector 3",
        "Pit Stops",
    ]

    # Normalize stats to 0-1 scale for radar chart
    values = [
        1
        - (driver_stats.get("avg_lap", 90) - 80)
        / 20,  # Pace (inverted, faster = better)
        1 - driver_stats.get("consistency", 5) / 10,  # Consistency (inverted)
        1 - (driver_stats.get("best_s1", 30) - 20) / 20,  # Sector times (inverted)
        1 - (driver_stats.get("best_s2", 30) - 20) / 20,
        1 - (driver_stats.get("best_s3", 30) - 20) / 20,
        1 - (driver_stats.get("avg_pit", 25) - 20) / 10,  # Pit stops (inverted)
    ]

    fig = go.Figure()

    fig.add_trace(
        go.Scatterpolar(
            r=values, theta=categories, fill="toself", name="Driver Performance"
        )
    )

    if teammate_stats:
        teammate_values = [
            1 - (teammate_stats.get("avg_lap", 90) - 80) / 20,
            1 - teammate_stats.get("consistency", 5) / 10,
            1 - (teammate_stats.get("best_s1", 30) - 20) / 20,
            1 - (teammate_stats.get("best_s2", 30) - 20) / 20,
            1 - (teammate_stats.get("best_s3", 30) - 20) / 20,
            1 - (teammate_stats.get("avg_pit", 25) - 20) / 10,
        ]

        fig.add_trace(
            go.Scatterpolar(
                r=teammate_values,
                theta=categories,
                fill="toself",
                name="Teammate Performance",
            )
        )

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        title="🎯 Performance Radar Comparison",
    )
    apply_plot_style(fig)

    return fig

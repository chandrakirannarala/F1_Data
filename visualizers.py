import plotly.express as px
import pandas as pd
from plotly.graph_objects import Figure

# Phase 1 visualizers
def plot_lap_trend(df):
    return px.line(df, x="lap_number", y="lap_duration", title="Lap Time Trend")


def plot_distribution(df):
    return px.histogram(df, x="lap_duration", nbins=20, title="Lap Time Distribution")


def plot_delta(df):
    return px.bar(df, x="lap_number", y="delta", title="Lap‐by‐Lap Delta vs. Teammate")

# Phase 2 visualizers
def plot_team_comparison(df: pd.DataFrame) -> Figure:
    team_avg = df.groupby("team_name")["avg_lap"].mean().reset_index()
    return px.bar(team_avg, x="team_name", y="avg_lap", title="Average Lap Time by Team")


def plot_pace_by_compound(df: pd.DataFrame) -> Figure:
    return px.box(df, x="compound", y="lap_duration", title="Lap Time by Tyre Compound")


def plot_degradation_curves(df: pd.DataFrame) -> Figure:
    return px.line(df, x="tyre_age", y="lap_duration", color="compound", title="Tyre Degradation Curves")


def plot_stint_timeline(stints: pd.DataFrame) -> Figure:
    fig = px.timeline(
        stints,
        x_start="lap_start",
        x_end="lap_end",
        y="driver_number",
        color="compound",
        title="Driver Stint Timeline"
    )
    fig.update_yaxes(title="Driver #")
    return fig

# Phase 3 visualizers
def plot_sector_table(df: pd.DataFrame) -> Figure:
    table = df.copy()
    table["sectors"] = table.apply(
        lambda r: f"S1:{r.best_s1}, S2:{r.best_s2}, S3:{r.best_s3}",
        axis=1
    )
    return px.scatter(
        table, x="driver_number", y=[0]*len(table), text="sectors",
        title="Best Sector Times"
    )


def plot_pit_durations(df: pd.DataFrame) -> Figure:
    return px.bar(df, x="driver_number", y="avg_pit", title="Average Pit Stop Duration")
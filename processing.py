import pandas as pd
import numpy as np
from typing import List, Dict, Any

def lap_stats(laps: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate comprehensive lap statistics."""
    if not laps:
        return {"error": "No lap data available"}
    
    df = pd.DataFrame(laps)
    
    # Handle different lap duration formats (seconds as float or time string)
    if 'lap_duration' in df.columns:
        if df['lap_duration'].dtype == 'object':
            # If it's a string format like "1:23.456", convert to seconds
            df["lap_duration_seconds"] = df["lap_duration"].apply(convert_time_to_seconds)
        else:
            # If it's already numeric (seconds)
            df["lap_duration_seconds"] = df["lap_duration"]
    else:
        return {"error": "No lap_duration column found"}
    
    # Filter out invalid laps (pit laps, outliers)
    valid_laps = df[
        (df["lap_duration_seconds"].notna()) & 
        (df["lap_duration_seconds"] > 0) &
        (~df.get("is_pit_out_lap", False))
    ]
    
    if valid_laps.empty:
        return {"error": "No valid lap data found"}
    
    return {
        "fastest": format_time(valid_laps["lap_duration_seconds"].min()),
        "average": format_time(valid_laps["lap_duration_seconds"].mean()),
        "median": format_time(valid_laps["lap_duration_seconds"].median()),
        "stdev": format_time(valid_laps["lap_duration_seconds"].std()),
        "total_laps": len(df),
        "valid_laps": len(valid_laps),
        "consistency": calculate_consistency(valid_laps["lap_duration_seconds"])
    }


def convert_time_to_seconds(time_str: Any) -> float:
    """Convert time string (MM:SS.mmm) to seconds."""
    if pd.isna(time_str) or time_str is None:
        return np.nan
    
    if isinstance(time_str, (int, float)):
        return float(time_str)
    
    try:
        time_str = str(time_str)
        if ':' in time_str:
            parts = time_str.split(':')
            minutes = float(parts[0])
            seconds = float(parts[1])
            return minutes * 60 + seconds
        else:
            return float(time_str)
    except (ValueError, IndexError):
        return np.nan


def format_time(seconds: float) -> str:
    """Format seconds back to MM:SS.mmm format."""
    if pd.isna(seconds):
        return "N/A"
    
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}:{secs:06.3f}"


def calculate_consistency(lap_times: pd.Series) -> float:
    """Calculate consistency score (lower is better)."""
    if len(lap_times) < 2:
        return 0.0
    
    # Use coefficient of variation (std/mean) as consistency metric
    return (lap_times.std() / lap_times.mean()) * 100


def teammate_deltas(driver_laps: pd.DataFrame, mate_laps: pd.DataFrame) -> pd.DataFrame:
    """Calculate lap-by-lap deltas between teammates."""
    if driver_laps.empty or mate_laps.empty:
        return pd.DataFrame(columns=["lap_number", "delta"])
    
    # Ensure lap_duration is in seconds
    driver_laps = driver_laps.copy()
    mate_laps = mate_laps.copy()
    
    for df in [driver_laps, mate_laps]:
        if 'lap_duration' in df.columns:
            df["lap_duration_seconds"] = df["lap_duration"].apply(convert_time_to_seconds)
    
    merged = driver_laps.merge(
        mate_laps[["lap_number", "lap_duration_seconds"]],
        on="lap_number",
        suffixes=("", "_mate"),
        how="inner"
    )
    
    if merged.empty:
        return pd.DataFrame(columns=["lap_number", "delta"])
    
    merged["delta"] = merged["lap_duration_seconds"] - merged["lap_duration_seconds_mate"]
    
    return merged[["lap_number", "delta"]].dropna()


# Phase 2: Team & Tyre Analysis

def team_pace_stats(laps: List[Dict[str, Any]]) -> pd.DataFrame:
    """Calculate team pace statistics."""
    if not laps:
        return pd.DataFrame()
    
    df = pd.DataFrame(laps)
    
    # Convert lap duration to seconds
    df["lap_duration_seconds"] = df["lap_duration"].apply(convert_time_to_seconds)
    
    # Filter valid laps
    valid_df = df[
        (df["lap_duration_seconds"].notna()) & 
        (df["lap_duration_seconds"] > 0) &
        (~df.get("is_pit_out_lap", False))
    ]
    
    if valid_df.empty:
        return pd.DataFrame()
    
    # Group by team and driver
    team_stats = valid_df.groupby(["team_name", "driver_number"]).agg(
        avg_lap=("lap_duration_seconds", "mean"),
        median_lap=("lap_duration_seconds", "median"),
        fastest_lap=("lap_duration_seconds", "min"),
        lap_count=("lap_duration_seconds", "count"),
        consistency=("lap_duration_seconds", lambda x: calculate_consistency(x))
    ).reset_index()
    
    return team_stats


def overall_team_pace(laps: List[Dict[str, Any]]) -> pd.DataFrame:
    """Aggregate average pace per team."""
    if not laps:
        return pd.DataFrame()

    df = pd.DataFrame(laps)
    df["lap_duration_seconds"] = df["lap_duration"].apply(convert_time_to_seconds)

    valid_df = df[
        (df["lap_duration_seconds"].notna())
        & (df["lap_duration_seconds"] > 0)
        & (~df.get("is_pit_out_lap", False))
    ]

    if valid_df.empty:
        return pd.DataFrame()

    team_avg = (
        valid_df.groupby("team_name")["lap_duration_seconds"].mean().reset_index()
    )

    return team_avg.sort_values("lap_duration_seconds")


def tyre_degradation(laps: List[Dict[str, Any]], stints: List[Dict[str, Any]]) -> pd.DataFrame:
    """Analyze tyre degradation patterns."""
    if not laps or not stints:
        return pd.DataFrame()
    
    laps_df = pd.DataFrame(laps)
    stints_df = pd.DataFrame(stints)
    
    # Convert lap duration to seconds
    laps_df["lap_duration_seconds"] = laps_df["lap_duration"].apply(convert_time_to_seconds)
    
    # Merge laps with stint information
    merged = laps_df.merge(
        stints_df,
        on=["session_key", "driver_number"],
        how="left"
    )
    
    # Filter laps within stint ranges
    merged = merged[
        (merged["lap_number"] >= merged["lap_start"]) &
        (merged["lap_number"] <= merged["lap_end"])
    ]
    
    # Calculate tyre age for each lap
    merged["tyre_age"] = (
        merged["tyre_age_at_start"] +
        (merged["lap_number"] - merged["lap_start"])
    )
    
    # Filter valid laps
    merged = merged[
        (merged["lap_duration_seconds"].notna()) & 
        (merged["lap_duration_seconds"] > 0) &
        (~merged.get("is_pit_out_lap", False))
    ]
    
    return merged[["driver_number", "compound", "tyre_age", "lap_duration_seconds", "lap_number"]]


# Phase 3: Sector & Pit Analysis

def sector_stats(laps: List[Dict[str, Any]]) -> pd.DataFrame:
    """Calculate sector performance statistics."""
    if not laps:
        return pd.DataFrame()
    
    df = pd.DataFrame(laps)
    
    # Convert sector times to seconds
    for sector in [1, 2, 3]:
        col = f"duration_sector_{sector}"
        if col in df.columns:
            df[f"s{sector}_seconds"] = df[col].apply(convert_time_to_seconds)
        else:
            df[f"s{sector}_seconds"] = np.nan
    
    # Calculate sector statistics by driver
    sector_stats = df.groupby("driver_number").agg(
        best_s1=("s1_seconds", "min"),
        avg_s1=("s1_seconds", "mean"),
        best_s2=("s2_seconds", "min"),
        avg_s2=("s2_seconds", "mean"),
        best_s3=("s3_seconds", "min"),
        avg_s3=("s3_seconds", "mean"),
        sector_consistency=("s1_seconds", lambda x: calculate_consistency(x.dropna()))
    ).reset_index()
    
    return sector_stats


def pit_stats(pits: List[Dict[str, Any]]) -> pd.DataFrame:
    """Calculate pit stop statistics."""
    if not pits:
        return pd.DataFrame()
    
    df = pd.DataFrame(pits)
    
    # Convert pit duration to seconds
    df["pit_duration_seconds"] = df["pit_duration"].apply(convert_time_to_seconds)
    
    # Filter valid pit stops
    valid_pits = df[
        (df["pit_duration_seconds"].notna()) & 
        (df["pit_duration_seconds"] > 0) &
        (df["pit_duration_seconds"] < 60)  # Reasonable pit stop duration
    ]
    
    if valid_pits.empty:
        return pd.DataFrame()
    
    pit_summary = valid_pits.groupby("driver_number").agg(
        avg_pit=("pit_duration_seconds", "mean"),
        min_pit=("pit_duration_seconds", "min"),
        max_pit=("pit_duration_seconds", "max"),
        pit_count=("pit_duration_seconds", "count"),
        pit_consistency=("pit_duration_seconds", lambda x: calculate_consistency(x))
    ).reset_index()
    
    return pit_summary


def advanced_performance_metrics(laps: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate advanced performance metrics."""
    if not laps:
        return {}
    
    df = pd.DataFrame(laps)
    df["lap_duration_seconds"] = df["lap_duration"].apply(convert_time_to_seconds)
    
    valid_laps = df[
        (df["lap_duration_seconds"].notna()) & 
        (df["lap_duration_seconds"] > 0) &
        (~df.get("is_pit_out_lap", False))
    ]
    
    if valid_laps.empty:
        return {}
    
    # Calculate percentiles
    percentiles = valid_laps["lap_duration_seconds"].quantile([0.1, 0.25, 0.5, 0.75, 0.9])
    
    # Calculate pace degradation over stint
    valid_laps = valid_laps.sort_values("lap_number")
    if len(valid_laps) > 5:
        early_pace = valid_laps.head(5)["lap_duration_seconds"].mean()
        late_pace = valid_laps.tail(5)["lap_duration_seconds"].mean()
        pace_degradation = late_pace - early_pace
    else:
        pace_degradation = 0
    
    return {
        "p10_laptime": format_time(percentiles[0.1]),
        "p25_laptime": format_time(percentiles[0.25]),
        "p75_laptime": format_time(percentiles[0.75]),
        "p90_laptime": format_time(percentiles[0.9]),
        "pace_degradation": pace_degradation,
        "race_pace": format_time(valid_laps["lap_duration_seconds"].mean()),
        "qualifying_pace": format_time(valid_laps["lap_duration_seconds"].min())
    }
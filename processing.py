import pandas as pd

def lap_stats(laps: list[dict]) -> dict:
    df = pd.DataFrame(laps)
    df["lap_duration"] = pd.to_timedelta(df["lap_duration"])
    return {
        "fastest": df["lap_duration"].min(),
        "average": df["lap_duration"].mean(),
        "median": df["lap_duration"].median(),
        "stdev": df["lap_duration"].std()
    }


def teammate_deltas(driver_laps: pd.DataFrame, mate_laps: pd.DataFrame) -> pd.DataFrame:
    merged = driver_laps.merge(
        mate_laps[["lap_number", "lap_duration"]],
        on="lap_number",
        suffixes=("", "_mate")
    )
    merged["delta"] = (
        pd.to_timedelta(merged["lap_duration"]) -
        pd.to_timedelta(merged["lap_duration_mate"])
    )
    return merged[["lap_number", "delta"]]


# Phase 2: Team & Tyre Analysis

def team_pace_stats(laps: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(laps)
    df["lap_duration"] = pd.to_timedelta(df["lap_duration"])
    grp = df.groupby(["team_name", "driver_number"]).agg(
        avg_lap=("lap_duration", "mean"),
        median_lap=("lap_duration", "median")
    ).reset_index()
    return grp


def tyre_degradation(laps: list[dict], stints: list[dict]) -> pd.DataFrame:
    laps_df = pd.DataFrame(laps)
    stints_df = pd.DataFrame(stints)
    merged = laps_df.merge(
        stints_df,
        on=["session_key", "driver_number"],
        how="left"
    )
    merged["lap_duration"] = pd.to_timedelta(merged["lap_duration"])
    merged["tyre_age"] = (
        merged["tyre_age_at_start"] +
        (merged["lap_number"] - merged["lap_start"])
    )
    return merged[["driver_number", "compound", "tyre_age", "lap_duration"]]


# Phase 3: Sector & Pit Analysis

def sector_stats(laps: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(laps)
    for s in [1,2,3]:
        df[f"s{s}"] = pd.to_timedelta(df[f"duration_sector_{s}"])
    best = df.groupby("driver_number").agg(
        best_s1=("s1", "min"),
        best_s2=("s2", "min"),
        best_s3=("s3", "min")
    ).reset_index()
    return best


def pit_stats(pits: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(pits)
    df["pit_duration"] = pd.to_timedelta(df["pit_duration"])
    summary = df.groupby("driver_number").agg(
        avg_pit=("pit_duration", "mean"),
        min_pit=("pit_duration", "min"),
        max_pit=("pit_duration", "max")
    ).reset_index()
    return summary
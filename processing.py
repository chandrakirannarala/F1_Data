import pandas as pd

def lap_stats(lap_records: list[dict]) -> dict:
    df = pd.DataFrame(lap_records)
    df["lap_duration"] = pd.to_timedelta(df["lap_duration"])
    stats = {
        "fastest": df["lap_duration"].min(),
        "average": df["lap_duration"].mean(),
        "median": df["lap_duration"].median(),
        "stdev": df["lap_duration"].std(),
    }
    return stats

def teammate_deltas(driver_df: pd.DataFrame, mate_df: pd.DataFrame):
    merged = driver_df.merge(
        mate_df[["lap_number", "lap_duration"]],
        on="lap_number",
        suffixes=("", "_mate")
    )
    merged["delta"] = merged["lap_duration"] - merged["lap_duration_mate"]
    return merged[["lap_number", "delta"]]

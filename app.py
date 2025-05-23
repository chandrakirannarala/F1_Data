import dash
import pandas as pd
from dash import html, dcc, Input, Output
from api import get_token, fetch_json
from processing import lap_stats, teammate_deltas
from visualizers import plot_lap_trend, plot_delta, plot_distribution

oauth = get_token("YOUR_ID", "YOUR_SECRET")
app = dash.Dash(__name__)

# Preload session & driver lists...
sessions = fetch_json(oauth, "sessions", meeting_key="2025-monaco")
drivers  = fetch_json(oauth, "drivers", session_key=sessions[0]["session_key"])

app.layout = html.Div([
    dcc.Dropdown(
      id="driver-select",
      options=[{"label": d["full_name"], "value": d["driver_number"]} for d in drivers],
      value=drivers[0]["driver_number"]
    ),
    dcc.Graph(id="trend"),
    dcc.Graph(id="distribution"),
    dcc.Graph(id="delta"),
    html.Div(id="stats")
])

@app.callback(
    [Output("trend","figure"),
     Output("distribution","figure"),
     Output("delta","figure"),
     Output("stats","children")],
    Input("driver-select","value")
)
def update_charts(driver_no):
    laps = fetch_json(oauth, "laps", session_key=sessions[0]["session_key"],
                      driver_number=driver_no)
    stats = lap_stats(laps)
    df = pd.DataFrame(laps)
    df["lap_duration"] = pd.to_timedelta(df["lap_duration"])
    # teammate:
    mate = [d for d in drivers if d["driver_number"]!=driver_no][0]
    mate_laps = fetch_json(oauth, "laps", session_key=sessions[0]["session_key"],
                           driver_number=mate["driver_number"])
    delta_df = teammate_deltas(df, pd.DataFrame(mate_laps))
    return (
      plot_lap_trend(df),
      plot_distribution(df),
      plot_delta(delta_df),
      f"Fastest: {stats['fastest']}, Avg: {stats['average']}, StdDev: {stats['stdev']}"
    )

if __name__=="__main__":
    app.run_server(debug=True)

import pandas as pd
import dash
from dash import html, dcc, Input, Output
import api, processing, visualizers

# Initialize
oauth = api.get_oauth_session()
sessions = api.get_sessions(oauth, meeting_key="2025-monaco")
drivers_all = api.get_drivers(oauth, session_key=sessions[0].session_key)

app = dash.Dash(__name__)
app.layout = html.Div([
    html.H2("F1 Performance Dashboard"),
    dcc.Dropdown(
        id='driver-select',
        options=[{'label': d.full_name, 'value': d.driver_number} for d in drivers_all],
        value=drivers_all[0].driver_number
    ),
    dcc.Graph(id='trend'),
    dcc.Graph(id='distribution'),
    dcc.Graph(id='delta'),
    html.H3("Team & Tyre Insights"),
    dcc.Graph(id='team-pace'),
    dcc.Graph(id='compound-dist'),
    dcc.Graph(id='degradation'),
    dcc.Graph(id='stint-timeline'),
    html.H3("Sector & Pit Analysis"),
    dcc.Graph(id='sector-table'),
    dcc.Graph(id='pit-duration'),
    html.Div(id='stats')
])

@app.callback(
    [Output('trend','figure'), Output('distribution','figure'), Output('delta','figure'),
     Output('team-pace','figure'), Output('compound-dist','figure'), Output('degradation','figure'),
     Output('stint-timeline','figure'), Output('sector-table','figure'), Output('pit-duration','figure'),
     Output('stats','children')],
    Input('driver-select','value')
)
def update_all(driver_no):
    sess_key = sessions[0].session_key
    # Fetch data
    laps = api.get_laps(oauth, sess_key, driver_no)
    laps_df = pd.DataFrame([l.dict() for l in laps])
    stats = processing.lap_stats([l.dict() for l in laps])
    # teammate
    mate = next(d for d in drivers_all if d.driver_number != driver_no)
    mate_laps = api.get_laps(oauth, sess_key, mate.driver_number)
    mate_df = pd.DataFrame([l.dict() for l in mate_laps])

    # Phase 2 & 3 data
    all_laps = api.get_laps(oauth, sess_key)
    all_stints = api.get_stints(oauth, sess_key)
    all_pits = api.get_pits(oauth, sess_key)

    # Processing
    team_df = processing.team_pace_stats([l.dict() for l in all_laps])
    tyre_df = processing.tyre_degradation([l.dict() for l in all_laps], [s.dict() for s in all_stints])
    sector_df = processing.sector_stats([l.dict() for l in all_laps])
    pit_df = processing.pit_stats([p.dict() for p in all_pits])

    # Visuals
    return (
        visualizers.plot_lap_trend(laps_df),
        visualizers.plot_distribution(laps_df),
        visualizers.plot_delta(processing.teammate_deltas(laps_df, mate_df)),
        visualizers.plot_team_comparison(team_df),
        visualizers.plot_pace_by_compound(tyre_df),
        visualizers.plot_degradation_curves(tyre_df),
        visualizers.plot_stint_timeline(pd.DataFrame([s.dict() for s in all_stints])),
        visualizers.plot_sector_table(sector_df),
        visualizers.plot_pit_durations(pit_df),
        f"Fastest: {stats['fastest']}, Avg: {stats['average']}, StdDev: {stats['stdev']}"
    )

if __name__ == '__main__':
    app.run_server(debug=True)
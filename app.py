import pandas as pd
import dash
from dash import html, dcc, Input, Output, callback
import api, processing, visualizers

# Initialize - No OAuth needed!
# Get available meetings for 2024 (2025 data might not be available yet)
try:
    meetings = api.get_meetings(2024)
    print(f"Found {len(meetings)} meetings for 2024")
    
    # Use the last meeting as an example (or you can choose a specific one)
    if meetings:
        selected_meeting = meetings[-1]  # Last meeting of the year
        print(f"Selected meeting: {selected_meeting.meeting_name}")
        
        sessions = api.get_sessions(selected_meeting.meeting_key)
        print(f"Found {len(sessions)} sessions")
        
        # Find race session or use the last session
        race_session = None
        for session in sessions:
            if "race" in session.session_name.lower():
                race_session = session
                break
        
        if not race_session and sessions:
            race_session = sessions[-1]  # Use last session if no race found
        
        if race_session:
            print(f"Using session: {race_session.session_name}")
            drivers_all = api.get_drivers(race_session.session_key)
            print(f"Found {len(drivers_all)} drivers")
        else:
            print("No suitable session found")
            drivers_all = []
    else:
        print("No meetings found for 2024")
        drivers_all = []
        race_session = None
        
except Exception as e:
    print(f"Error initializing data: {e}")
    print("Using fallback data...")
    drivers_all = []
    race_session = None

app = dash.Dash(__name__)

if not drivers_all:
    # Fallback layout if no data available
    app.layout = html.Div([
        html.H2("F1 Performance Dashboard"),
        html.Div([
            html.H3("⚠️ No Data Available"),
            html.P("Could not load F1 data. This might be because:"),
            html.Ul([
                html.Li("The API is temporarily unavailable"),
                html.Li("No 2024 race data is available yet"),
                html.Li("Network connectivity issues")
            ]),
            html.P("Please try again later or check the OpenF1 API status."),
            html.A("Visit OpenF1 API", href="https://openf1.org", target="_blank")
        ], style={"padding": "20px", "border": "1px solid #ccc", "margin": "20px"})
    ])
else:
    # Main dashboard layout
    app.layout = html.Div([
        html.H2("🏎️ F1 Performance Dashboard"),
        html.Div([
            html.Label("Select Driver:"),
            dcc.Dropdown(
                id='driver-select',
                options=[{
                    'label': f"{d.broadcast_name} ({d.team_name})", 
                    'value': d.driver_number
                } for d in drivers_all],
                value=drivers_all[0].driver_number if drivers_all else None,
                style={'marginBottom': '20px'}
            )
        ]),
        
        # Basic Performance Metrics
        html.H3("📊 Lap Performance"),
        html.Div([
            dcc.Graph(id='trend', style={'width': '50%', 'display': 'inline-block'}),
            dcc.Graph(id='distribution', style={'width': '50%', 'display': 'inline-block'})
        ]),
        dcc.Graph(id='delta'),
        
        # Team & Tyre Analysis
        html.H3("🏁 Team & Tyre Insights"),
        html.Div([
            dcc.Graph(id='team-pace', style={'width': '50%', 'display': 'inline-block'}),
            dcc.Graph(id='compound-dist', style={'width': '50%', 'display': 'inline-block'})
        ]),
        dcc.Graph(id='degradation'),
        dcc.Graph(id='stint-timeline'),
        
        # Sector & Pit Analysis
        html.H3("⏱️ Sector & Pit Analysis"),
        html.Div([
            dcc.Graph(id='sector-table', style={'width': '50%', 'display': 'inline-block'}),
            dcc.Graph(id='pit-duration', style={'width': '50%', 'display': 'inline-block'})
        ]),
        
        # Statistics Summary
        html.H3("📈 Statistics Summary"),
        html.Div(id='stats', style={
            'padding': '20px', 
            'backgroundColor': '#f0f0f0', 
            'border': '1px solid #ddd',
            'borderRadius': '5px',
            'margin': '20px 0'
        }),
        
        # Session Info
        html.Div([
            html.H4("Session Information"),
            html.P(f"Meeting: {selected_meeting.meeting_name if 'selected_meeting' in locals() else 'Unknown'}"),
            html.P(f"Session: {race_session.session_name if race_session else 'Unknown'}"),
            html.P(f"Date: {race_session.date_start.strftime('%Y-%m-%d %H:%M') if race_session else 'Unknown'}")
        ], style={'marginTop': '30px', 'padding': '15px', 'backgroundColor': '#e8f4f8'})
    ])

@app.callback(
    [Output('trend','figure'), Output('distribution','figure'), Output('delta','figure'),
     Output('team-pace','figure'), Output('compound-dist','figure'), Output('degradation','figure'),
     Output('stint-timeline','figure'), Output('sector-table','figure'), Output('pit-duration','figure'),
     Output('stats','children')],
    Input('driver-select','value'),
    prevent_initial_call=False
)
def update_all(driver_no):
    if not race_session or not driver_no:
        # Return empty figures if no data
        empty_fig = {"data": [], "layout": {"title": "No data available"}}
        return [empty_fig] * 9 + ["No statistics available"]
    
    try:
        sess_key = race_session.session_key
        
        # Fetch data for selected driver
        laps = api.get_laps(sess_key, driver_no)
        if not laps:
            print(f"No lap data found for driver {driver_no}")
            empty_fig = {"data": [], "layout": {"title": "No lap data available"}}
            return [empty_fig] * 9 + ["No lap data available for this driver"]
        
        laps_df = pd.DataFrame([l.dict() for l in laps])
        stats = processing.lap_stats([l.dict() for l in laps])
        
        # Find teammate (same team, different driver)
        selected_driver = next((d for d in drivers_all if d.driver_number == driver_no), None)
        teammate = None
        mate_df = pd.DataFrame()
        
        if selected_driver:
            teammates = [d for d in drivers_all 
                        if d.team_name == selected_driver.team_name and d.driver_number != driver_no]
            if teammates:
                teammate = teammates[0]
                mate_laps = api.get_laps(sess_key, teammate.driver_number)
                if mate_laps:
                    mate_df = pd.DataFrame([l.dict() for l in mate_laps])

        # Fetch additional data for comprehensive analysis
        all_laps = api.get_laps(sess_key)
        all_stints = api.get_stints(sess_key)
        all_pits = api.get_pits(sess_key)

        # Process data
        team_df = processing.team_pace_stats([l.dict() for l in all_laps]) if all_laps else pd.DataFrame()
        tyre_df = processing.tyre_degradation([l.dict() for l in all_laps], [s.dict() for s in all_stints]) if all_laps and all_stints else pd.DataFrame()
        sector_df = processing.sector_stats([l.dict() for l in all_laps]) if all_laps else pd.DataFrame()
        pit_df = processing.pit_stats([p.dict() for p in all_pits]) if all_pits else pd.DataFrame()

        # Generate visualizations
        return (
            visualizers.plot_lap_trend(laps_df),
            visualizers.plot_distribution(laps_df),
            visualizers.plot_delta(processing.teammate_deltas(laps_df, mate_df)) if not mate_df.empty else {"data": [], "layout": {"title": "No teammate data"}},
            visualizers.plot_team_comparison(team_df) if not team_df.empty else {"data": [], "layout": {"title": "No team data"}},
            visualizers.plot_pace_by_compound(tyre_df) if not tyre_df.empty else {"data": [], "layout": {"title": "No tyre data"}},
            visualizers.plot_degradation_curves(tyre_df) if not tyre_df.empty else {"data": [], "layout": {"title": "No degradation data"}},
            visualizers.plot_stint_timeline(pd.DataFrame([s.dict() for s in all_stints])) if all_stints else {"data": [], "layout": {"title": "No stint data"}},
            visualizers.plot_sector_table(sector_df) if not sector_df.empty else {"data": [], "layout": {"title": "No sector data"}},
            visualizers.plot_pit_durations(pit_df) if not pit_df.empty else {"data": [], "layout": {"title": "No pit data"}},
            html.Div([
                html.P(f"🏎️ Driver: {selected_driver.broadcast_name if selected_driver else 'Unknown'} ({selected_driver.team_name if selected_driver else 'Unknown Team'})"),
                html.P(f"⚡ Fastest Lap: {stats.get('fastest', 'N/A')}"),
                html.P(f"📊 Average Lap: {stats.get('average', 'N/A')}"),
                html.P(f"📈 Std Deviation: {stats.get('stdev', 'N/A')}"),
                html.P(f"🔢 Total Laps: {len(laps)}"),
                html.P(f"👥 Teammate: {teammate.broadcast_name if teammate else 'None found'}")
            ])
        )
        
    except Exception as e:
        print(f"Error in callback: {e}")
        error_fig = {"data": [], "layout": {"title": f"Error: {str(e)[:50]}..."}}
        return [error_fig] * 9 + [f"Error processing data: {str(e)}"]

if __name__ == '__main__':
    print("🚀 Starting F1 Performance Dashboard...")
    print("📡 Using OpenF1 API (no authentication required)")
    app.run_server(debug=True, host='0.0.0.0', port=8050)
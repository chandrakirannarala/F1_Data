import dash
from dash import dcc, html, Input, Output, callback
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from datetime import datetime
import logging
from typing import List, Dict, Any, Optional
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Dash app
app = dash.Dash(__name__)
app.title = "🏎️ F1 Performance Dashboard"

# API Configuration
API_BASE = "https://api.openf1.org/v1"

# Color schemes
TEAM_COLORS = {
    'Red Bull Racing': '#1E41FF',
    'Mercedes': '#00D2BE', 
    'Ferrari': '#DC143C',
    'McLaren': '#FF8700',
    'Alpine': '#0090FF',
    'Aston Martin': '#006F62',
    'Williams': '#005AFF',
    'AlphaTauri': '#2B4562',
    'Alfa Romeo': '#900000',
    'Haas': '#FFFFFF'
}

COMPOUND_COLORS = {
    'SOFT': '#FF3333',
    'MEDIUM': '#FFD700', 
    'HARD': '#FFFFFF',
    'INTERMEDIATE': '#00FF00',
    'WET': '#0066FF'
}

# API Functions
def fetch_json(path: str, **params) -> List[dict]:
    """Fetch raw JSON list from OpenF1 API endpoint."""
    url = f"{API_BASE}/{path}"
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if not isinstance(data, list):
            logger.warning(f"API returned non-list data for {path}: {type(data)}")
            return []
            
        logger.info(f"Fetched {len(data)} records from {path}")
        return data
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed for {path}: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching {path}: {e}")
        return []

def get_meetings(year: int) -> List[dict]:
    """Get all meetings for a specific year."""
    return fetch_json("meetings", year=year)

def get_sessions(meeting_key: int) -> List[dict]:
    """Get all sessions for a specific meeting."""
    return fetch_json("sessions", meeting_key=meeting_key)

def get_drivers(session_key: int) -> List[dict]:
    """Get all drivers for a specific session."""
    return fetch_json("drivers", session_key=session_key)

def get_laps(session_key: int, driver_number: Optional[int] = None) -> List[dict]:
    """Get lap data for a session, optionally filtered by driver."""
    params = {"session_key": session_key}
    if driver_number is not None:
        params["driver_number"] = driver_number
    return fetch_json("laps", **params)

def get_stints(session_key: int, driver_number: Optional[int] = None) -> List[dict]:
    """Get stint data for a session, optionally filtered by driver."""
    params = {"session_key": session_key}
    if driver_number is not None:
        params["driver_number"] = driver_number
    return fetch_json("stints", **params)

def get_pits(session_key: int, driver_number: Optional[int] = None) -> List[dict]:
    """Get pit stop data for a session, optionally filtered by driver."""
    params = {"session_key": session_key}
    if driver_number is not None:
        params["driver_number"] = driver_number
    return fetch_json("pit", **params)

# Processing Functions
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

def calculate_lap_stats(laps: List[dict]) -> Dict[str, Any]:
    """Calculate comprehensive lap statistics."""
    if not laps:
        return {"error": "No lap data available"}
    
    df = pd.DataFrame(laps)
    
    if 'lap_duration' not in df.columns:
        return {"error": "No lap_duration column found"}
    
    df["lap_duration_seconds"] = df["lap_duration"].apply(convert_time_to_seconds)
    
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
        "total_laps": len(df),
        "valid_laps": len(valid_laps),
        "consistency": (valid_laps["lap_duration_seconds"].std() / valid_laps["lap_duration_seconds"].mean()) * 100
    }

# Visualization Functions
def create_lap_trend_plot(df: pd.DataFrame) -> go.Figure:
    """Create lap time trend plot."""
    if df.empty:
        return go.Figure().add_annotation(
            text="No data available", 
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
    
    df = df.copy()
    df['lap_duration_seconds'] = df['lap_duration'].apply(convert_time_to_seconds)
    
    # Filter valid laps
    valid_df = df[
        (df['lap_duration_seconds'].notna()) & 
        (df['lap_duration_seconds'] > 0)
    ]
    
    if valid_df.empty:
        return go.Figure().add_annotation(
            text="No valid lap times", 
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
    
    fig = px.line(valid_df, x="lap_number", y="lap_duration_seconds", 
                  title="🏁 Lap Time Trend",
                  labels={"lap_number": "Lap Number", "lap_duration_seconds": "Lap Time (seconds)"})
    
    # Add moving average if enough data
    if len(valid_df) > 3:
        valid_df['moving_avg'] = valid_df['lap_duration_seconds'].rolling(window=3, center=True).mean()
        fig.add_scatter(x=valid_df['lap_number'], y=valid_df['moving_avg'], 
                       mode='lines', name='3-lap moving average',
                       line=dict(dash='dash', color='orange'))
    
    fig.update_layout(
        template='plotly_white',
        hovermode='x unified',
        showlegend=True
    )
    
    return fig

def create_lap_distribution_plot(df: pd.DataFrame) -> go.Figure:
    """Create lap time distribution plot."""
    if df.empty:
        return go.Figure().add_annotation(
            text="No data available", 
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
    
    df = df.copy()
    df['lap_duration_seconds'] = df['lap_duration'].apply(convert_time_to_seconds)
    
    valid_times = df['lap_duration_seconds'].dropna()
    if valid_times.empty:
        return go.Figure().add_annotation(
            text="No valid lap times", 
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
    
    fig = px.histogram(df[df['lap_duration_seconds'].notna()], 
                      x="lap_duration_seconds", nbins=20, 
                      title="📊 Lap Time Distribution",
                      labels={"lap_duration_seconds": "Lap Time (seconds)"})
    
    # Add statistical lines
    mean_time = valid_times.mean()
    median_time = valid_times.median()
    
    fig.add_vline(x=mean_time, line_dash="dash", line_color="red", 
                  annotation_text=f"Mean: {mean_time:.3f}s")
    fig.add_vline(x=median_time, line_dash="dot", line_color="blue",
                  annotation_text=f"Median: {median_time:.3f}s")
    
    fig.update_layout(template='plotly_white')
    return fig

def create_team_comparison_plot(all_laps: List[dict]) -> go.Figure:
    """Create team comparison plot."""
    if not all_laps:
        return go.Figure().add_annotation(
            text="No data available", 
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
    
    df = pd.DataFrame(all_laps)
    if df.empty or 'team_name' not in df.columns:
        return go.Figure().add_annotation(
            text="No team data available", 
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
    
    df['lap_duration_seconds'] = df['lap_duration'].apply(convert_time_to_seconds)
    
    # Filter valid laps
    valid_df = df[
        (df['lap_duration_seconds'].notna()) & 
        (df['lap_duration_seconds'] > 0) &
        (~df.get('is_pit_out_lap', False))
    ]
    
    if valid_df.empty:
        return go.Figure().add_annotation(
            text="No valid lap data", 
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
    
    # Calculate team averages
    team_avg = valid_df.groupby('team_name')['lap_duration_seconds'].mean().reset_index()
    team_avg = team_avg.sort_values('lap_duration_seconds')
    
    colors = [TEAM_COLORS.get(team, '#888888') for team in team_avg['team_name']]
    
    fig = go.Figure()
    fig.add_bar(x=team_avg['team_name'], y=team_avg['lap_duration_seconds'],
               marker_color=colors,
               name='Average Lap Time',
               text=[f"{t:.3f}s" for t in team_avg['lap_duration_seconds']],
               textposition='outside')
    
    fig.update_layout(
        title="🏆 Average Lap Time by Team",
        xaxis_title="Team",
        yaxis_title="Average Lap Time (seconds)",
        template='plotly_white',
        xaxis_tickangle=-45
    )
    
    return fig

# App Layout
app.layout = html.Div([
    html.Div([
        html.H1("🏎️ F1 Performance Dashboard", className="text-center mb-4"),
        html.P("Real-time F1 telemetry and performance analysis using OpenF1 API", 
               className="text-center text-muted mb-4"),
    ], className="header-section"),
    
    html.Div([
        # Controls Section
        html.Div([
            html.H4("🏁 Race Selection"),
            
            html.Div([
                html.Label("Select Year:"),
                dcc.Dropdown(
                    id='year-dropdown',
                    options=[
                        {'label': '2024', 'value': 2024},
                        {'label': '2023', 'value': 2023}
                    ],
                    value=2024,
                    className="mb-3"
                )
            ]),
            
            html.Div([
                html.Label("Select Grand Prix:"),
                dcc.Dropdown(id='meeting-dropdown', className="mb-3")
            ]),
            
            html.Div([
                html.Label("Select Session:"),
                dcc.Dropdown(id='session-dropdown', className="mb-3")
            ]),
            
            html.Div([
                html.Label("Select Driver:"),
                dcc.Dropdown(id='driver-dropdown', className="mb-3")
            ]),
            
            html.Div(id='session-info', className="mt-3")
            
        ], className="col-md-3"),
        
        # Main Content
        html.Div([
            # Metrics Row
            html.Div(id='metrics-row', className="row mb-4"),
            
            # Charts Section
            dcc.Tabs([
                dcc.Tab(label="📈 Lap Analysis", children=[
                    html.Div([
                        html.Div([
                            dcc.Graph(id='lap-trend-chart')
                        ], className="col-md-6"),
                        html.Div([
                            dcc.Graph(id='lap-distribution-chart')
                        ], className="col-md-6")
                    ], className="row mt-3")
                ]),
                
                dcc.Tab(label="🏆 Team Comparison", children=[
                    html.Div([
                        dcc.Graph(id='team-comparison-chart')
                    ], className="mt-3")
                ]),
                
                dcc.Tab(label="🛞 Tyre Analysis", children=[
                    html.Div([
                        html.P("Tyre analysis will be displayed here when data is available.", 
                               className="text-center mt-5")
                    ])
                ])
            ])
            
        ], className="col-md-9")
        
    ], className="row"),
    
    # Footer
    html.Hr(),
    html.P("Data provided by OpenF1 API | Dashboard built with Dash", 
           className="text-center text-muted")
    
], className="container-fluid p-4")

# Callbacks
@app.callback(
    Output('meeting-dropdown', 'options'),
    Output('meeting-dropdown', 'value'),
    Input('year-dropdown', 'value')
)
def update_meetings(year):
    if not year:
        return [], None
    
    meetings = get_meetings(year)
    if not meetings:
        return [], None
    
    options = [
        {'label': f"{m['meeting_name']} ({m['meeting_country']})", 'value': m['meeting_key']}
        for m in meetings
    ]
    
    # Default to last meeting
    default_value = meetings[-1]['meeting_key'] if meetings else None
    
    return options, default_value

@app.callback(
    Output('session-dropdown', 'options'),
    Output('session-dropdown', 'value'),
    Input('meeting-dropdown', 'value')
)
def update_sessions(meeting_key):
    if not meeting_key:
        return [], None
    
    sessions = get_sessions(meeting_key)
    if not sessions:
        return [], None
    
    options = [
        {'label': f"{s['session_name']} ({s['session_type']})", 'value': s['session_key']}
        for s in sessions
    ]
    
    # Prefer race session, otherwise last session
    race_session = next((s for s in sessions if 'Race' in s['session_name']), None)
    default_value = race_session['session_key'] if race_session else sessions[-1]['session_key']
    
    return options, default_value

@app.callback(
    Output('driver-dropdown', 'options'),
    Output('driver-dropdown', 'value'),
    Input('session-dropdown', 'value')
)
def update_drivers(session_key):
    if not session_key:
        return [], None
    
    drivers = get_drivers(session_key)
    if not drivers:
        return [], None
    
    options = [
        {'label': f"{d['broadcast_name']} ({d['team_name']})", 'value': d['driver_number']}
        for d in drivers
    ]
    
    # Default to first driver
    default_value = drivers[0]['driver_number'] if drivers else None
    
    return options, default_value

@app.callback(
    [Output('session-info', 'children'),
     Output('metrics-row', 'children'),
     Output('lap-trend-chart', 'figure'),
     Output('lap-distribution-chart', 'figure'),
     Output('team-comparison-chart', 'figure')],
    [Input('year-dropdown', 'value'),
     Input('meeting-dropdown', 'value'),
     Input('session-dropdown', 'value'),
     Input('driver-dropdown', 'value')]
)
def update_dashboard(year, meeting_key, session_key, driver_number):
    # Default empty returns
    empty_fig = go.Figure().add_annotation(
        text="Please select all options above", 
        xref="paper", yref="paper",
        x=0.5, y=0.5, showarrow=False
    )
    
    if not all([year, meeting_key, session_key, driver_number]):
        return "", "", empty_fig, empty_fig, empty_fig
    
    # Get session info
    sessions = get_sessions(meeting_key)
    meetings = get_meetings(year)
    drivers = get_drivers(session_key)
    
    selected_session = next((s for s in sessions if s['session_key'] == session_key), None)
    selected_meeting = next((m for m in meetings if m['meeting_key'] == meeting_key), None)
    selected_driver = next((d for d in drivers if d['driver_number'] == driver_number), None)
    
    if not all([selected_session, selected_meeting, selected_driver]):
        return "", "", empty_fig, empty_fig, empty_fig
    
    # Session info
    session_info = html.Div([
        html.H6("Session Info:"),
        html.P(f"📍 Location: {selected_meeting['location']}"),
        html.P(f"🏁 Meeting: {selected_meeting['meeting_name']}"),
        html.P(f"⏱️ Session: {selected_session['session_name']}"),
        html.P(f"🏎️ Driver: {selected_driver['broadcast_name']}"),
        html.P(f"🏆 Team: {selected_driver['team_name']}")
    ])
    
    # Get lap data
    driver_laps = get_laps(session_key, driver_number)
    all_laps_data = get_laps(session_key)
    
    if not driver_laps:
        return session_info, "", empty_fig, empty_fig, empty_fig
    
    # Calculate statistics
    stats = calculate_lap_stats(driver_laps)
    
    # Create metrics
    metrics = html.Div([
        html.Div([
            html.H4(stats.get('fastest', 'N/A')),
            html.P("🏁 Fastest Lap")
        ], className="col-md-3 text-center"),
        html.Div([
            html.H4(stats.get('average', 'N/A')),
            html.P("⚡ Average Lap")
        ], className="col-md-3 text-center"),
        html.Div([
            html.H4(str(len(driver_laps))),
            html.P("📊 Total Laps")
        ], className="col-md-3 text-center"),
        html.Div([
            html.H4(f"{stats.get('consistency', 0):.2f}%"),
            html.P("🎯 Consistency")
        ], className="col-md-3 text-center")
    ], className="row")
    
    # Create charts
    laps_df = pd.DataFrame(driver_laps)
    lap_trend_fig = create_lap_trend_plot(laps_df)
    lap_dist_fig = create_lap_distribution_plot(laps_df)
    team_comp_fig = create_team_comparison_plot(all_laps_data)
    
    return session_info, metrics, lap_trend_fig, lap_dist_fig, team_comp_fig

if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=8050)
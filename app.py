import dash
from dash import dcc, html, Input, Output, callback
import pandas as pd
import logging
from datetime import datetime
import api
import processing
import visualizers

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Dash app
app = dash.Dash(__name__, title="🏎️ F1 Performance Dashboard")
app._favicon = "🏁"

# Define the layout
app.layout = html.Div([
    html.Div([
        html.H1("🏎️ F1 Performance Dashboard", 
                style={'textAlign': 'center', 'color': '#DC143C', 'marginBottom': '30px'}),
        html.P("Real-time F1 telemetry and performance analysis using OpenF1 API",
               style={'textAlign': 'center', 'fontSize': '18px', 'color': '#666'})
    ], style={'padding': '20px'}),
    
    # Control panel
    html.Div([
        html.Div([
            html.Label("Select Year:", style={'fontWeight': 'bold'}),
            dcc.Dropdown(
                id='year-dropdown',
                options=[{'label': str(year), 'value': year} for year in [2024, 2023]],
                value=2024,
                style={'marginBottom': '15px'}
            )
        ], style={'width': '20%', 'display': 'inline-block', 'verticalAlign': 'top', 'marginRight': '2%'}),
        
        html.Div([
            html.Label("Select Grand Prix:", style={'fontWeight': 'bold'}),
            dcc.Dropdown(
                id='meeting-dropdown',
                style={'marginBottom': '15px'}
            )
        ], style={'width': '23%', 'display': 'inline-block', 'verticalAlign': 'top', 'marginRight': '2%'}),
        
        html.Div([
            html.Label("Select Session:", style={'fontWeight': 'bold'}),
            dcc.Dropdown(
                id='session-dropdown',
                style={'marginBottom': '15px'}
            )
        ], style={'width': '23%', 'display': 'inline-block', 'verticalAlign': 'top', 'marginRight': '2%'}),
        
        html.Div([
            html.Label("Select Driver:", style={'fontWeight': 'bold'}),
            dcc.Dropdown(
                id='driver-dropdown',
                style={'marginBottom': '15px'}
            )
        ], style={'width': '28%', 'display': 'inline-block', 'verticalAlign': 'top'})
    ], style={'padding': '20px', 'backgroundColor': '#f8f9fa', 'margin': '20px', 'borderRadius': '10px'}),
    
    # Loading indicator
    dcc.Loading(
        id="loading",
        children=[
            # Key metrics
            html.Div(id='key-metrics', style={'margin': '20px'}),
            
            # Charts
            html.Div([
                dcc.Tabs(id="tabs", value='lap-analysis', children=[
                    dcc.Tab(label='📈 Lap Analysis', value='lap-analysis'),
                    dcc.Tab(label='🏆 Team Comparison', value='team-comparison'),
                    dcc.Tab(label='🛞 Tyre Analysis', value='tyre-analysis'),
                    dcc.Tab(label='⚙️ Advanced', value='advanced')
                ])
            ], style={'margin': '20px'}),
            
            html.Div(id='tab-content', style={'margin': '20px'})
        ],
        type="default"
    ),
    
    # Footer
    html.Div([
        html.Hr(),
        html.P("Data provided by OpenF1 API | Dashboard built with Dash/Plotly",
               style={'textAlign': 'center', 'color': '#888', 'fontSize': '14px'})
    ], style={'marginTop': '50px'})
])

# Callbacks
@callback(
    Output('meeting-dropdown', 'options'),
    Output('meeting-dropdown', 'value'),
    Input('year-dropdown', 'value')
)
def update_meetings(year):
    if not year:
        return [], None
    
    try:
        meetings = api.get_meetings(year)
        options = [{'label': f"{m.meeting_name} ({m.meeting_country})", 'value': m.meeting_key} 
                   for m in meetings]
        value = meetings[-1].meeting_key if meetings else None
        return options, value
    except Exception as e:
        logger.error(f"Error loading meetings: {e}")
        return [], None

@callback(
    Output('session-dropdown', 'options'),
    Output('session-dropdown', 'value'),
    Input('meeting-dropdown', 'value')
)
def update_sessions(meeting_key):
    if not meeting_key:
        return [], None
    
    try:
        sessions = api.get_sessions(meeting_key)
        options = [{'label': f"{s.session_name} ({s.session_type})", 'value': s.session_key} 
                   for s in sessions]
        # Prefer race session or last session
        race_session = next((s for s in sessions if 'race' in s.session_name.lower()), None)
        value = race_session.session_key if race_session else (sessions[-1].session_key if sessions else None)
        return options, value
    except Exception as e:
        logger.error(f"Error loading sessions: {e}")
        return [], None

@callback(
    Output('driver-dropdown', 'options'),
    Output('driver-dropdown', 'value'),
    Input('session-dropdown', 'value')
)
def update_drivers(session_key):
    if not session_key:
        return [], None
    
    try:
        drivers = api.get_drivers(session_key)
        options = [{'label': f"{d.broadcast_name} ({d.team_name})", 'value': d.driver_number} 
                   for d in drivers]
        value = drivers[0].driver_number if drivers else None
        return options, value
    except Exception as e:
        logger.error(f"Error loading drivers: {e}")
        return [], None

@callback(
    Output('key-metrics', 'children'),
    Input('session-dropdown', 'value'),
    Input('driver-dropdown', 'value')
)
def update_key_metrics(session_key, driver_number):
    if not session_key or not driver_number:
        return html.Div("Please select a session and driver.", style={'textAlign': 'center'})
    
    try:
        # Load lap data
        laps = api.get_laps(session_key, driver_number)
        if not laps:
            return html.Div("No lap data available.", style={'textAlign': 'center'})
        
        # Calculate stats
        stats = processing.lap_stats([lap.dict() for lap in laps])
        
        return html.Div([
            html.Div([
                html.H3("🏁", style={'margin': '0', 'color': '#DC143C'}),
                html.H4(stats.get('fastest', 'N/A'), style={'margin': '5px 0'}),
                html.P("Fastest Lap", style={'margin': '0', 'color': '#666'})
            ], style={'textAlign': 'center', 'padding': '20px', 'backgroundColor': '#fff', 
                     'borderRadius': '10px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)',
                     'width': '22%', 'display': 'inline-block', 'margin': '1%'}),
            
            html.Div([
                html.H3("⚡", style={'margin': '0', 'color': '#FFA500'}),
                html.H4(stats.get('average', 'N/A'), style={'margin': '5px 0'}),
                html.P("Average Lap", style={'margin': '0', 'color': '#666'})
            ], style={'textAlign': 'center', 'padding': '20px', 'backgroundColor': '#fff', 
                     'borderRadius': '10px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)',
                     'width': '22%', 'display': 'inline-block', 'margin': '1%'}),
            
            html.Div([
                html.H3("📊", style={'margin': '0', 'color': '#4CAF50'}),
                html.H4(str(len(laps)), style={'margin': '5px 0'}),
                html.P("Total Laps", style={'margin': '0', 'color': '#666'})
            ], style={'textAlign': 'center', 'padding': '20px', 'backgroundColor': '#fff', 
                     'borderRadius': '10px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)',
                     'width': '22%', 'display': 'inline-block', 'margin': '1%'}),
            
            html.Div([
                html.H3("🎯", style={'margin': '0', 'color': '#2196F3'}),
                html.H4(f"{stats.get('consistency', 0):.2f}%", style={'margin': '5px 0'}),
                html.P("Consistency", style={'margin': '0', 'color': '#666'})
            ], style={'textAlign': 'center', 'padding': '20px', 'backgroundColor': '#fff', 
                     'borderRadius': '10px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)',
                     'width': '22%', 'display': 'inline-block', 'margin': '1%'})
        ])
        
    except Exception as e:
        logger.error(f"Error updating key metrics: {e}")
        return html.Div(f"Error loading metrics: {str(e)}", 
                       style={'textAlign': 'center', 'color': 'red'})

@callback(
    Output('tab-content', 'children'),
    Input('tabs', 'value'),
    Input('session-dropdown', 'value'),
    Input('driver-dropdown', 'value')
)
def update_tab_content(active_tab, session_key, driver_number):
    if not session_key or not driver_number:
        return html.Div("Please select a session and driver.")
    
    try:
        if active_tab == 'lap-analysis':
            return render_lap_analysis(session_key, driver_number)
        elif active_tab == 'team-comparison':
            return render_team_comparison(session_key)
        elif active_tab == 'tyre-analysis':
            return render_tyre_analysis(session_key)
        elif active_tab == 'advanced':
            return render_advanced_analysis(session_key, driver_number)
    except Exception as e:
        logger.error(f"Error rendering tab content: {e}")
        return html.Div(f"Error loading content: {str(e)}", style={'color': 'red'})
    
    return html.Div("Select a tab to view content.")

def render_lap_analysis(session_key, driver_number):
    """Render lap analysis tab content."""
    try:
        # Load driver laps
        laps = api.get_laps(session_key, driver_number)
        if not laps:
            return html.Div("No lap data available.")
        
        laps_df = pd.DataFrame([lap.dict() for lap in laps])
        
        # Create visualizations
        lap_trend_fig = visualizers.plot_lap_trend(laps_df)
        distribution_fig = visualizers.plot_distribution(laps_df)
        
        # Find teammate for comparison
        drivers = api.get_drivers(session_key)
        selected_driver = next((d for d in drivers if d.driver_number == driver_number), None)
        teammate = None
        
        if selected_driver:
            teammate = next((d for d in drivers 
                           if d.team_name == selected_driver.team_name and d.driver_number != driver_number), 
                          None)
        
        teammate_content = html.Div("No teammate found for comparison.")
        
        if teammate:
            teammate_laps = api.get_laps(session_key, teammate.driver_number)
            if teammate_laps:
                teammate_df = pd.DataFrame([lap.dict() for lap in teammate_laps])
                delta_df = processing.teammate_deltas(laps_df, teammate_df)
                if not delta_df.empty:
                    delta_fig = visualizers.plot_delta(delta_df)
                    teammate_content = dcc.Graph(figure=delta_fig)
                else:
                    teammate_content = html.Div("No comparable laps found between teammates.")
        
        return html.Div([
            html.Div([
                html.Div([dcc.Graph(figure=lap_trend_fig)], 
                        style={'width': '48%', 'display': 'inline-block'}),
                html.Div([dcc.Graph(figure=distribution_fig)], 
                        style={'width': '48%', 'display': 'inline-block', 'float': 'right'})
            ]),
            html.H3("Teammate Comparison", style={'marginTop': '30px'}),
            teammate_content
        ])
        
    except Exception as e:
        logger.error(f"Error in lap analysis: {e}")
        return html.Div(f"Error: {str(e)}", style={'color': 'red'})

def render_team_comparison(session_key):
    """Render team comparison tab content."""
    try:
        all_laps = api.get_laps(session_key)
        if not all_laps:
            return html.Div("No lap data available for team comparison.")
        
        team_df = processing.team_pace_stats([lap.dict() for lap in all_laps])
        if team_df.empty:
            return html.Div("No team comparison data available.")
        
        team_fig = visualizers.plot_team_comparison(team_df)
        return dcc.Graph(figure=team_fig)
        
    except Exception as e:
        logger.error(f"Error in team comparison: {e}")
        return html.Div(f"Error: {str(e)}", style={'color': 'red'})

def render_tyre_analysis(session_key):
    """Render tyre analysis tab content."""
    try:
        all_laps = api.get_laps(session_key)
        stints = api.get_stints(session_key)
        
        if not all_laps or not stints:
            return html.Div("No tyre data available.")
        
        tyre_df = processing.tyre_degradation(
            [lap.dict() for lap in all_laps],
            [stint.dict() for stint in stints]
        )
        
        if tyre_df.empty:
            return html.Div("No tyre degradation data available.")
        
        compound_fig = visualizers.plot_pace_by_compound(tyre_df)
        degradation_fig = visualizers.plot_degradation_curves(tyre_df)
        
        # Stint timeline
        stint_df = pd.DataFrame([stint.dict() for stint in stints])
        timeline_fig = visualizers.plot_stint_timeline(stint_df)
        
        return html.Div([
            html.Div([
                html.Div([dcc.Graph(figure=compound_fig)], 
                        style={'width': '48%', 'display': 'inline-block'}),
                html.Div([dcc.Graph(figure=degradation_fig)], 
                        style={'width': '48%', 'display': 'inline-block', 'float': 'right'})
            ]),
            dcc.Graph(figure=timeline_fig)
        ])
        
    except Exception as e:
        logger.error(f"Error in tyre analysis: {e}")
        return html.Div(f"Error: {str(e)}", style={'color': 'red'})

def render_advanced_analysis(session_key, driver_number):
    """Render advanced analysis tab content."""
    try:
        # Load data
        driver_laps = api.get_laps(session_key, driver_number)
        all_laps = api.get_laps(session_key)
        
        if not driver_laps:
            return html.Div("No driver data available.")
        
        # Advanced metrics
        advanced_stats = processing.advanced_performance_metrics([lap.dict() for lap in driver_laps])
        
        content = [html.H3("📊 Advanced Performance Metrics")]
        
        if advanced_stats:
            metrics_row = html.Div([
                html.Div([
                    html.P(f"Race Pace: {advanced_stats.get('race_pace', 'N/A')}", 
                          style={'fontSize': '16px', 'margin': '10px'}),
                    html.P(f"Qualifying Pace: {advanced_stats.get('qualifying_pace', 'N/A')}", 
                          style={'fontSize': '16px', 'margin': '10px'}),
                ], style={'width': '48%', 'display': 'inline-block', 'padding': '20px', 
                         'backgroundColor': '#f8f9fa', 'borderRadius': '10px'}),
                
                html.Div([
                    html.P(f"10th Percentile: {advanced_stats.get('p10_laptime', 'N/A')}", 
                          style={'fontSize': '16px', 'margin': '10px'}),
                    html.P(f"90th Percentile: {advanced_stats.get('p90_laptime', 'N/A')}", 
                          style={'fontSize': '16px', 'margin': '10px'}),
                ], style={'width': '48%', 'display': 'inline-block', 'float': 'right', 
                         'padding': '20px', 'backgroundColor': '#f8f9fa', 'borderRadius': '10px'})
            ])
            content.append(metrics_row)
        
        # Sector analysis
        if all_laps:
            try:
                sector_df = processing.sector_stats([lap.dict() for lap in all_laps])
                if not sector_df.empty:
                    sector_fig = visualizers.plot_sector_table(sector_df)
                    content.extend([
                        html.H3("⏱️ Sector Analysis", style={'marginTop': '30px'}),
                        dcc.Graph(figure=sector_fig)
                    ])
            except Exception as e:
                logger.warning(f"Sector analysis failed: {e}")
        
        # Pit stop analysis
        try:
            pits = api.get_pits(session_key)
            if pits:
                pit_df = processing.pit_stats([pit.dict() for pit in pits])
                if not pit_df.empty:
                    pit_fig = visualizers.plot_pit_durations(pit_df)
                    content.extend([
                        html.H3("🔧 Pit Stop Analysis", style={'marginTop': '30px'}),
                        dcc.Graph(figure=pit_fig)
                    ])
        except Exception as e:
            logger.warning(f"Pit analysis failed: {e}")
        
        return html.Div(content)
        
    except Exception as e:
        logger.error(f"Error in advanced analysis: {e}")
        return html.Div(f"Error: {str(e)}", style={'color': 'red'})

def main():
    """Main function to run the app."""
    print("🏎️ Starting F1 Performance Dashboard...")
    
    # Test API connection
    if api.test_api_connection():
        print("✅ API connection successful!")
        print("🚀 Starting dashboard on http://localhost:8050")
        app.run_server(debug=True, host='0.0.0.0', port=8050)
    else:
        print("❌ API connection failed. Please check your internet connection.")

if __name__ == "__main__":
    main()
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import api
import processing
import visualizers
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="🏎️ F1 Performance Dashboard",
    page_icon="🏁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #ff6b6b;
    }
    .stMetric > label {
        font-size: 14px !important;
        font-weight: bold !important;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=600)  # Cache for 10 minutes
def load_meetings(year: int):
    """Load meetings data with caching."""
    try:
        meetings = api.get_meetings(year)
        return meetings
    except Exception as e:
        st.error(f"Failed to load meetings: {e}")
        return []

@st.cache_data(ttl=600)
def load_sessions(meeting_key: int):
    """Load sessions data with caching."""
    try:
        sessions = api.get_sessions(meeting_key)
        return sessions
    except Exception as e:
        st.error(f"Failed to load sessions: {e}")
        return []

@st.cache_data(ttl=600)
def load_drivers(session_key: int):
    """Load drivers data with caching."""
    try:
        drivers = api.get_drivers(session_key)
        return drivers
    except Exception as e:
        st.error(f"Failed to load drivers: {e}")
        return []

@st.cache_data(ttl=300)  # Cache lap data for 5 minutes
def load_lap_data(session_key: int, driver_number: int = None):
    """Load lap data with caching."""
    try:
        laps = api.get_laps(session_key, driver_number)
        return laps
    except Exception as e:
        st.error(f"Failed to load lap data: {e}")
        return []

def main():
    # Title and description
    st.title("🏎️ F1 Performance Dashboard")
    st.markdown("**Real-time F1 telemetry and performance analysis using OpenF1 API**")
    
    # Sidebar for selections
    with st.sidebar:
        st.header("🏁 Race Selection")
        
        # Year selection
        year = st.selectbox("Select Year", [2024, 2023], index=0)
        
        # Load meetings
        with st.spinner("Loading meetings..."):
            meetings = load_meetings(year)
        
        if not meetings:
            st.error("No meetings found for the selected year.")
            return
        
        # Meeting selection
        meeting_options = {f"{m.meeting_name} ({m.meeting_country})": m for m in meetings}
        selected_meeting_name = st.selectbox(
            "Select Grand Prix", 
            list(meeting_options.keys()),
            index=len(meeting_options)-1  # Default to last meeting
        )
        selected_meeting = meeting_options[selected_meeting_name]
        
        # Load sessions
        with st.spinner("Loading sessions..."):
            sessions = load_sessions(selected_meeting.meeting_key)
        
        if not sessions:
            st.error("No sessions found for the selected meeting.")
            return
        
        # Session selection
        session_options = {f"{s.session_name} ({s.session_type})": s for s in sessions}
        selected_session_name = st.selectbox(
            "Select Session", 
            list(session_options.keys()),
            index=max(0, len(session_options)-1)  # Prefer race session
        )
        selected_session = session_options[selected_session_name]
        
        # Load drivers
        with st.spinner("Loading drivers..."):
            drivers = load_drivers(selected_session.session_key)
        
        if not drivers:
            st.error("No drivers found for the selected session.")
            return
        
        # Driver selection
        driver_options = {f"{d.broadcast_name} ({d.team_name})": d for d in drivers}
        selected_driver_name = st.selectbox(
            "Select Driver", 
            list(driver_options.keys())
        )
        selected_driver = driver_options[selected_driver_name]
        
        # Display session info
        st.markdown("---")
        st.markdown("**Session Info:**")
        st.markdown(f"📍 **Location:** {selected_meeting.location}")
        st.markdown(f"🏁 **Meeting:** {selected_meeting.meeting_name}")
        st.markdown(f"⏱️ **Session:** {selected_session.session_name}")
        st.markdown(f"📅 **Date:** {selected_session.date_start.strftime('%Y-%m-%d %H:%M')}")
        st.markdown(f"🏎️ **Driver:** {selected_driver.broadcast_name}")
        st.markdown(f"🏆 **Team:** {selected_driver.team_name}")
    
    # Main content area
    col1, col2, col3 = st.columns(3)
    
    # Load lap data for selected driver
    with st.spinner("Loading lap data..."):
        driver_laps = load_lap_data(selected_session.session_key, selected_driver.driver_number)
    
    if not driver_laps:
        st.warning("No lap data available for the selected driver.")
        return
    
    # Convert to DataFrame
    laps_df = pd.DataFrame([lap.dict() for lap in driver_laps])
    
    # Calculate basic stats
    stats = processing.lap_stats([lap.dict() for lap in driver_laps])
    
    # Display key metrics
    with col1:
        st.metric(
            label="🏁 Fastest Lap",
            value=stats.get('fastest', 'N/A'),
            delta=None
        )
    
    with col2:
        st.metric(
            label="⚡ Average Lap",
            value=stats.get('average', 'N/A'),
            delta=None
        )
    
    with col3:
        st.metric(
            label="📊 Total Laps",
            value=len(driver_laps),
            delta=None
        )
    
    # Create tabs for different analyses
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Lap Analysis", "🏆 Team Comparison", "🛞 Tyre Analysis", "⚙️ Advanced"])
    
    with tab1:
        st.header("Lap Performance Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Lap time trend
            if not laps_df.empty:
                fig_trend = visualizers.plot_lap_trend(laps_df)
                st.plotly_chart(fig_trend, use_container_width=True)
        
        with col2:
            # Lap time distribution
            if not laps_df.empty:
                fig_dist = visualizers.plot_distribution(laps_df)
                st.plotly_chart(fig_dist, use_container_width=True)
        
        # Find and compare with teammate
        st.subheader("Teammate Comparison")
        
        teammate = None
        for driver in drivers:
            if (driver.team_name == selected_driver.team_name and 
                driver.driver_number != selected_driver.driver_number):
                teammate = driver
                break
        
        if teammate:
            teammate_laps = load_lap_data(selected_session.session_key, teammate.driver_number)
            if teammate_laps:
                teammate_df = pd.DataFrame([lap.dict() for lap in teammate_laps])
                delta_df = processing.teammate_deltas(laps_df, teammate_df)
                
                if not delta_df.empty:
                    fig_delta = visualizers.plot_delta(delta_df)
                    st.plotly_chart(fig_delta, use_container_width=True)
                else:
                    st.info("No comparable laps found between teammates.")
            else:
                st.info(f"No lap data available for teammate {teammate.broadcast_name}")
        else:
            st.info("No teammate found for comparison.")
    
    with tab2:
        st.header("Team Performance Comparison")
        
        # Load all laps for team comparison
        with st.spinner("Loading all lap data for team comparison..."):
            all_laps = load_lap_data(selected_session.session_key)
        
        if all_laps:
            team_df = processing.team_pace_stats([lap.dict() for lap in all_laps])
            if not team_df.empty:
                fig_team = visualizers.plot_team_comparison(team_df)
                st.plotly_chart(fig_team, use_container_width=True)
            else:
                st.warning("No team comparison data available.")
        else:
            st.warning("Unable to load data for team comparison.")
    
    with tab3:
        st.header("Tyre Strategy Analysis")
        
        # Load stint data
        with st.spinner("Loading stint data..."):
            try:
                stints = api.get_stints(selected_session.session_key)
                if stints and all_laps:
                    tyre_df = processing.tyre_degradation(
                        [lap.dict() for lap in all_laps],
                        [stint.dict() for stint in stints]
                    )
                    
                    if not tyre_df.empty:
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            fig_compound = visualizers.plot_pace_by_compound(tyre_df)
                            st.plotly_chart(fig_compound, use_container_width=True)
                        
                        with col2:
                            fig_deg = visualizers.plot_degradation_curves(tyre_df)
                            st.plotly_chart(fig_deg, use_container_width=True)
                        
                        # Stint timeline
                        stint_df = pd.DataFrame([stint.dict() for stint in stints])
                        if not stint_df.empty:
                            fig_timeline = visualizers.plot_stint_timeline(stint_df)
                            st.plotly_chart(fig_timeline, use_container_width=True)
                    else:
                        st.warning("No tyre degradation data available.")
                else:
                    st.warning("No stint data available for tyre analysis.")
            except Exception as e:
                st.error(f"Error loading tyre data: {e}")
    
    with tab4:
        st.header("Advanced Analytics")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Sector Performance")
            try:
                sector_df = processing.sector_stats([lap.dict() for lap in all_laps])
                if not sector_df.empty:
                    fig_sectors = visualizers.plot_sector_table(sector_df)
                    st.plotly_chart(fig_sectors, use_container_width=True)
                else:
                    st.warning("No sector data available.")
            except Exception as e:
                st.error(f"Error processing sector data: {e}")
        
        with col2:
            st.subheader("Pit Stop Analysis")
            try:
                pits = api.get_pits(selected_session.session_key)
                if pits:
                    pit_df = processing.pit_stats([pit.dict() for pit in pits])
                    if not pit_df.empty:
                        fig_pits = visualizers.plot_pit_durations(pit_df)
                        st.plotly_chart(fig_pits, use_container_width=True)
                    else:
                        st.warning("No pit stop data available.")
                else:
                    st.warning("No pit stop data found.")
            except Exception as e:
                st.error(f"Error loading pit data: {e}")
        
        # Advanced statistics
        st.subheader("📊 Detailed Statistics")
        advanced_stats = processing.advanced_performance_metrics([lap.dict() for lap in driver_laps])
        
        if advanced_stats:
            metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)
            
            with metrics_col1:
                st.metric("10th Percentile", advanced_stats.get('p10_laptime', 'N/A'))
                st.metric("25th Percentile", advanced_stats.get('p25_laptime', 'N/A'))
            
            with metrics_col2:
                st.metric("75th Percentile", advanced_stats.get('p75_laptime', 'N/A'))
                st.metric("90th Percentile", advanced_stats.get('p90_laptime', 'N/A'))
            
            with metrics_col3:
                st.metric("Race Pace", advanced_stats.get('race_pace', 'N/A'))
                st.metric("Qualifying Pace", advanced_stats.get('qualifying_pace', 'N/A'))
            
            with metrics_col4:
                st.metric("Pace Degradation", f"{advanced_stats.get('pace_degradation', 0):.3f}s")
                st.metric("Consistency Score", f"{stats.get('consistency', 0):.2f}%")

    # Footer
    st.markdown("---")
    st.markdown("*Data provided by OpenF1 API | Dashboard built with Streamlit*")

if __name__ == "__main__":
    main()
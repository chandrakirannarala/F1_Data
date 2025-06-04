import streamlit as st
import pandas as pd
import logging
# Assuming api.py, processing.py, visualizers.py are in the same directory or accessible
import api
import processing
import visualizers

# Configure logging (Streamlit has its own logging, but this can be kept)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="🏎️ F1 Performance Dashboard", page_icon="🏁", layout="wide")

# --- Sidebar Controls ---
st.sidebar.title("🔍 Controls")
selected_year = st.sidebar.selectbox(
    "Select Year:",
    options=[2024, 2023], # Years mentioned in original app.py
    index=0  # Default to 2024
)

# --- Functions to fetch data for dropdowns (adapted from Dash callbacks) ---
def get_meeting_options(year):
    if not year:
        return [], None
    try:
        meetings = api.get_meetings(year) # API call
        # Create a dictionary of display label to meeting_key
        options = {f"{m.meeting_name} ({m.meeting_country})": m.meeting_key for m in meetings}
        # Default to the last meeting if available, as in original app.py
        default_key = meetings[-1].meeting_key if meetings else None
        default_label = next((label for label, key in options.items() if key == default_key), None)
        return options, default_label
    except Exception as e:
        logger.error(f"Error loading meetings: {e}")
        st.sidebar.error(f"Error loading meetings for {year}.")
        return {}, None

meeting_options, default_meeting_label = get_meeting_options(selected_year)
selected_meeting_key = None # Initialize
if meeting_options:
    # Determine index for default selection
    options_list = list(meeting_options.keys())
    default_index = 0
    if default_meeting_label and default_meeting_label in options_list:
        default_index = options_list.index(default_meeting_label)
    
    selected_meeting_label = st.sidebar.selectbox(
        "Select Grand Prix:",
        options=options_list,
        index=default_index
    )
    selected_meeting_key = meeting_options.get(selected_meeting_label)
else:
    st.sidebar.warning("No meetings found for the selected year.")


def get_session_options(meeting_key):
    if not meeting_key:
        return {}, None
    try:
        sessions = api.get_sessions(meeting_key) # API call
        options = {f"{s.session_name} ({s.session_type})": s.session_key for s in sessions}
        # Prefer race session or last session, as in original app.py
        race_session = next((s for s in sessions if 'race' in s.session_name.lower()), None)
        default_key = race_session.session_key if race_session else (sessions[-1].session_key if sessions else None)
        default_label = next((label for label, key in options.items() if key == default_key), None)
        return options, default_label
    except Exception as e:
        logger.error(f"Error loading sessions: {e}")
        st.sidebar.error(f"Error loading sessions for meeting key {meeting_key}.")
        return {}, None

selected_session_key = None # Initialize
if selected_meeting_key:
    session_options, default_session_label = get_session_options(selected_meeting_key)
    if session_options:
        options_list = list(session_options.keys())
        default_index = 0
        if default_session_label and default_session_label in options_list:
            default_index = options_list.index(default_session_label)

        selected_session_label = st.sidebar.selectbox(
            "Select Session:",
            options=options_list,
            index=default_index
        )
        selected_session_key = session_options.get(selected_session_label)
    else:
        st.sidebar.warning("No sessions found for the selected Grand Prix.")
else:
    if selected_year and not meeting_options: # Only show if year was selected but no meetings
        pass # Warning already shown by get_meeting_options
    elif selected_year and meeting_options and not selected_meeting_key :
         st.sidebar.info("Select a Grand Prix.")


def get_driver_options(session_key):
    if not session_key:
        return {}, None
    try:
        drivers = api.get_drivers(session_key) # API call
        options = {f"{d.broadcast_name} ({d.team_name})": d.driver_number for d in drivers}
        # Default to the first driver if available, as in original app.py
        default_key = drivers[0].driver_number if drivers else None
        default_label = next((label for label, key in options.items() if key == default_key), None)
        return options, default_label
    except Exception as e:
        logger.error(f"Error loading drivers: {e}")
        st.sidebar.error(f"Error loading drivers for session key {session_key}.")
        return {}, None

selected_driver_number = None # Initialize
if selected_session_key:
    driver_options, default_driver_label = get_driver_options(selected_session_key)
    if driver_options:
        options_list = list(driver_options.keys())
        default_index = 0
        if default_driver_label and default_driver_label in options_list:
            default_index = options_list.index(default_driver_label)
            
        selected_driver_label = st.sidebar.selectbox(
            "Select Driver:",
            options=options_list,
            index=default_index
        )
        selected_driver_number = driver_options.get(selected_driver_label)
    else:
        st.sidebar.warning("No drivers found for the selected session.")
else:
    if selected_meeting_key and not selected_session_key:
        pass # Warning already shown by get_session_options
    elif selected_meeting_key and selected_session_key and selected_driver_number is None:
        st.sidebar.info("Select a Session with drivers.")


# --- Main Page Layout ---
st.title("🏎️ F1 Performance Dashboard")
st.markdown("Real-time F1 telemetry and performance analysis using OpenF1 API") #

# --- Key Metrics ---
if selected_session_key and selected_driver_number:
    st.header("📊 Key Metrics")
    try:
        with st.spinner("Loading key metrics..."): # Loading indicator
            laps_data = api.get_laps(selected_session_key, selected_driver_number) # API call
            if not laps_data:
                st.warning("No lap data available for key metrics.")
            else:
                # The processing.lap_stats function expects a list of dicts
                stats = processing.lap_stats([lap.dict() for lap in laps_data]) 
                
                cols = st.columns(4)
                cols[0].metric(label="🏁 Fastest Lap", value=stats.get('fastest', 'N/A'))
                cols[1].metric(label="⚡ Average Lap", value=stats.get('average', 'N/A'))
                cols[2].metric(label="📊 Total Laps", value=str(len(laps_data)))
                consistency_val = stats.get('consistency', 0)
                consistency_str = f"{consistency_val:.2f}%" if isinstance(consistency_val, (float, int)) else "N/A"
                cols[3].metric(label="🎯 Consistency", value=consistency_str)

    except Exception as e:
        logger.error(f"Error updating key metrics: {e}")
        st.error(f"Error loading key metrics: {str(e)}")
else:
    st.info("ℹ️ Please select a year, Grand Prix, session, and driver from the sidebar to view metrics and charts.")


# --- Tabs for Charts ---
if selected_session_key and selected_driver_number:
    st.header("📈 Analysis Tabs")
    # Tab structure from original app.py
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Lap Analysis", "🏆 Team Comparison", "🛞 Tyre Analysis", "⚙️ Advanced"])

    with st.spinner("Loading charts..."): # Loading indicator
        with tab1:
            st.subheader("Lap Analysis")
            try:
                laps = api.get_laps(selected_session_key, selected_driver_number) # API call
                if not laps:
                    st.warning("No lap data available for the selected driver.")
                else:
                    laps_df = pd.DataFrame([lap.dict() for lap in laps]) # Convert Pydantic models to DataFrame
                    
                    # Ensure 'lap_duration' (numeric, seconds) is present for visualizers/processing
                    if 'lap_duration' not in laps_df.columns and 'lap_duration_seconds' in laps_df.columns:
                         laps_df['lap_duration'] = laps_df['lap_duration_seconds']
                    elif 'lap_duration' not in laps_df.columns: # If neither, attempt conversion if it's string time
                        laps_df['lap_duration'] = laps_df['lap_duration'].apply(processing.convert_time_to_seconds)


                    if 'lap_duration' in laps_df.columns and not laps_df['lap_duration'].isna().all():
                        lap_trend_fig = visualizers.plot_lap_trend(laps_df) #
                        st.plotly_chart(lap_trend_fig, use_container_width=True)
                        
                        distribution_fig = visualizers.plot_distribution(laps_df) #
                        st.plotly_chart(distribution_fig, use_container_width=True)
                    else:
                        st.warning("Lap duration data missing or invalid for charts.")

                    # Teammate comparison (within lap analysis)
                    st.subheader("Teammate Delta")
                    drivers = api.get_drivers(selected_session_key) # API call
                    selected_driver_details = next((d for d in drivers if d.driver_number == selected_driver_number), None)
                    teammate = None
                    if selected_driver_details:
                        teammate = next((d for d in drivers 
                                       if d.team_name == selected_driver_details.team_name and d.driver_number != selected_driver_number), 
                                      None)
                    
                    if teammate:
                        teammate_laps_data = api.get_laps(selected_session_key, teammate.driver_number) # API call
                        if teammate_laps_data:
                            teammate_df = pd.DataFrame([lap.dict() for lap in teammate_laps_data])
                            
                            # Ensure 'lap_duration' (numeric, seconds) for processing
                            for df_to_check in [laps_df, teammate_df]:
                                if 'lap_duration' not in df_to_check.columns and 'lap_duration_seconds' in df_to_check.columns:
                                    df_to_check['lap_duration'] = df_to_check['lap_duration_seconds']
                                elif 'lap_duration' not in df_to_check.columns:
                                     df_to_check['lap_duration'] = df_to_check['lap_duration'].apply(processing.convert_time_to_seconds)


                            if 'lap_duration' in laps_df.columns and 'lap_duration' in teammate_df.columns:
                                delta_df = processing.teammate_deltas(laps_df, teammate_df) #
                                if not delta_df.empty:
                                    delta_fig = visualizers.plot_delta(delta_df) #
                                    st.plotly_chart(delta_fig, use_container_width=True)
                                else:
                                    st.info("No comparable laps found between teammates for delta analysis.")
                            else:
                                st.warning("Lap duration data missing for selected driver or teammate, cannot calculate delta.")
                        else:
                            st.info(f"No lap data found for teammate ({teammate.broadcast_name}).")
                    else:
                        st.info("No teammate found for comparison or selected driver details missing.")

            except Exception as e:
                logger.error(f"Error in lap analysis tab: {e}")
                st.error(f"Error rendering lap analysis: {str(e)}")

        with tab2:
            st.subheader("Team Comparison")
            try:
                all_laps_data = api.get_laps(selected_session_key) # API call
                if not all_laps_data:
                    st.warning("No lap data available for team comparison.")
                else:
                    all_laps_list = [lap.dict() for lap in all_laps_data]
                    
                    # Add team_name to laps, as processing.team_pace_stats needs it
                    # Lap model itself doesn't have team_name
                    drivers_list_for_teams = api.get_drivers(selected_session_key) # API call
                    driver_to_team_map = {d.driver_number: d.team_name for d in drivers_list_for_teams}

                    for lap_dict in all_laps_list:
                        if 'team_name' not in lap_dict or pd.isna(lap_dict.get('team_name')):
                            lap_dict['team_name'] = driver_to_team_map.get(lap_dict['driver_number'])
                        # Ensure 'lap_duration' is numeric (seconds)
                        if 'lap_duration' not in lap_dict and 'lap_duration_seconds' in lap_dict:
                             lap_dict['lap_duration'] = lap_dict['lap_duration_seconds']
                        elif 'lap_duration' in lap_dict and not isinstance(lap_dict['lap_duration'], (int, float)):
                            lap_dict['lap_duration'] = processing.convert_time_to_seconds(lap_dict['lap_duration'])


                    # Filter out laps without team_name or valid lap_duration
                    filtered_laps_list = [
                        lap for lap in all_laps_list if lap.get('team_name') and pd.notna(lap.get('team_name')) and 'lap_duration' in lap and pd.notna(lap['lap_duration'])
                    ]

                    if not filtered_laps_list:
                         st.warning("Insufficient data for team pace stats after attempting to map team names and validate lap durations.")
                    else:
                        team_df = processing.team_pace_stats(filtered_laps_list) #
                        if team_df.empty:
                            st.info("No team comparison data could be processed.")
                        else:
                            team_fig = visualizers.plot_team_comparison(team_df) #
                            st.plotly_chart(team_fig, use_container_width=True)

                            # Overall team pace ranking
                            overall_df = processing.overall_team_pace(filtered_laps_list)
                            if not overall_df.empty:
                                pace_fig = visualizers.plot_team_pace(overall_df)
                                st.plotly_chart(pace_fig, use_container_width=True)
            except Exception as e:
                logger.error(f"Error in team comparison tab: {e}")
                st.error(f"Error rendering team comparison: {str(e)}")

        with tab3:
            st.subheader("Tyre Analysis")
            try:
                all_laps_data_tyre = api.get_laps(selected_session_key) # API call
                stints_data = api.get_stints(selected_session_key) # API call

                if not all_laps_data_tyre or not stints_data:
                    st.warning("No tyre data (laps or stints) available.")
                else:
                    all_laps_list_tyre = [lap.dict() for lap in all_laps_data_tyre]
                    stints_list = [stint.dict() for stint in stints_data]

                    # Ensure 'lap_duration' is numeric (seconds) in all_laps_list_tyre
                    for lap_dict in all_laps_list_tyre:
                        if 'lap_duration' not in lap_dict and 'lap_duration_seconds' in lap_dict:
                             lap_dict['lap_duration'] = lap_dict['lap_duration_seconds']
                        elif 'lap_duration' in lap_dict and not isinstance(lap_dict['lap_duration'], (int, float)):
                            lap_dict['lap_duration'] = processing.convert_time_to_seconds(lap_dict['lap_duration'])
                    
                    filtered_laps_list_tyre = [lap for lap in all_laps_list_tyre if 'lap_duration' in lap and pd.notna(lap['lap_duration'])]

                    if not filtered_laps_list_tyre:
                        st.warning("Insufficient lap data for tyre degradation analysis after filtering.")
                    else:
                        tyre_df = processing.tyre_degradation(filtered_laps_list_tyre, stints_list) #
                        
                        if tyre_df.empty:
                            st.info("No tyre degradation data could be processed.")
                        else:
                            compound_fig = visualizers.plot_pace_by_compound(tyre_df) #
                            st.plotly_chart(compound_fig, use_container_width=True)
                            
                            degradation_fig = visualizers.plot_degradation_curves(tyre_df) #
                            st.plotly_chart(degradation_fig, use_container_width=True)
                        
                    # Stint timeline (can be plotted even if tyre_df is empty if stints_data exists)
                    stint_df_vis = pd.DataFrame(stints_list) # Stint model has lap_start, lap_end, driver_number, compound
                    if not stint_df_vis.empty and all(col in stint_df_vis.columns for col in ['lap_start', 'lap_end', 'driver_number', 'compound']):
                        timeline_fig = visualizers.plot_stint_timeline(stint_df_vis) #
                        st.plotly_chart(timeline_fig, use_container_width=True)
                    else:
                        st.info("No valid stint data for timeline (missing required columns or empty).")

            except Exception as e:
                logger.error(f"Error in tyre analysis tab: {e}")
                st.error(f"Error rendering tyre analysis: {str(e)}")

        with tab4:
            st.subheader("Advanced Analysis")
            try:
                driver_laps_data_adv = api.get_laps(selected_session_key, selected_driver_number) # API call
                all_laps_data_adv = api.get_laps(selected_session_key) # API call

                if not driver_laps_data_adv:
                    st.warning("No driver data available for advanced metrics.")
                else:
                    driver_laps_list_adv = [lap.dict() for lap in driver_laps_data_adv]
                    # Ensure 'lap_duration' is numeric (seconds)
                    for lap_dict in driver_laps_list_adv:
                         if 'lap_duration' not in lap_dict and 'lap_duration_seconds' in lap_dict:
                             lap_dict['lap_duration'] = lap_dict['lap_duration_seconds']
                         elif 'lap_duration' in lap_dict and not isinstance(lap_dict['lap_duration'], (int, float)):
                            lap_dict['lap_duration'] = processing.convert_time_to_seconds(lap_dict['lap_duration'])

                    
                    filtered_driver_laps_adv = [lap for lap in driver_laps_list_adv if 'lap_duration' in lap and pd.notna(lap['lap_duration'])]

                    if filtered_driver_laps_adv:
                        advanced_stats = processing.advanced_performance_metrics(filtered_driver_laps_adv) #
                        if advanced_stats:
                            st.markdown("#### 📊 Advanced Performance Metrics")
                            cols_adv = st.columns(2)
                            cols_adv[0].markdown(f"**Race Pace:** {advanced_stats.get('race_pace', 'N/A')}")
                            cols_adv[0].markdown(f"**Qualifying Pace:** {advanced_stats.get('qualifying_pace', 'N/A')}")
                            cols_adv[1].markdown(f"**10th Percentile:** {advanced_stats.get('p10_laptime', 'N/A')}")
                            cols_adv[1].markdown(f"**90th Percentile:** {advanced_stats.get('p90_laptime', 'N/A')}")
                        else:
                            st.info("Could not compute advanced performance metrics for the driver.")
                    else:
                         st.warning("Insufficient driver lap data for advanced metrics after filtering (missing valid lap_duration).")


                # Sector analysis
                if all_laps_data_adv:
                    all_laps_list_adv = [lap.dict() for lap in all_laps_data_adv]
                    # processing.sector_stats expects duration_sector_1, etc. which are in Lap model
                    
                    # Quick check for required sector columns in a sample lap if data exists
                    required_sector_cols_present = True
                    if all_laps_list_adv:
                        sample_lap = all_laps_list_adv[0]
                        for i in [1,2,3]:
                            if f'duration_sector_{i}' not in sample_lap:
                                required_sector_cols_present = False
                                break
                    
                    if not all_laps_list_adv or not required_sector_cols_present:
                        st.warning("Sector duration data missing from laps, cannot perform sector analysis.")
                    else:
                        try:
                            # Ensure driver_number is present for grouping in sector_stats
                            laps_with_driver = [lap for lap in all_laps_list_adv if 'driver_number' in lap]
                            if not laps_with_driver:
                                st.warning("Driver number missing from lap data, cannot perform sector analysis.")
                            else:
                                sector_df = processing.sector_stats(laps_with_driver) #
                                if not sector_df.empty:
                                    st.markdown("#### ⏱️ Sector Analysis")
                                    # visualizers.plot_sector_table might need 'driver_number' and sector columns
                                    if 'driver_number' in sector_df.columns and all(f'best_s{i}' in sector_df.columns for i in [1,2,3]):
                                        sector_fig = visualizers.plot_sector_table(sector_df)
                                        st.plotly_chart(sector_fig, use_container_width=True)
                                    else:
                                        st.warning("Processed sector data is missing required columns (driver_number, best_s1/2/3) for visualization.")
                                else:
                                    st.info("No sector stats could be processed.")
                        except Exception as e_sector:
                            logger.warning(f"Sector analysis failed: {e_sector}")
                            st.warning(f"Sector analysis could not be completed: {e_sector}")
                else:
                    st.warning("No lap data available for sector analysis.")


                # Pit stop analysis
                try:
                    pits_data = api.get_pits(selected_session_key) # API call
                    if pits_data:
                        pit_list = [pit.dict() for pit in pits_data]
                        # processing.pit_stats expects 'pit_duration'
                        # Pit model has pit_duration
                        for pit_dict in pit_list:
                             if 'pit_duration' not in pit_dict and pit_dict.get('pit_duration_seconds') is not None:
                                 pit_dict['pit_duration'] = pit_dict['pit_duration_seconds']
                             elif 'pit_duration' in pit_dict and not isinstance(pit_dict['pit_duration'], (int,float)):
                                 pit_dict['pit_duration'] = processing.convert_time_to_seconds(pit_dict['pit_duration'])


                        filtered_pit_list = [pit for pit in pit_list if 'pit_duration' in pit and pd.notna(pit['pit_duration']) and 'driver_number' in pit]

                        if filtered_pit_list:
                            pit_df = processing.pit_stats(filtered_pit_list) #
                            if not pit_df.empty:
                                st.markdown("#### 🔧 Pit Stop Analysis")
                                # visualizers.plot_pit_durations expects 'driver_number', 'avg_pit', 'min_pit', 'max_pit'
                                if all(col in pit_df.columns for col in ['driver_number', 'avg_pit', 'min_pit', 'max_pit']):
                                    pit_fig = visualizers.plot_pit_durations(pit_df)
                                    st.plotly_chart(pit_fig, use_container_width=True)
                                else:
                                    st.warning("Processed pit data is missing required columns for visualization.")
                            else:
                                st.info("No pit stats could be processed.")
                        else:
                            st.warning("Insufficient pit data after filtering (missing 'pit_duration' or 'driver_number').")
                    else:
                        st.info("No pit data available for this session.")
                except Exception as e_pit:
                    logger.warning(f"Pit analysis failed: {e_pit}")
                    st.warning(f"Pit analysis could not be completed: {e_pit}")

            except Exception as e:
                logger.error(f"Error in advanced analysis tab: {e}")
                st.error(f"Error rendering advanced analysis: {str(e)}")

else:
    if not (selected_session_key and selected_driver_number): # Only show if controls not fully selected
        st.info("📊 Select all options from the sidebar to see detailed analysis.")


# --- Footer ---
st.markdown("---")
st.markdown("Data provided by OpenF1 API | Dashboard built with Streamlit/Plotly") #


# Optional: Test API connection button (Original app.py had a test in main)
# if st.sidebar.button("Test API Connection"):
#     with st.spinner("Testing API connection..."):
#         # The api.test_api_connection() function prints to console
#         if api.test_api_connection(): 
#             st.sidebar.success("API connection successful! Check console for details.")
#         else:
#             st.sidebar.error("API connection failed. Check console for details.")
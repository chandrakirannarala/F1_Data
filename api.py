import requests
import pandas as pd
from typing import List, Type, Optional
from cache import fetch_with_cache
from models import Meeting, Session, Driver, Lap, Stint, Pit, CarData
import logging

API_BASE = "https://api.openf1.org/v1"

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fetch_json(path: str, **params) -> List[dict]:
    """
    Fetch raw JSON list from OpenF1 API endpoint.
    No authentication required - it's a free public API.
    """
    url = f"{API_BASE}/{path}"
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Ensure we always return a list
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


def fetch_with_cache_json(path: str, **params) -> List[dict]:
    """
    Wrap fetch_json with caching (Redis + in-memory).
    """
    return fetch_with_cache(
        lambda p, **kw: fetch_json(p, **kw),
        path,
        **params
    )


def _parse_list(data: List[dict], model: Type) -> List:
    """Parse list of dictionaries into Pydantic models with error handling."""
    if not data:
        return []
        
    parsed_items = []
    errors = 0
    
    for item in data:
        try:
            # Handle both v1 and v2 Pydantic models
            if hasattr(model, 'parse_obj'):
                parsed_item = model.parse_obj(item)
            else:
                parsed_item = model(**item)
            parsed_items.append(parsed_item)
        except Exception as e:
            errors += 1
            if errors <= 3:  # Only log first few errors to avoid spam
                logger.warning(f"Failed to parse {model.__name__}: {e}")
                logger.debug(f"Problematic data: {item}")
    
    if errors > 0:
        logger.info(f"Successfully parsed {len(parsed_items)}/{len(data)} {model.__name__} items ({errors} errors)")
    
    return parsed_items


def get_meetings(year: int) -> List[Meeting]:
    """Get all meetings for a specific year."""
    data = fetch_with_cache_json("meetings", year=year)
    return _parse_list(data, Meeting)


def get_sessions(meeting_key: int) -> List[Session]:
    """Get all sessions for a specific meeting."""
    data = fetch_with_cache_json("sessions", meeting_key=meeting_key)
    return _parse_list(data, Session)


def get_drivers(session_key: int) -> List[Driver]:
    """Get all drivers for a specific session."""
    data = fetch_with_cache_json("drivers", session_key=session_key)
    return _parse_list(data, Driver)


def get_laps(session_key: int, driver_number: Optional[int] = None) -> List[Lap]:
    """Get lap data for a session, optionally filtered by driver."""
    params = {"session_key": session_key}
    if driver_number is not None:
        params["driver_number"] = driver_number
    data = fetch_with_cache_json("laps", **params)
    return _parse_list(data, Lap)


def get_stints(session_key: int, driver_number: Optional[int] = None) -> List[Stint]:
    """Get stint data for a session, optionally filtered by driver."""
    params = {"session_key": session_key}
    if driver_number is not None:
        params["driver_number"] = driver_number
    data = fetch_with_cache_json("stints", **params)
    return _parse_list(data, Stint)


def get_pits(session_key: int, driver_number: Optional[int] = None) -> List[Pit]:
    """Get pit stop data for a session, optionally filtered by driver."""
    params = {"session_key": session_key}
    if driver_number is not None:
        params["driver_number"] = driver_number
    data = fetch_with_cache_json("pit", **params)
    return _parse_list(data, Pit)


def get_car_data(session_key: int, driver_number: Optional[int] = None, 
                 speed_min: Optional[int] = None, speed_max: Optional[int] = None) -> List[CarData]:
    """
    Get car telemetry data (speed, RPM, gear, etc.) at ~3.7Hz sample rate.
    Can filter by driver and speed range.
    """
    params = {"session_key": session_key}
    if driver_number is not None:
        params["driver_number"] = driver_number
    if speed_min is not None:
        params["speed>="] = speed_min
    if speed_max is not None:
        params["speed<="] = speed_max
    
    data = fetch_with_cache_json("car_data", **params)
    return _parse_list(data, CarData)


def get_position_data(session_key: int, driver_number: Optional[int] = None) -> List[dict]:
    """Get position data (X, Y, Z coordinates) for drivers."""
    params = {"session_key": session_key}
    if driver_number is not None:
        params["driver_number"] = driver_number
    return fetch_with_cache_json("position", **params)


def get_weather_data(session_key: int) -> List[dict]:
    """Get weather data for a session."""
    return fetch_with_cache_json("weather", session_key=session_key)


def get_race_control(session_key: int) -> List[dict]:
    """Get race control messages (flags, penalties, etc.)."""
    return fetch_with_cache_json("race_control", session_key=session_key)


def models_to_dataframe(models: List, include_columns: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Convert list of Pydantic models to pandas DataFrame.
    
    Args:
        models: List of Pydantic model instances
        include_columns: Optional list of columns to include (filters others out)
    
    Returns:
        pandas DataFrame
    """
    if not models:
        return pd.DataFrame()
    
    # Convert models to dictionaries
    data = []
    for model in models:
        if hasattr(model, 'dict'):
            # Pydantic v1
            model_dict = model.dict()
        elif hasattr(model, 'model_dump'):
            # Pydantic v2
            model_dict = model.model_dump()
        else:
            # Fallback - try to convert to dict
            model_dict = dict(model)
        
        # Filter columns if specified
        if include_columns:
            model_dict = {k: v for k, v in model_dict.items() if k in include_columns}
        
        data.append(model_dict)
    
    df = pd.DataFrame(data)
    
    # Convert time strings to seconds if needed
    time_columns = ['lap_duration', 'duration_sector_1', 'duration_sector_2', 'duration_sector_3', 'pit_duration']
    for col in time_columns:
        if col in df.columns:
            df[col] = df[col].apply(_convert_time_to_seconds)
    
    return df


def _convert_time_to_seconds(time_value):
    """
    Convert time value to seconds (float).
    Handles various formats: float, int, "MM:SS.mmm", None
    """
    if pd.isna(time_value) or time_value is None:
        return None
    
    if isinstance(time_value, (int, float)):
        return float(time_value)
    
    if isinstance(time_value, str):
        try:
            # Handle format like "1:23.456" or "83.456"
            if ':' in time_value:
                parts = time_value.split(':')
                minutes = float(parts[0])
                seconds = float(parts[1])
                return minutes * 60 + seconds
            else:
                return float(time_value)
        except (ValueError, IndexError):
            logger.warning(f"Could not convert time value to seconds: {time_value}")
            return None
    
    return None


def test_api_connection():
    """Test API connectivity and data availability."""
    try:
        meetings = get_meetings(2024)
        if meetings:
            print(f"✓ API connection successful - found {len(meetings)} meetings for 2024")
            
            # Test a specific session
            latest_meeting = meetings[-1]
            sessions = get_sessions(latest_meeting.meeting_key)
            print(f"✓ Found {len(sessions)} sessions for {latest_meeting.meeting_name}")
            
            if sessions:
                drivers = get_drivers(sessions[0].session_key)
                print(f"✓ Found {len(drivers)} drivers in first session")
                
                # Test data conversion
                if drivers:
                    drivers_df = models_to_dataframe(drivers)
                    print(f"✓ Successfully converted {len(drivers_df)} drivers to DataFrame")
                
            return True
        else:
            print("⚠ No meetings found for 2024")
            return False
            
    except Exception as e:
        print(f"✗ API test failed: {e}")
        return False


if __name__ == "__main__":
    test_api_connection()
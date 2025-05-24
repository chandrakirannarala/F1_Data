from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class Meeting(BaseModel):
    meeting_key: int
    year: int
    meeting_name: str
    meeting_country: str
    meeting_circuit: str
    date_start: datetime
    gmt_offset: str
    meeting_official_name: str
    location: str

class Session(BaseModel):
    session_key: int
    meeting_key: int
    session_name: str
    session_type: str
    date_start: datetime
    date_end: datetime
    gmt_offset: str
    country_code: str
    country_key: int
    country_name: str
    circuit_key: int
    circuit_short_name: str

class Driver(BaseModel):
    driver_number: int
    session_key: int
    broadcast_name: str
    full_name: str
    name_acronym: str
    team_name: str
    team_colour: Optional[str] = None
    first_name: str
    last_name: str
    headshot_url: Optional[str] = None
    country_code: Optional[str] = None

class Lap(BaseModel):
    session_key: int
    driver_number: int
    date_start: datetime
    lap_number: int
    lap_duration: Optional[float] = None  # in seconds
    duration_sector_1: Optional[float] = None
    duration_sector_2: Optional[float] = None
    duration_sector_3: Optional[float] = None
    segments_sector_1: Optional[list] = None
    segments_sector_2: Optional[list] = None
    segments_sector_3: Optional[list] = None
    is_pit_out_lap: Optional[bool] = None
    st_speed: Optional[float] = None
    i1_speed: Optional[float] = None
    i2_speed: Optional[float] = None
    fl_speed: Optional[float] = None

class Stint(BaseModel):
    session_key: int
    driver_number: int
    stint_number: int
    compound: str
    lap_start: int
    lap_end: int
    tyre_age_at_start: int

class Pit(BaseModel):
    session_key: int
    driver_number: int
    date: datetime
    lap_number: int
    pit_duration: Optional[float] = None  # in seconds

class CarData(BaseModel):
    """
    Car telemetry data sampled at ~3.7Hz
    Contains speed, RPM, gear, throttle, brake, DRS status
    """
    session_key: int
    driver_number: int
    date: datetime
    speed: Optional[float] = None
    rpm: Optional[int] = None
    n_gear: Optional[int] = None
    throttle: Optional[float] = None  # 0-100%
    brake: Optional[bool] = None
    drs: Optional[int] = None  # 0=closed, 1=open
    
class Position(BaseModel):
    """
    Car position data with X, Y, Z coordinates
    """
    session_key: int
    driver_number: int 
    date: datetime
    x: float
    y: float
    z: float

class Weather(BaseModel):
    """
    Weather conditions during session
    """
    session_key: int
    date: datetime
    air_temperature: Optional[float] = None
    humidity: Optional[float] = None
    pressure: Optional[float] = None
    rainfall: Optional[bool] = None
    track_temperature: Optional[float] = None
    wind_direction: Optional[int] = None
    wind_speed: Optional[float] = None

class RaceControl(BaseModel):
    """
    Race control messages, flags, penalties
    """
    session_key: int
    date: datetime
    lap_number: Optional[int] = None
    driver_number: Optional[int] = None
    message: str
    category: Optional[str] = None
    flag: Optional[str] = None
    scope: Optional[str] = None
    sector: Optional[int] = None
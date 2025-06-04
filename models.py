from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional, Union
import pandas as pd

class Meeting(BaseModel):
    meeting_key: int
    year: int
    meeting_name: str
    meeting_country: Optional[str] = None # Made Optional
    meeting_circuit: Optional[str] = None # Made Optional
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
    country_code: str # Assuming this comes from session data, not meeting directly for display
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
    date_start: Optional[datetime] = None
    lap_number: int
    lap_duration: Optional[float] = None
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
    
    @validator('date_start', pre=True)
    def validate_date_start(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            try:
                return pd.to_datetime(v)
            except:
                return None
        return v

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
    date: Optional[datetime] = None
    lap_number: int
    pit_duration: Optional[float] = None
    
    @validator('date', pre=True)
    def validate_date(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            try:
                return pd.to_datetime(v)
            except:
                return None
        return v

class CarData(BaseModel):
    session_key: int
    driver_number: int
    date: Optional[datetime] = None
    speed: Optional[float] = None
    rpm: Optional[int] = None
    n_gear: Optional[int] = None
    throttle: Optional[float] = None
    brake: Optional[bool] = None
    drs: Optional[int] = None
    
    @validator('date', pre=True)
    def validate_date_car(cls, v): # Renamed validator to avoid conflict if copy-pasting
        if v is None:
            return None
        if isinstance(v, str):
            try:
                return pd.to_datetime(v)
            except:
                return None
        return v
    
class Position(BaseModel):
    session_key: int
    driver_number: int 
    date: Optional[datetime] = None
    x: float
    y: float
    z: float
    
    @validator('date', pre=True)
    def validate_date_position(cls, v): # Renamed validator
        if v is None:
            return None
        if isinstance(v, str):
            try:
                return pd.to_datetime(v)
            except:
                return None
        return v

class Weather(BaseModel):
    session_key: int
    date: Optional[datetime] = None
    air_temperature: Optional[float] = None
    humidity: Optional[float] = None
    pressure: Optional[float] = None
    rainfall: Optional[bool] = None
    track_temperature: Optional[float] = None
    wind_direction: Optional[int] = None
    wind_speed: Optional[float] = None
    
    @validator('date', pre=True)
    def validate_date_weather(cls, v): # Renamed validator
        if v is None:
            return None
        if isinstance(v, str):
            try:
                return pd.to_datetime(v)
            except:
                return None
        return v

class RaceControl(BaseModel):
    session_key: int
    date: Optional[datetime] = None
    lap_number: Optional[int] = None
    driver_number: Optional[int] = None
    message: str
    category: Optional[str] = None
    flag: Optional[str] = None
    scope: Optional[str] = None
    sector: Optional[int] = None
    
    @validator('date', pre=True)
    def validate_date_racecontrol(cls, v): # Renamed validator
        if v is None:
            return None
        if isinstance(v, str):
            try:
                return pd.to_datetime(v)
            except:
                return None
        return v
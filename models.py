from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class Meeting(BaseModel):
    meeting_key: str
    year: int
    meeting_name: str
    country_name: str
    circuit_short_name: str

class Session(BaseModel):
    session_key: str
    meeting_key: str
    session_name: str
    session_type: str
    date_start: datetime
    date_end: datetime

class Driver(BaseModel):
    driver_number: int
    session_key: str
    full_name: str
    team_name: str
    team_colour: Optional[str]

class Lap(BaseModel):
    session_key: str
    driver_number: int
    lap_number: int
    lap_duration: str
    duration_sector_1: Optional[str]
    duration_sector_2: Optional[str]
    duration_sector_3: Optional[str]
    is_pit_out_lap: Optional[bool]
    st_speed: Optional[float]
    i1_speed: Optional[float]
    i2_speed: Optional[float]

class Stint(BaseModel):
    session_key: str
    driver_number: int
    stint_number: int
    compound: str
    lap_start: int
    lap_end: int
    tyre_age_at_start: int

class Pit(BaseModel):
    session_key: str
    driver_number: int
    lap_number: int
    pit_duration: str
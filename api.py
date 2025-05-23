import os
from typing import List, Type
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import BackendApplicationClient
from cache import fetch_with_cache
from models import Meeting, Session, Driver, Lap, Stint, Pit

API_BASE = "https://api.openf1.org/v1"


def get_oauth_session(client_id: str = None, client_secret: str = None) -> OAuth2Session:
    """
    Create an OAuth2Session using client credentials grant.
    Expects OPENF1_CLIENT_ID and OPENF1_CLIENT_SECRET in env if not passed.
    """
    client_id = client_id or os.getenv("OPENF1_CLIENT_ID")
    client_secret = client_secret or os.getenv("OPENF1_CLIENT_SECRET")
    client = BackendApplicationClient(client_id=client_id)
    oauth = OAuth2Session(client=client)
    oauth.fetch_token(
        token_url="https://api.openf1.org/oauth2/token",
        client_id=client_id,
        client_secret=client_secret
    )
    return oauth


def fetch_json(oauth: OAuth2Session, path: str, **params) -> List[dict]:
    """Fetch raw JSON list from given API endpoint."""
    url = f"{API_BASE}/{path}"
    resp = oauth.get(url, params=params)
    resp.raise_for_status()
    return resp.json()


def fetch_with_cache_json(oauth: OAuth2Session, path: str, **params) -> List[dict]:
    """
    Wrap fetch_json with caching (Redis + in-memory).
    """
    return fetch_with_cache(
        lambda p, **kw: fetch_json(oauth, p, **kw),
        path,
        **params
    )


def _parse_list(data: List[dict], model: Type) -> List:
    return [model.parse_obj(item) for item in data]


def get_meetings(oauth: OAuth2Session, year: int) -> List[Meeting]:
    data = fetch_with_cache_json(oauth, "meetings", year=year)
    return _parse_list(data, Meeting)


def get_sessions(oauth: OAuth2Session, meeting_key: str) -> List[Session]:
    data = fetch_with_cache_json(oauth, "sessions", meeting_key=meeting_key)
    return _parse_list(data, Session)


def get_drivers(oauth: OAuth2Session, session_key: str) -> List[Driver]:
    data = fetch_with_cache_json(oauth, "drivers", session_key=session_key)
    return _parse_list(data, Driver)


def get_laps(oauth: OAuth2Session, session_key: str, driver_number: int = None) -> List[Lap]:
    params = {"session_key": session_key}
    if driver_number is not None:
        params["driver_number"] = driver_number
    data = fetch_with_cache_json(oauth, "laps", **params)
    return _parse_list(data, Lap)


def get_stints(oauth: OAuth2Session, session_key: str, driver_number: int = None) -> List[Stint]:
    params = {"session_key": session_key}
    if driver_number is not None:
        params["driver_number"] = driver_number
    data = fetch_with_cache_json(oauth, "stints", **params)
    return _parse_list(data, Stint)


def get_pits(oauth: OAuth2Session, session_key: str, driver_number: int = None) -> List[Pit]:
    params = {"session_key": session_key}
    if driver_number is not None:
        params["driver_number"] = driver_number
    data = fetch_with_cache_json(oauth, "pit", **params)
    return _parse_list(data, Pit)
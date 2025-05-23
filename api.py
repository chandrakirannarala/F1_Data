import requests
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session

API_BASE = "https://api.openf1.org/v1"

def get_token(client_id: str, client_secret: str) -> OAuth2Session:
    client = BackendApplicationClient(client_id=client_id)
    oauth = OAuth2Session(client=client)
    token = oauth.fetch_token(token_url="https://api.openf1.org/oauth2/token",
                              client_id=client_id,
                              client_secret=client_secret)
    return oauth

def fetch_json(oauth: OAuth2Session, path: str, **params):
    url = f"{API_BASE}/{path}"
    r = oauth.get(url, params=params)
    r.raise_for_status()
    return r.json()

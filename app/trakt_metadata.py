import logging
import json
import time
import os
import pickle
from typing import Dict, Any, List, Tuple
from urllib.parse import urlparse, urlencode
import requests
from app.settings import Settings
import trakt.core
from trakt import init
from trakt.users import User
from trakt.movies import Movie
from trakt.tv import TVShow
from flask import url_for
from datetime import datetime, timedelta
import iso8601
from datetime import timezone

TRAKT_API_URL = "https://api.trakt.tv"
CACHE_FILE = 'db_content/trakt_last_activity.pkl'
REQUEST_TIMEOUT = 10  # seconds

class TraktMetadata:
    def __init__(self):
        self.settings = Settings()
        self.base_url = "https://api.trakt.tv"
        self.client_id = self.settings.Trakt.get('client_id')
        self.client_secret = self.settings.Trakt.get('client_secret')
        self.redirect_uri = "http://192.168.1.51:5001/trakt_callback"

        # Log Trakt settings for debugging
        logging.info(f"Trakt settings: client_id={self.client_id}, client_secret={'*' * len(self.client_secret) if self.client_secret else 'Not set'}")

    def load_trakt_credentials(self) -> Dict[str, str]:
        try:
            with open('config/.pytrakt.json', 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            logging.error("Trakt credentials file not found.")
            return {}
        except json.JSONDecodeError:
            logging.error("Error decoding Trakt credentials file.")
            return {}

    def get_trakt_headers(self) -> Dict[str, str]:
        client_id = self.credentials.get('CLIENT_ID')
        access_token = self.credentials.get('OAUTH_TOKEN')
        if not client_id or not access_token:
            logging.error("Trakt API credentials not set. Please configure in settings.")
            return {}
        return {
            'Content-Type': 'application/json',
            'trakt-api-version': '2',
            'trakt-api-key': client_id,
            'Authorization': f'Bearer {access_token}'
        }

    def ensure_trakt_auth(self):
        if not self.client_id or not self.client_secret:
            raise ValueError("Trakt client ID and secret must be set")
        if self.is_authenticated():
            return None
        return self.get_device_code()

    def get_device_code(self, client_id: str, client_secret: str) -> Dict[str, Any]:
        url = f"{TRAKT_API_URL}/oauth/device/code"
        data = {
            "client_id": client_id
        }
        response = requests.post(url, json=data, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json()

    def fetch_items_from_trakt(self, endpoint: str) -> List[Dict[str, Any]]:
        if not self.headers:
            return []

        full_url = f"{TRAKT_API_URL}{endpoint}"
        logging.debug(f"Fetching items from Trakt URL: {full_url}")

        try:
            response = requests.get(full_url, headers=self.headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching items from Trakt: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logging.error(f"Response text: {e.response.text}")
            return []

    def get_metadata(self, imdb_id: str) -> Dict[str, Any]:
        show_data = self._get_show_data(imdb_id)
        if show_data:
            return {
                'type': 'show',
                'metadata': show_data
            }

        movie_data = self._get_movie_data(imdb_id)
        if movie_data:
            return {
                'type': 'movie',
                'metadata': movie_data
            }

        return None

    def _get_show_data(self, imdb_id):
        url = f"{self.base_url}/shows/{imdb_id}?extended=full"
        response = self._make_request(url)
        if response and response.status_code == 200:
            return response.json()
        return None

    def _get_movie_data(self, imdb_id):
        url = f"{self.base_url}/movies/{imdb_id}?extended=full"
        response = self._make_request(url)
        if response and response.status_code == 200:
            return response.json()
        return None

    def get_show_seasons(self, imdb_id):
        url = f"{self.base_url}/shows/{imdb_id}/seasons?extended=full"
        response = self._make_request(url)
        if response and response.status_code == 200:
            seasons_data = response.json()
            processed_seasons = []
            for season in seasons_data:
                if season['number'] is not None and season['number'] > 0:
                    processed_seasons.append({
                        'season': season['number'],
                        'episode_count': season.get('episode_count', 0),
                        'aired_episodes': season.get('aired_episodes', 0),
                        'title': season.get('title', f"Season {season['number']}"),
                        'overview': season.get('overview', ''),
                    })
            return processed_seasons
        return None

    def get_show_episodes(self, imdb_id):
        url = f"{self.base_url}/shows/{imdb_id}/seasons?extended=full,episodes"
        response = self._make_request(url)
        if response and response.status_code == 200:
            seasons_data = response.json()
            processed_episodes = []
            for season in seasons_data:
                if season['number'] is not None and season['number'] > 0:
                    for episode in season.get('episodes', []):
                        first_aired = None
                        if episode.get('first_aired'):
                            try:
                                first_aired = datetime.strptime(episode['first_aired'], "%Y-%m-%dT%H:%M:%S.%fZ")
                            except ValueError:
                                # If the format is different, try without milliseconds
                                first_aired = datetime.strptime(episode['first_aired'], "%Y-%m-%dT%H:%M:%SZ")

                        processed_episodes.append({
                            'season': season['number'],
                            'episode': episode['number'],
                            'title': episode.get('title', ''),
                            'overview': episode.get('overview', ''),
                            'runtime': episode.get('runtime', 0),
                            'first_aired': first_aired,  # Now a datetime object
                        })
            return processed_episodes
        return None

    def _make_request(self, url):
        headers = {
            'Content-Type': 'application/json',
            'trakt-api-version': '2',
            'trakt-api-key': self.client_id,
            'Authorization': f'Bearer {self.settings.Trakt["access_token"]}'
        }
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logging.error(f"Error making request to Trakt API: {e}")
            logging.error(f"URL: {url}")
            logging.error(f"Headers: {headers}")
            if hasattr(e, 'response') and e.response is not None:
                logging.error(f"Response status code: {e.response.status_code}")
                logging.error(f"Response text: {e.response.text}")
            return None

    def refresh_metadata(self, imdb_id: str) -> Dict[str, Any]:
        return self.get_metadata(imdb_id)

    def get_authorization_url(self):
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
        }
        auth_url = f"{self.base_url}/oauth/authorize?{urlencode(params)}"
        logging.info(f"Generated Trakt authorization URL: {auth_url}")
        return auth_url

    def exchange_code_for_token(self, code):
        data = {
            'code': code,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_uri': self.redirect_uri,
            'grant_type': 'authorization_code'
        }
        response = requests.post(f"{self.base_url}/oauth/token", json=data)
        if response.status_code == 200:
            token_data = response.json()
            self.save_token_data(token_data)
            return True
        else:
            logging.error(f"Failed to exchange code for token: {response.text}")
            return False

    def save_token_data(self, token_data):
        self.settings.Trakt['access_token'] = token_data['access_token']
        self.settings.Trakt['refresh_token'] = token_data['refresh_token']
        self.settings.Trakt['expires_at'] = (datetime.now() + timedelta(seconds=token_data['expires_in'])).isoformat()
        self.settings.save_settings()
        logging.info("Trakt token data saved successfully.")

    def save_trakt_credentials(self):
        credentials = {
            'ACCESS_TOKEN': trakt.core.OAUTH_TOKEN,
            'REFRESH_TOKEN': trakt.core.OAUTH_REFRESH,
            'EXPIRES_AT': trakt.core.OAUTH_EXPIRES_AT
        }
        with open('config/.pytrakt.json', 'w') as f:
            json.dump(credentials, f)

    def is_authenticated(self):
        access_token = self.settings.Trakt.get('access_token')
        expires_at = self.settings.Trakt.get('expires_at')
        if not access_token or not expires_at:
            return False
        expires_at = iso8601.parse_date(expires_at)
        now = datetime.now(timezone.utc)
        return now < expires_at.astimezone(timezone.utc)

    def get_movie_metadata(self, imdb_id):
        headers = {
            'Content-Type': 'application/json',
            'trakt-api-version': '2',
            'trakt-api-key': self.client_id,
            'Authorization': f'Bearer {self.settings.Trakt["access_token"]}'
        }
        response = requests.get(f"{self.base_url}/movies/{imdb_id}?extended=full", headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            logging.error(f"Failed to fetch movie metadata from Trakt: {response.text}")
            return None

    def get_poster(self, imdb_id: str) -> str:
        return "Posters not available through Trakt API"

# Add this to your MetadataManager class
def refresh_trakt_metadata(self, imdb_id: str) -> None:
    trakt = TraktMetadata()
    new_metadata = trakt.refresh_metadata(imdb_id)
    if new_metadata:
        for key, value in new_metadata.items():
            self.add_or_update_metadata(imdb_id, key, value, 'Trakt')
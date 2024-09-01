import logging
import json
import time
import os
import pickle
from typing import Dict, Any, List, Tuple
from urllib.parse import urlparse, urlencode
import requests
from settings import Settings
import trakt.core
from trakt import init
from trakt.users import User
from trakt.movies import Movie
from trakt.tv import TVShow
from flask import url_for
from datetime import datetime, timedelta

TRAKT_API_URL = "https://api.trakt.tv"
CACHE_FILE = 'db_content/trakt_last_activity.pkl'
REQUEST_TIMEOUT = 10  # seconds

class TraktMetadata:
    def __init__(self):
        self.settings = Settings()
        self.base_url = "https://api.trakt.tv"
        self.client_id = self.settings.Trakt['client_id']
        self.client_secret = self.settings.Trakt['client_secret']
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
        logging.info("Starting Trakt authentication check")
        
        client_id = self.settings.get('Trakt', 'client_id')
        client_secret = self.settings.get('Trakt', 'client_secret')
        
        logging.info(f"Client ID: {client_id}, Client Secret: {'*' * len(client_secret) if client_secret else 'Not set'}")
        
        if not client_id or not client_secret:
            logging.error("Trakt client ID or secret not set. Please configure in settings.")
            return None
        
        try:
            device_code_response = self.get_device_code(client_id, client_secret)
            user_code = device_code_response['user_code']
            device_code = device_code_response['device_code']
            verification_url = device_code_response['verification_url']
            
            logging.info(f"Authorization code generated: {user_code}")
            logging.info(f"Verification URL: {verification_url}")
            
            return {
                'user_code': user_code,
                'device_code': device_code,
                'verification_url': verification_url
            }
        except Exception as e:
            logging.error(f"Error during Trakt authorization: {str(e)}")
            return None

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
        # Try to get movie metadata first
        movie_metadata = self.get_movie_metadata(imdb_id)
        if movie_metadata:
            return {'type': 'movie', 'metadata': movie_metadata}
        
        # If not a movie, try to get TV show metadata
        show_metadata = self.get_show_metadata(imdb_id)
        if show_metadata:
            return {'type': 'show', 'metadata': show_metadata}
        
        return None

    def get_movie_metadata(self, imdb_id):
        headers = self._get_headers()
        response = requests.get(f"{self.base_url}/movies/{imdb_id}?extended=full", headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            logging.error(f"Failed to fetch movie metadata from Trakt: {response.text}")
            return None

    def get_show_metadata(self, imdb_id):
        headers = self._get_headers()
        response = requests.get(f"{self.base_url}/shows/{imdb_id}?extended=full", headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            logging.error(f"Failed to fetch show metadata from Trakt: {response.text}")
            return None

    def get_show_seasons(self, imdb_id):
        headers = self._get_headers()
        response = requests.get(f"{self.base_url}/shows/{imdb_id}/seasons?extended=full,episodes", headers=headers)
        
        if response.status_code == 200:
            seasons_data = response.json()
            for season in seasons_data:
                if 'episodes' in season:
                    for episode in season['episodes']:
                        episode['airdate'] = self._parse_date(episode.get('first_aired'))
            return seasons_data
        else:
            logging.error(f"Failed to fetch show seasons from Trakt: {response.text}")
            return None

    def _parse_date(self, date_string):
        if date_string:
            try:
                return datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S.%fZ")
            except ValueError:
                return None
        return None

    def _get_headers(self):
        return {
            'Content-Type': 'application/json',
            'trakt-api-version': '2',
            'trakt-api-key': self.client_id,
            'Authorization': f'Bearer {self.settings.Trakt["access_token"]}'
        }

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
        return (
            self.settings.Trakt.get('access_token') and
            self.settings.Trakt.get('expires_at') and
            datetime.fromisoformat(self.settings.Trakt['expires_at']) > datetime.now()
        )

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

# Add this to your MetadataManager class
def refresh_trakt_metadata(self, imdb_id: str) -> None:
    trakt = TraktMetadata()
    new_metadata = trakt.refresh_metadata(imdb_id)
    if new_metadata:
        for key, value in new_metadata.items():
            self.add_or_update_metadata(imdb_id, key, value, 'Trakt')
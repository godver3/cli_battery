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
from collections import defaultdict
from app.trakt_auth import TraktAuth

TRAKT_API_URL = "https://api.trakt.tv"
CACHE_FILE = 'db_content/trakt_last_activity.pkl'
REQUEST_TIMEOUT = 10  # seconds
trakt_auth = TraktAuth()

class TraktMetadata:
    def __init__(self):
        self.settings = Settings()
        self.base_url = "https://api.trakt.tv"
        self.client_id = self.settings.Trakt.get('client_id')
        self.client_secret = self.settings.Trakt.get('client_secret')
        self.redirect_uri = "http://192.168.1.51:5001/trakt_callback"
        self.access_token = self.settings.Trakt.get('access_token')
        self.refresh_token = self.settings.Trakt.get('refresh_token')
        self.expires_at = self.settings.Trakt.get('expires_at')

        logging.info(f"Trakt settings: client_id={self.client_id}, client_secret={'*' * len(self.client_secret) if self.client_secret else 'Not set'}")

    def _make_request(self, url):
        if not trakt_auth.is_authenticated():
            if not trakt_auth.refresh_access_token():
                logging.error("Failed to authenticate with Trakt.")
                return None

        headers = {
            'Content-Type': 'application/json',
            'trakt-api-version': '2',
            'trakt-api-key': self.client_id,
            'Authorization': f'Bearer {self.access_token}'
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
            movie_metadata = {
                'type': 'movie',
                'metadata': movie_data
            }
            # Add release dates to the metadata
            release_dates = self.get_release_dates(imdb_id)
            if release_dates:
                movie_metadata['metadata']['release_dates'] = release_dates
            return movie_metadata

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

    def refresh_metadata(self, imdb_id: str) -> Dict[str, Any]:
        return self.get_metadata(imdb_id)

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

    def get_release_dates(self, imdb_id):
        url = f"{self.base_url}/movies/{imdb_id}/releases"
        response = self._make_request(url)
        if response and response.status_code == 200:
            releases = response.json()
            formatted_releases = defaultdict(list)
            for release in releases:
                country = release.get('country')
                release_date = release.get('release_date')
                release_type = release.get('release_type')
                if country and release_date:
                    try:
                        # Parse the date and convert to ISO format
                        date = iso8601.parse_date(release_date)
                        formatted_releases[country].append({
                            'date': date.date().isoformat(),
                            'type': release_type
                        })
                    except iso8601.ParseError:
                        logging.warning(f"Could not parse date: {release_date} for {imdb_id} in {country}")
            return dict(formatted_releases)  # Convert defaultdict to regular dict
        return None

    def convert_tmdb_to_imdb(self, tmdb_id):
        url = f"{self.base_url}/search/tmdb/{tmdb_id}?type=movie,show"
        response = self._make_request(url)
        if response and response.status_code == 200:
            data = response.json()
            if data:
                item = data[0]
                if 'movie' in item:
                    return item['movie']['ids']['imdb'], 'trakt'
                elif 'show' in item:
                    return item['show']['ids']['imdb'], 'trakt'
        return None, None
    
    def get_show_metadata(self, imdb_id):
        url = f"{self.base_url}/shows/{imdb_id}?extended=full,episodes"
        response = self._make_request(url)
        if response and response.status_code == 200:
            show_data = response.json()
            
            # Fetch seasons data separately to get episode IMDb IDs
            seasons_url = f"{self.base_url}/shows/{imdb_id}/seasons?extended=episodes,full"
            seasons_response = self._make_request(seasons_url)
            if seasons_response and seasons_response.status_code == 200:
                seasons_data = seasons_response.json()
                
                # Add episode IMDb IDs to the show data
                show_data['seasons'] = []
                for season in seasons_data:
                    if season['number'] is not None and season['number'] > 0:
                        season_info = {
                            'number': season['number'],
                            'episodes': []
                        }
                        for episode in season.get('episodes', []):
                            episode_info = {
                                'number': episode['number'],
                                'title': episode['title'],
                                'imdb_id': episode['ids'].get('imdb'),
                                'runtime': episode.get('runtime', 0)
                            }
                            season_info['episodes'].append(episode_info)
                        show_data['seasons'].append(season_info)
            
            return show_data
        return None

    def get_episode_metadata(self, episode_imdb_id):
        url = f"{self.base_url}/search/imdb/{episode_imdb_id}?type=episode"
        response = self._make_request(url)
        if response and response.status_code == 200:
            data = response.json()
            if data:
                episode_data = data[0]['episode']
                show_data = data[0]['show']
                return {
                    'episode': episode_data,
                    'show': {
                        'imdb_id': show_data['ids']['imdb'],
                        'metadata': show_data
                    }
                }
        return None

# Add this to your MetadataManager class
def refresh_trakt_metadata(self, imdb_id: str) -> None:
    trakt = TraktMetadata()
    new_metadata = trakt.refresh_metadata(imdb_id)
    if new_metadata:
        for key, value in new_metadata.items():
            self.add_or_update_metadata(imdb_id, key, value, 'Trakt')
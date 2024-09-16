from app.metadata_manager import MetadataManager
from typing import Dict, Any, Tuple, Optional

class DirectAPI:
    @staticmethod
    def get_movie_metadata(imdb_id: str) -> Tuple[Dict[str, Any], str]:
        return MetadataManager.get_movie_metadata(imdb_id)

    @staticmethod
    def get_movie_release_dates(imdb_id: str):
        return MetadataManager.get_release_dates(imdb_id)

    @staticmethod
    def get_episode_metadata(imdb_id):
        return MetadataManager.get_metadata_by_episode_imdb(imdb_id)

    @staticmethod
    def get_show_metadata(imdb_id):
        return MetadataManager.get_show_metadata(imdb_id)

    @staticmethod
    def get_show_seasons(imdb_id: str) -> Tuple[Dict[str, Any], str]:
        return MetadataManager.get_seasons(imdb_id)

    @staticmethod
    def tmdb_to_imdb(tmdb_id: str) -> Optional[str]:
        return MetadataManager.tmdb_to_imdb(tmdb_id)
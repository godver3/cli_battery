from app.metadata_manager import MetadataManager
from typing import Dict, Any, Tuple, Optional
from app.logger_config import logger

class DirectAPI:
    @staticmethod
    def get_movie_metadata(imdb_id: str) -> Tuple[Dict[str, Any], str]:
        logger.info(f"DirectAPI: Calling get_movie_metadata for IMDB ID: {imdb_id}")
        metadata, source = MetadataManager.get_movie_metadata(imdb_id)
        logger.info(f"DirectAPI: Movie metadata retrieved from {source} for IMDB ID: {imdb_id}")
        return metadata, source

    @staticmethod
    def get_movie_release_dates(imdb_id: str):
        logger.info(f"DirectAPI: Calling get_movie_release_dates for IMDB ID: {imdb_id}")
        release_dates, source = MetadataManager.get_release_dates(imdb_id)
        logger.info(f"DirectAPI: Release dates retrieved from {source} for IMDB ID: {imdb_id}")
        return release_dates, source

    @staticmethod
    def get_episode_metadata(imdb_id):
        logger.info(f"DirectAPI: Calling get_episode_metadata for IMDB ID: {imdb_id}")
        metadata, source = MetadataManager.get_metadata_by_episode_imdb(imdb_id)
        logger.info(f"DirectAPI: Episode metadata retrieved from {source} for IMDB ID: {imdb_id}")
        return metadata, source

    @staticmethod
    def get_show_metadata(imdb_id):
        logger.info(f"DirectAPI: Calling get_show_metadata for IMDB ID: {imdb_id}")
        metadata, source = MetadataManager.get_show_metadata(imdb_id)
        logger.info(f"DirectAPI: Show metadata retrieved from {source} for IMDB ID: {imdb_id}")
        return metadata, source

    @staticmethod
    def get_show_seasons(imdb_id: str) -> Tuple[Dict[str, Any], str]:
        logger.info(f"DirectAPI: Calling get_show_seasons for IMDB ID: {imdb_id}")
        seasons, source = MetadataManager.get_seasons(imdb_id)
        logger.info(f"DirectAPI: Show seasons retrieved from {source} for IMDB ID: {imdb_id}")
        return seasons, source

    @staticmethod
    def tmdb_to_imdb(tmdb_id: str) -> Optional[str]:
        logger.info(f"DirectAPI: Calling tmdb_to_imdb for TMDB ID: {tmdb_id}")
        imdb_id, source = MetadataManager.tmdb_to_imdb(tmdb_id)
        logger.info(f"DirectAPI: IMDB ID retrieved from {source} for TMDB ID: {tmdb_id}")
        return imdb_id
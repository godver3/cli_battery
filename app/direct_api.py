from app.database import Session, Item, Metadata, Season
from app.metadata_manager import MetadataManager
from sqlalchemy.orm import joinedload
from typing import Dict, Any, Tuple, List, Optional, Union
import json

class DirectAPI:
    @staticmethod
    def get_movie_metadata(imdb_id: str) -> Tuple[Dict[str, Any], str]:
        with Session() as session:
            item = session.query(Item).options(joinedload(Item.item_metadata)).filter_by(imdb_id=imdb_id, type='movie').first()
            if item:
                metadata = {}
                for m in item.item_metadata:
                    if m.key == 'release_dates':
                        if isinstance(m.value, str):
                            try:
                                metadata[m.key] = json.loads(m.value)
                            except json.JSONDecodeError:
                                metadata[m.key] = m.value
                        else:
                            metadata[m.key] = m.value
                    else:
                        metadata[m.key] = m.value
                return metadata, 'database'
            else:
                return MetadataManager.get_movie_metadata(imdb_id)

    @staticmethod
    def get_movie_release_dates(imdb_id: str):
        release_dates, source = MetadataManager.get_release_dates(imdb_id)
        if release_dates is None:
            # Handle the case where no release dates are found
            return {}, "No data available"
        return release_dates, source

    @staticmethod
    def get_episode_metadata(imdb_id):
        metadata, source = MetadataManager.get_metadata_by_episode_imdb(imdb_id)
        if metadata is None:
            return {}, "No data available"
        return metadata, source

    @staticmethod
    def get_show_metadata(imdb_id):
        return MetadataManager.get_show_metadata(imdb_id)

    @staticmethod
    def get_show_seasons(imdb_id: str) -> Tuple[Dict[str, Any], str]:
        return MetadataManager.get_seasons(imdb_id)

    @staticmethod
    def tmdb_to_imdb(tmdb_id: str) -> Optional[str]:
        return MetadataManager.tmdb_to_imdb(tmdb_id)

    @staticmethod
    def batch_get_metadata(imdb_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        results = {}
        with Session() as session:
            items = session.query(Item).options(joinedload(Item.item_metadata)).filter(Item.imdb_id.in_(imdb_ids)).all()
            for item in items:
                metadata = {m.key: m.value for m in item.item_metadata}
                results[item.imdb_id] = metadata
        
        # Fetch missing items from external sources
        missing_ids = set(imdb_ids) - set(results.keys())
        for imdb_id in missing_ids:
            if MetadataManager.is_movie(imdb_id):
                metadata, _ = MetadataManager.get_movie_metadata(imdb_id)
            else:
                metadata, _ = MetadataManager.get_show_metadata(imdb_id)
            if metadata:
                results[imdb_id] = metadata
        
        return results
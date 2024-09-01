from app.database import Session, Item, Metadata, Season, Episode
from datetime import datetime, timedelta
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from app.trakt_metadata import TraktMetadata
import io
from PIL import Image
from typing import Any
from sqlalchemy.exc import IntegrityError
import logging

class MetadataManager:
    @staticmethod
    def add_or_update_item(imdb_id, title, year=None, item_type=None):
        with Session() as session:
            item = session.query(Item).filter_by(imdb_id=imdb_id).first()
            if item:
                item.title = title
                if year is not None:
                    item.year = year
                if item_type is not None:
                    item.type = item_type
                item.updated_at = datetime.utcnow()
            else:
                item = Item(imdb_id=imdb_id, title=title, year=year, type=item_type)
                session.add(item)
            session.commit()
            return item.id

    @staticmethod
    def add_or_update_metadata(imdb_id, metadata_dict, provider):
        with Session() as session:
            item = session.query(Item).filter_by(imdb_id=imdb_id).first()
            if not item:
                # Create a new item if it doesn't exist
                item = Item(imdb_id=imdb_id, title=metadata_dict.get('title', ''))
                session.add(item)
                session.flush()  # This will assign an ID to the new item

            # Update the item type
            if 'type' in metadata_dict:
                item.type = metadata_dict['type']

            for key, value in metadata_dict.items():
                if key != 'type':  # We've already handled 'type' for the Item
                    metadata = session.query(Metadata).filter_by(item_id=item.id, key=key, provider=provider).first()
                    if metadata:
                        metadata.value = str(value)
                        metadata.last_updated = datetime.utcnow()
                    else:
                        metadata = Metadata(item_id=item.id, key=key, value=str(value), provider=provider)
                        session.add(metadata)
                
                # Update the year in the main item table if the metadata key is 'year'
                if key == 'year':
                    try:
                        item.year = int(value)
                        logging.info(f"Updated year for item {item.title} (ID: {item.id}) to {item.year}")
                    except ValueError:
                        logging.warning(f"Invalid year value '{value}' for item {item.title} (ID: {item.id})")
                        item.year = None
            
            session.commit()
            logging.info(f"Metadata updated for IMDB ID: {imdb_id}, Provider: {provider}")

    @staticmethod
    def get_item(imdb_id):
        with Session() as session:
            return session.query(Item).options(joinedload(Item.item_metadata), joinedload(Item.poster)).filter_by(imdb_id=imdb_id).first()

    @staticmethod
    def get_all_items():
        with Session() as session:
            items = session.query(Item).options(joinedload(Item.item_metadata)).all()
            for item in items:
                year_metadata = next((m.value for m in item.item_metadata if m.key == 'year'), None)
            return items

    @staticmethod
    def delete_item(imdb_id):
        with Session() as session:
            item = session.query(Item).filter_by(imdb_id=imdb_id).first()
            if item:
                session.delete(item)
                session.commit()
                return True
            return False

    @staticmethod
    def add_or_update_poster(item_id, image_data):
        with Session() as session:
            poster = session.query(Poster).filter_by(item_id=item_id).first()
            if poster:
                poster.image_data = image_data
                poster.last_updated = datetime.utcnow()
            else:
                poster = Poster(item_id=item_id, image_data=image_data)
                session.add(poster)
            session.commit()

    @staticmethod
    def get_poster(imdb_id):
        with Session() as session:
            item = session.query(Item).options(joinedload(Item.poster)).filter_by(imdb_id=imdb_id).first()
            if item:
                return item.poster
            return None

    @staticmethod
    def get_stats():
        with Session() as session:
            total_items = session.query(func.count(Item.id)).scalar()
            total_metadata = session.query(func.count(Metadata.id)).scalar()
            providers = session.query(Metadata.provider, func.count(Metadata.id)).group_by(Metadata.provider).all()
            last_update = session.query(func.max(Metadata.last_updated)).scalar()

            return {
                'total_items': total_items,
                'total_metadata': total_metadata,
                'providers': dict(providers),
                'last_update': last_update
            }

    @staticmethod
    def get_metadata(imdb_id, metadata_type='all'):
        with Session() as session:
            item = session.query(Item).filter_by(imdb_id=imdb_id).first()
            if not item:
                return None

            if metadata_type == 'all':
                metadata = {m.key: m.value for m in item.item_metadata}
            else:
                metadata = {m.key: m.value for m in item.item_metadata if m.key == metadata_type}

            # Include the 'type' from the Item table
            metadata['type'] = item.type

            return metadata

    @staticmethod
    def add_or_update_seasons(imdb_id: str, seasons_data: list, provider: str):
        with Session() as session:
            item = session.query(Item).filter_by(imdb_id=imdb_id).first()
            if not item:
                return

            for season_data in seasons_data:
                season_number = season_data.get('number')
                episode_count = season_data.get('episode_count')
                season = session.query(Season).filter_by(item_id=item.id, season_number=season_number).first()
                if not season:
                    season = Season(item_id=item.id, season_number=season_number, episode_count=episode_count)
                    session.add(season)
                else:
                    season.episode_count = episode_count

                if 'episodes' in season_data:
                    for episode_data in season_data['episodes']:
                        episode_number = episode_data.get('number')
                        episode = session.query(Episode).filter_by(season_id=season.id, episode_number=episode_number).first()
                        if not episode:
                            episode = Episode(
                                season_id=season.id,
                                episode_number=episode_number,
                                title=episode_data.get('title'),
                                runtime=episode_data.get('runtime'),
                                airdate=episode_data.get('airdate')
                            )
                            session.add(episode)
                        else:
                            episode.title = episode_data.get('title')
                            episode.runtime = episode_data.get('runtime')
                            episode.airdate = episode_data.get('airdate')

            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                logging.error(f"Failed to add/update seasons and episodes for {imdb_id}")

    @staticmethod
    def get_seasons(imdb_id):
        with Session() as session:
            item = session.query(Item).filter_by(imdb_id=imdb_id).first()
            if not item:
                return None

            seasons = session.query(Season).filter_by(item_id=item.id).all()
            seasons_data = []
            for season in seasons:
                episodes = session.query(Episode).filter_by(season_id=season.id).all()
                episodes_data = [
                    {
                        'number': episode.episode_number,
                        'title': episode.title,
                        'runtime': episode.runtime,
                        'airdate': episode.airdate.isoformat() if episode.airdate else None
                    }
                    for episode in episodes
                ]
                seasons_data.append({
                    'season': season.season_number,
                    'episode_count': season.episode_count,
                    'episodes': episodes_data
                })
            return seasons_data

    @staticmethod
    def get_specific_metadata(imdb_id, key):
        with Session() as session:
            item = session.query(Item).filter_by(imdb_id=imdb_id).first()
            if not item:
                return None

            metadata = next((m for m in item.item_metadata if m.key == key), None)
            if not metadata:
                new_metadata = MetadataManager.refresh_metadata(imdb_id)
                return {key: new_metadata.get(key)}

            if MetadataManager.is_metadata_stale(item):
                new_metadata = MetadataManager.refresh_metadata(imdb_id)
                return {key: new_metadata.get(key, metadata.value)}

            return {key: metadata.value}

    @staticmethod
    def is_metadata_stale(item):
        staleness_threshold = timedelta(days=7)
        return datetime.utcnow() - item.updated_at > staleness_threshold

    @staticmethod
    def refresh_metadata(imdb_id):
        trakt = TraktMetadata()
        new_metadata = trakt.refresh_metadata(imdb_id)
        if new_metadata:
            with Session() as session:
                item = session.query(Item).filter_by(imdb_id=imdb_id).first()
                if item:
                    for key, value in new_metadata.items():
                        MetadataManager.add_or_update_metadata(item.id, key, value, 'Trakt')
                    item.updated_at = datetime.utcnow()
                    session.commit()
        return new_metadata

    # TODO: Implement method to refresh metadata from enabled providers
    @staticmethod
    def refresh_trakt_metadata(self, imdb_id: str) -> None:
        trakt = TraktMetadata()
        new_metadata = trakt.refresh_metadata(imdb_id)
        if new_metadata:
            for key, value in new_metadata.items():
                self.add_or_update_metadata(imdb_id, key, value, 'Trakt')
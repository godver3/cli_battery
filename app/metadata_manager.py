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
import requests
from io import BytesIO
from app.settings import Settings

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
            item_type = metadata_dict.get('type')
            if item_type:
                item.type = item_type
            elif 'aired_episodes' in metadata_dict:  # If it has aired_episodes, it's likely a show
                item.type = 'show'
            else:
                item.type = 'movie'  # Default to movie if we can't determine

            for key, value in metadata_dict.items():
                if key != 'type':  # We've already handled 'type' for the Item
                    metadata = session.query(Metadata).filter_by(item_id=item.id, key=key, provider=provider).first()
                    if metadata:
                        metadata.value = str(value) if value is not None else None
                        metadata.last_updated = datetime.utcnow()
                    else:
                        metadata = Metadata(item_id=item.id, key=key, value=str(value) if value is not None else None, provider=provider)
                        session.add(metadata)
                
                # Update the year in the main item table if the metadata key is 'year'
                if key == 'year' and value is not None:
                    try:
                        item.year = int(value)
                    except ValueError:
                        logging.warning(f"Invalid year value '{value}' for item {item.title} (ID: {item.id})")
                        item.year = None
            
            session.commit()
            logging.info(f"Metadata updated for IMDB ID: {imdb_id}, Provider: {provider}")

    @staticmethod
    def get_metadata(imdb_id, metadata_type='all', force_refresh=False):
        if not force_refresh:
            with Session() as session:
                item = session.query(Item).filter_by(imdb_id=imdb_id).first()
                if item:
                    if metadata_type == 'all':
                        metadata = {m.key: m.value for m in item.item_metadata}
                    else:
                        metadata = {m.key: m.value for m in item.item_metadata if m.key == metadata_type}
                    if metadata:
                        logging.info(f"Metadata for {imdb_id} retrieved from battery")
                        return {
                            "source": "battery", 
                            "metadata": metadata,
                            "type": item.type
                        }

        logging.info(f"Fetching metadata for {imdb_id} from Trakt")
        trakt = TraktMetadata()
        trakt_data = trakt.get_metadata(imdb_id)
        if trakt_data:
            metadata = trakt_data['metadata']
            if metadata_type != 'all':
                metadata = {k: v for k, v in metadata.items() if k == metadata_type}
            MetadataManager.add_or_update_metadata(imdb_id, metadata, 'Trakt')
            logging.info(f"Metadata for {imdb_id} fetched from Trakt and saved to battery")
            return {
                "source": "trakt", 
                "metadata": metadata, 
                "type": trakt_data['type']
            }

        logging.warning(f"No metadata found for {imdb_id}")
        return None

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
    def get_poster(imdb_id: str):
        with Session() as session:
            item = session.query(Item).filter_by(imdb_id=imdb_id).first()
            if item and item.poster:
                return item.poster.image_data

        # If poster not in database, fetch from Trakt
        trakt = TraktMetadata()
        poster_url = trakt.get_poster(imdb_id)
        if (poster_url):
            response = requests.get(poster_url)
            if response.status_code == 200:
                image = Image.open(BytesIO(response.content))
                image_data = BytesIO()
                image.save(image_data, format='JPEG')
                image_data = image_data.getvalue()

                # Save poster to database
                MetadataManager.add_or_update_poster(imdb_id, image_data)

                return image_data

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
    def get_seasons(imdb_id):
        with Session() as session:
            item = session.query(Item).filter_by(imdb_id=imdb_id).first()
            print(f"Item query result: {item}")
            if not item:
                logging.info(f"Item with IMDB ID {imdb_id} not found in battery")
                return None

            seasons = session.query(Season).filter_by(item_id=item.id).all()
            print(f"Seasons query result: {seasons}")
            if seasons:
                seasons_dict = {}
                for season in seasons:
                    print(f"Processing season: {season.season_number}")
                    episodes = session.query(Episode).filter_by(season_id=season.id).all()
                    print(f"Episodes query result for season {season.season_number}: {episodes}")
                    seasons_dict[season.season_number] = {
                        'episode_count': season.episode_count,
                        'episodes': {
                            episode.episode_number: {
                                'title': episode.title,
                                'first_aired': episode.first_aired.isoformat() if episode.first_aired else None,
                                'runtime': episode.runtime
                            }
                            for episode in episodes
                        }
                    }
                logging.info(f"Seasons and episodes for {imdb_id} retrieved from battery")
                print(f"Seasons dict from database: {seasons_dict}")
                return seasons_dict

        logging.info(f"Seasons for {imdb_id} not found in battery, fetching from Trakt")
        trakt = TraktMetadata()
        trakt_seasons = trakt.get_show_seasons(imdb_id)
        trakt_episodes = trakt.get_show_episodes(imdb_id)
        print(f"Trakt seasons: {trakt_seasons}")  # Add this line
        print(f"Trakt episodes: {trakt_episodes}")  # Add this line
        if trakt_seasons and trakt_episodes:
            seasons_dict = MetadataManager._process_trakt_seasons(item.id, trakt_seasons, trakt_episodes)
            logging.info(f"Seasons and episodes for {imdb_id} fetched from Trakt and saved to battery")
            print(f"Seasons dict from Trakt: {seasons_dict}")  # Add this line
            return seasons_dict
        
        logging.info(f"No seasons found for {imdb_id} in Trakt")
        return None

    @staticmethod
    def _process_trakt_seasons(item_id, trakt_seasons, trakt_episodes):
        seasons_dict = {}
        with Session() as session:
            for season_data in trakt_seasons:
                season_number = season_data['season']
                season = Season(
                    item_id=item_id,
                    season_number=season_number,
                    episode_count=season_data['episode_count']
                )
                session.add(season)
                session.flush()  # To get the season.id

                season_episodes = [ep for ep in trakt_episodes if ep['season'] == season_number]
                episodes_dict = {}
                for ep_data in season_episodes:
                    episode = Episode(
                        season_id=season.id,
                        episode_number=ep_data['episode'],
                        title=ep_data['title'],
                        overview=ep_data.get('overview', ''),
                        runtime=ep_data.get('runtime', 0),
                        first_aired=ep_data.get('first_aired')
                    )
                    session.add(episode)
                    episodes_dict[ep_data['episode']] = {
                        'title': ep_data['title'],
                        'first_aired': ep_data['first_aired'].isoformat() if ep_data['first_aired'] else None,
                        'runtime': ep_data.get('runtime', 0)
                    }

                seasons_dict[season_number] = {
                    'episode_count': season_data['episode_count'],
                    'episodes': episodes_dict
                }

            session.commit()

        return seasons_dict

    @staticmethod
    def add_or_update_seasons(imdb_id, seasons_data, provider):
        with Session() as session:
            item = session.query(Item).filter_by(imdb_id=imdb_id).first()
            if not item:
                return False

            for season_data in seasons_data:
                season = session.query(Season).filter_by(item_id=item.id, season_number=season_data['season']).first()
                if not season:
                    season = Season(item_id=item.id, season_number=season_data['season'])
                    session.add(season)

                season.episode_count = season_data['episode_count']
                # Add more season attributes as needed

            session.commit()
        return True

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

    @staticmethod
    def update_provider_rank(provider_name, rank_type, new_rank):
        settings = Settings()
        providers = settings.providers
        
        for provider in providers:
            if provider['name'] == provider_name:
                if rank_type == 'metadata':
                    provider['metadata_rank'] = int(new_rank)
                elif rank_type == 'poster':
                    provider['poster_rank'] = int(new_rank)
                break
        
        # Ensure all providers have both rank types
        for provider in providers:
            if 'metadata_rank' not in provider:
                provider['metadata_rank'] = len(providers)  # Default to last rank
            if 'poster_rank' not in provider:
                provider['poster_rank'] = len(providers)  # Default to last rank
        
        # Re-sort providers based on new ranks
        providers.sort(key=lambda x: (x.get('metadata_rank', len(providers)), x.get('poster_rank', len(providers))))
        
        settings.providers = providers
        settings.save()

    @staticmethod
    def get_ranked_providers(rank_type):
        settings = Settings()
        providers = settings.providers
        return sorted([p for p in providers if p['enabled']], key=lambda x: x[f'{rank_type}_rank'])

    @staticmethod
    def add_or_update_episodes(imdb_id, episodes_data, provider):
        with Session() as session:
            item = session.query(Item).filter_by(imdb_id=imdb_id).first()
            if not item:
                logging.error(f"Item with IMDB ID {imdb_id} not found when adding episodes.")
                return

            for episode_data in episodes_data:
                season_number = episode_data.get('season')
                episode_number = episode_data.get('episode')
                
                if season_number is None or episode_number is None:
                    logging.warning(f"Skipping episode data without season or episode number for IMDB ID {imdb_id}")
                    continue

                season = session.query(Season).filter_by(
                    item_id=item.id, 
                    season_number=season_number
                ).first()

                if not season:
                    logging.warning(f"Season {season_number} not found for IMDB ID {imdb_id}. Creating new season.")
                    season = Season(item_id=item.id, season_number=season_number)
                    session.add(season)
                    session.flush()

                episode = session.query(Episode).filter_by(
                    season_id=season.id, 
                    episode_number=episode_number
                ).first()

                if episode:
                    # Update existing episode
                    episode.title = episode_data.get('title', episode.title)
                    episode.overview = episode_data.get('overview', episode.overview)
                    episode.runtime = episode_data.get('runtime', episode.runtime)
                    episode.first_aired = episode_data.get('first_aired', episode.first_aired)
                else:
                    # Create new episode
                    episode = Episode(
                        season_id=season.id,
                        episode_number=episode_number,
                        title=episode_data.get('title', ''),
                        overview=episode_data.get('overview', ''),
                        runtime=episode_data.get('runtime', 0),
                        first_aired=episode_data.get('first_aired', None)
                    )
                    session.add(episode)

            try:
                session.commit()
                logging.info(f"Episodes updated for IMDB ID: {imdb_id}, Provider: {provider}")
            except Exception as e:
                session.rollback()
                logging.error(f"Error updating episodes for IMDB ID {imdb_id}: {str(e)}")

    @staticmethod
    def get_episodes(imdb_id):
        with Session() as session:
            item = session.query(Item).filter_by(imdb_id=imdb_id).first()
            if not item:
                return None

            episodes = session.query(Episode).join(Season).filter(Season.item_id == item.id).all()
            return [
                {
                    'season': episode.season.season_number,
                    'episode': episode.episode_number,
                    'title': episode.title,
                    'overview': episode.overview,
                    'runtime': episode.runtime,
                    'first_aired': episode.first_aired.isoformat() if episode.first_aired else None
                }
                for episode in episodes
            ]
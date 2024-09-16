from app.database import DatabaseManager, Session, Item, Metadata, Season, Episode, TMDBToIMDBMapping
from datetime import datetime, timedelta
from sqlalchemy import func, cast, String, or_
from sqlalchemy.orm import joinedload
from app.trakt_metadata import TraktMetadata
from PIL import Image
from app.logger_config import logger
import requests
from io import BytesIO
from app.settings import Settings
import json
from sqlalchemy.orm import selectinload
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.exc import IntegrityError

class MetadataManager:
    @staticmethod
    def add_or_update_item(imdb_id, title, year=None, item_type=None):
        return DatabaseManager.add_or_update_item(imdb_id, title, year, item_type)

    @staticmethod
    def add_or_update_metadata(imdb_id, metadata_dict, provider):
        DatabaseManager.add_or_update_metadata(imdb_id, metadata_dict, provider)

    @staticmethod
    def debug_find_item(imdb_id):
        with Session() as session:
            items = session.query(Item).filter(
                or_(
                    Item.imdb_id == imdb_id,
                    Item.imdb_id == imdb_id.lower(),
                    Item.imdb_id == imdb_id.upper()
                )
            ).all()
            
            for item in items:
                logger.info(f"Found item: ID={item.id}, IMDb ID={item.imdb_id}, Title={item.title}, Type={item.type}")
            
            if not items:
                logger.info(f"No items found for IMDb ID: {imdb_id}")

    @staticmethod
    def get_metadata(imdb_id, metadata_type='all', force_refresh=False):
        settings = Settings()
        staleness_threshold = settings.staleness_threshold_timedelta

        logger.info(f"get_metadata called for IMDB ID: {imdb_id}, type: {metadata_type}, force_refresh: {force_refresh}")

        if not force_refresh:
            with Session() as session:
                item = session.query(Item).options(selectinload(Item.item_metadata)).filter_by(imdb_id=imdb_id).first()
                if item:
                    logger.info(f"Item found in database for IMDB ID: {imdb_id}")
                    if metadata_type == 'all':
                        metadata = {m.key: m.value for m in item.item_metadata}
                    else:
                        metadata = {m.key: m.value for m in item.item_metadata if m.key == metadata_type}
                    
                    if metadata:
                        last_updated = max(m.last_updated for m in item.item_metadata)
                        time_until_stale = last_updated + staleness_threshold - datetime.utcnow()
                        
                        logger.info(f"Metadata found for {imdb_id}. Last updated: {last_updated}, Time until stale: {time_until_stale}")
                        
                        if time_until_stale > timedelta():
                            logger.info(f"Metadata for {imdb_id} retrieved from battery. Time until stale: {time_until_stale}")
                            return {"metadata": metadata, "source": "battery", "type": item.type}
                        else:
                            logger.info(f"Metadata for {imdb_id} is stale. Refreshing from Trakt.")
                    else:
                        logger.info(f"No metadata found for {imdb_id} in database")
                else:
                    logger.info(f"No item found in database for IMDB ID: {imdb_id}")

        # If item not found, force_refresh is True, or metadata is stale, fetch from Trakt
        logger.info(f"Fetching metadata for {imdb_id} from Trakt")
        trakt = TraktMetadata()
        trakt_data = trakt.get_metadata(imdb_id)
        
        if trakt_data:
            metadata = trakt_data['metadata']
            if metadata_type != 'all':
                metadata = {k: v for k, v in metadata.items() if k == metadata_type}
            MetadataManager.add_or_update_metadata(imdb_id, metadata, 'Trakt')
            logger.debug(f"Metadata for {imdb_id} fetched from Trakt and saved to battery")
            return {"metadata": metadata, "source": "trakt", "type": trakt_data['type']}

        # If still not found, try to fetch episode metadata
        logger.info(f"Attempting to fetch episode metadata for {imdb_id}")
        episode_metadata, source = MetadataManager.get_metadata_by_episode_imdb(imdb_id)
        
        if episode_metadata and 'show' in episode_metadata:
            show_metadata = episode_metadata['show']['metadata']
            show_imdb_id = show_metadata['ids']['imdb']
            
            # Add the show metadata to the database
            MetadataManager.add_or_update_metadata(show_imdb_id, show_metadata, 'Trakt')
            
            # Return the show metadata
            if metadata_type == 'all':
                return {"metadata": show_metadata, "source": source, "type": "show"}
            else:
                filtered_metadata = {k: v for k, v in show_metadata.items() if k == metadata_type}
                return {"metadata": filtered_metadata, "source": source, "type": "show"}

        logger.warning(f"No metadata found for {imdb_id}")
        return None

    @staticmethod
    def get_item(imdb_id):
        return DatabaseManager.get_item(imdb_id)

    @staticmethod
    def get_all_items():
        return DatabaseManager.get_all_items()

    @staticmethod
    def delete_item(imdb_id):
        return DatabaseManager.delete_item(imdb_id)

    @staticmethod
    def add_or_update_poster(item_id, image_data):
        DatabaseManager.add_or_update_poster(item_id, image_data)

    @staticmethod
    def get_poster(imdb_id):
        poster_data = DatabaseManager.get_poster(imdb_id)
        if poster_data:
            return poster_data

        # If poster not in database, fetch from Trakt
        trakt = TraktMetadata()
        poster_url = trakt.get_poster(imdb_id)
        if poster_url:
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
        logger.info(f"Getting seasons for IMDB ID: {imdb_id}")
        with Session() as session:
            item = session.query(Item).filter_by(imdb_id=imdb_id, type='show').first()
            if not item:
                logger.info(f"Item not found in database for IMDB ID: {imdb_id}. Fetching metadata from Trakt.")
                trakt = TraktMetadata()
                show_metadata = trakt.get_show_metadata(imdb_id)
                if show_metadata:
                    item = Item(
                        imdb_id=imdb_id,
                        title=show_metadata.get('title', 'Unknown Title'),
                        year=show_metadata.get('year'),
                        type='show'
                    )
                    session.add(item)
                    session.commit()
                else:
                    logger.error(f"Failed to fetch metadata for IMDB ID: {imdb_id}")
                    return None, None

            if item.seasons:
                logger.info(f"Found seasons in database for IMDB ID: {imdb_id}")
                seasons_data = {}
                for season in item.seasons:
                    episodes = MetadataManager.get_episodes(imdb_id, season.season_number)
                    seasons_data[str(season.season_number)] = {
                        'episode_count': season.episode_count,
                        'episodes': episodes
                    }
                if seasons_data:
                    logger.info(f"Retrieved seasons data from database for IMDB ID: {imdb_id}")
                    return seasons_data, "battery"
                else:
                    logger.info(f"No seasons data found in database for IMDB ID: {imdb_id}")

            logger.info(f"Fetching seasons data from Trakt for IMDB ID: {imdb_id}")
            trakt = TraktMetadata()
            seasons_data = trakt.get_show_seasons(imdb_id)
            episodes_data = trakt.get_show_episodes(imdb_id)
            if seasons_data and episodes_data:
                processed_data = MetadataManager._process_trakt_seasons(imdb_id, seasons_data, episodes_data)
                MetadataManager.add_or_update_seasons(imdb_id, seasons_data, 'Trakt')
                MetadataManager.add_or_update_episodes(imdb_id, episodes_data, 'Trakt')
                logger.info(f"Stored seasons and episodes data in database for IMDB ID: {imdb_id}")
                return processed_data, "trakt"

            logger.warning(f"No seasons data found for IMDB ID: {imdb_id}")
            return None, None

    @staticmethod
    def _process_trakt_seasons(imdb_id, seasons_data, episodes_data):
        processed_data = {}
        for season in seasons_data:
            season_number = season['season']
            season_episodes = [ep for ep in episodes_data if ep['season'] == season_number]
            episodes = {}
            for episode in season_episodes:
                episodes[str(episode['episode'])] = {
                    'title': episode['title'],
                    'first_aired': episode['first_aired'].isoformat() if episode['first_aired'] else None,
                    'runtime': episode['runtime']
                }
            processed_data[str(season_number)] = {
                'episode_count': season['episode_count'],
                'episodes': episodes
            }
        return processed_data

    @staticmethod
    def get_episodes(imdb_id, season_number):
        with Session() as session:
            item = session.query(Item).filter_by(imdb_id=imdb_id).first()
            if not item:
                return {}

            season = session.query(Season).filter_by(item_id=item.id, season_number=season_number).first()
            if not season:
                return {}

            episodes = session.query(Episode).filter_by(season_id=season.id).all()
            return {
                str(episode.episode_number): {
                    'first_aired': episode.first_aired.isoformat() if episode.first_aired else None,
                    'runtime': episode.runtime,
                    'title': episode.title
                } for episode in episodes
            }
            
    @staticmethod
    def add_or_update_seasons(imdb_id, seasons_data, provider):
        with Session() as session:
            item = session.query(Item).filter_by(imdb_id=imdb_id).first()
            if not item:
                logger.info(f"Creating new Item for IMDB ID: {imdb_id}")
                trakt = TraktMetadata()
                show_metadata = trakt.get_show_metadata(imdb_id)
                if show_metadata:
                    item = Item(
                        imdb_id=imdb_id,
                        title=show_metadata.get('title', 'Unknown Title'),
                        year=show_metadata.get('year'),
                        type='show'
                    )
                    session.add(item)
                    session.flush()
                else:
                    logger.error(f"Failed to fetch metadata for IMDB ID: {imdb_id}")
                    return False

            for season_data in seasons_data:
                season = session.query(Season).filter_by(item_id=item.id, season_number=season_data['season']).first()
                if not season:
                    season = Season(item_id=item.id, season_number=season_data['season'])
                    session.add(season)

                season.episode_count = season_data['episode_count']
                # Add more season attributes as needed

            session.commit()
            logger.info(f"Seasons data updated for IMDB ID: {imdb_id}, Provider: {provider}")
        return True

    @staticmethod
    def add_or_update_episodes(imdb_id, episodes_data, provider):
        with Session() as session:
            item = session.query(Item).filter_by(imdb_id=imdb_id).first()
            if not item:
                logger.info(f"Creating new Item for IMDB ID: {imdb_id}")
                trakt = TraktMetadata()
                show_metadata = trakt.get_show_metadata(imdb_id)
                if show_metadata:
                    item = Item(
                        imdb_id=imdb_id,
                        title=show_metadata.get('title', 'Unknown Title'),
                        year=show_metadata.get('year'),
                        type='show'
                    )
                    session.add(item)
                    session.flush()
                else:
                    logger.error(f"Failed to fetch metadata for IMDB ID: {imdb_id}")
                    return False

            for episode_data in episodes_data:
                season = session.query(Season).filter_by(item_id=item.id, season_number=episode_data['season']).first()
                if not season:
                    logger.info(f"Creating new Season for IMDB ID: {imdb_id}, Season: {episode_data['season']}")
                    season = Season(item_id=item.id, season_number=episode_data['season'])
                    session.add(season)
                    session.flush()

                episode = session.query(Episode).filter_by(season_id=season.id, episode_number=episode_data['episode']).first()
                if not episode:
                    episode = Episode(season_id=season.id, episode_number=episode_data['episode'])
                    session.add(episode)

                episode.title = episode_data.get('title', '')
                episode.overview = episode_data.get('overview', '')
                episode.first_aired = episode_data.get('first_aired')
                episode.runtime = episode_data.get('runtime', 0)

            session.commit()
            logger.info(f"Episodes data updated for IMDB ID: {imdb_id}, Provider: {provider}")
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
                return {key: new_metadata.get(key, json.loads(metadata.value))}

            return {key: json.loads(metadata.value)}

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
                logger.error(f"Item with IMDB ID {imdb_id} not found when adding episodes.")
                return

            for episode_data in episodes_data:
                season_number = episode_data.get('season')
                episode_number = episode_data.get('episode')
                
                if season_number is None or episode_number is None:
                    logger.warning(f"Skipping episode data without season or episode number for IMDB ID {imdb_id}")
                    continue

                season = session.query(Season).filter_by(
                    item_id=item.id, 
                    season_number=season_number
                ).first()

                if not season:
                    logger.warning(f"Season {season_number} not found for IMDB ID {imdb_id}. Creating new season.")
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
                logger.info(f"Episodes updated for IMDB ID: {imdb_id}, Provider: {provider}")
            except Exception as e:
                session.rollback()
                logger.error(f"Error updating episodes for IMDB ID {imdb_id}: {str(e)}")

    @classmethod
    def get_release_dates(cls, imdb_id):
        with Session() as session:
            item = session.query(Item).filter_by(imdb_id=imdb_id).first()
            if not item:
                return None, None
            
            for metadata in item.item_metadata:
                if metadata.key == 'release_dates':
                    if isinstance(metadata.value, dict):
                        return metadata.value, "battery"
                    elif isinstance(metadata.value, str):
                        try:
                            return json.loads(metadata.value), "battery"
                        except json.JSONDecodeError:
                            # If it's not valid JSON, return it as is
                            return metadata.value, "battery"
            
            # If not in database, fetch from Trakt
            trakt = TraktMetadata()
            trakt_release_dates = trakt.get_release_dates(imdb_id)
            if trakt_release_dates:
                cls.add_or_update_metadata(imdb_id, {'release_dates': trakt_release_dates}, 'Trakt')
                return trakt_release_dates, "trakt"
            
            return None, None

    @staticmethod
    def tmdb_to_imdb(tmdb_id):
        with Session() as session:
            # Check if the mapping exists in the cache
            cached_mapping = session.query(TMDBToIMDBMapping).filter_by(tmdb_id=tmdb_id).first()
            if cached_mapping:
                return cached_mapping.imdb_id, 'battery'

            # If not in cache, fetch from Trakt
            trakt = TraktMetadata()
            imdb_id, source = trakt.convert_tmdb_to_imdb(tmdb_id)
            
            if imdb_id:
                # Cache the result
                new_mapping = TMDBToIMDBMapping(tmdb_id=tmdb_id, imdb_id=imdb_id)
                session.add(new_mapping)
                session.commit()
            
            return imdb_id, source
        
    @staticmethod
    def get_metadata_by_episode_imdb(episode_imdb_id):
        with Session() as session:
            # Check if we already have this episode's metadata
            episode_metadata = session.query(Metadata).filter(
                Metadata.key == 'episode_imdb_id',
                cast(Metadata.value, String).contains(episode_imdb_id)
            ).first()
            
            if episode_metadata:
                item = episode_metadata.item
                show_metadata = {}
                for m in item.item_metadata:
                    if isinstance(m.value, str):
                        try:
                            show_metadata[m.key] = json.loads(m.value)
                        except json.JSONDecodeError:
                            show_metadata[m.key] = m.value
                    else:
                        show_metadata[m.key] = m.value
                
                try:
                    episode_data = json.loads(episode_metadata.value) if isinstance(episode_metadata.value, str) else episode_metadata.value
                except json.JSONDecodeError:
                    episode_data = episode_metadata.value
                
                return {'show': show_metadata, 'episode': episode_data}, "battery"

        # If not in database, fetch from Trakt
        trakt = TraktMetadata()
        trakt_data = trakt.get_episode_metadata(episode_imdb_id)
        if trakt_data:
            show_imdb_id = trakt_data['show']['imdb_id']
            show_metadata = trakt_data['show']['metadata']
            episode_data = trakt_data['episode']

            # Save episode metadata
            with Session() as session:
                item = session.query(Item).filter_by(imdb_id=show_imdb_id).first()
                if item:
                    episode_metadata = Metadata(
                        item_id=item.id,
                        key='episode_imdb_id',
                        value=json.dumps(episode_data),
                        provider='Trakt'
                    )
                    session.add(episode_metadata)
                    session.commit()

            return {'show': show_metadata, 'episode': episode_data}, "trakt"

        return None, None

    @staticmethod
    def get_movie_metadata(imdb_id):
        settings = Settings()
        trakt = TraktMetadata()

        with Session() as session:
            item = session.query(Item).filter_by(imdb_id=imdb_id, type='movie').first()
            if item:
                metadata = session.query(Metadata).filter_by(item_id=item.id).all()
                metadata_dict = {}
                for m in metadata:
                    if m.key == 'release_dates':
                        if isinstance(m.value, str):
                            try:
                                metadata_dict[m.key] = json.loads(m.value)
                            except json.JSONDecodeError:
                                metadata_dict[m.key] = m.value
                        else:
                            metadata_dict[m.key] = m.value
                    else:
                        metadata_dict[m.key] = m.value

                return metadata_dict, "battery"

            # If the item doesn't exist in our database, fetch it from Trakt
            movie_data = trakt.get_movie_metadata(imdb_id)
            if movie_data:
                item = Item(imdb_id=imdb_id, title=movie_data.get('title'), type='movie', year=movie_data.get('year'))
                session.add(item)
                session.commit()

                for key, value in movie_data.items():
                    if isinstance(value, (list, dict)):
                        value = json.dumps(value)
                    metadata = Metadata(item_id=item.id, key=key, value=str(value), provider='trakt')
                    session.add(metadata)
                session.commit()

                return movie_data, "trakt"

            return None, None

    @staticmethod
    def get_show_metadata(imdb_id):
        with Session() as session:
            item = session.query(Item).filter_by(imdb_id=imdb_id, type='show').first()
            if item:
                metadata = session.query(Metadata).filter_by(item_id=item.id).all()
                metadata_dict = {}
                for m in metadata:
                    if m.key == 'release_dates':
                        if isinstance(m.value, str):
                            try:
                                metadata_dict[m.key] = json.loads(m.value)
                            except json.JSONDecodeError:
                                metadata_dict[m.key] = m.value
                        else:
                            metadata_dict[m.key] = m.value
                    else:
                        metadata_dict[m.key] = m.value

                return metadata_dict, "battery"

            # If the item doesn't exist in our database, fetch it from Trakt
            trakt = TraktMetadata()
            show_data = trakt.get_show_metadata(imdb_id)
            if show_data:
                try:
                    item = Item(imdb_id=imdb_id, title=show_data.get('title'), type='show', year=show_data.get('year'))
                    session.add(item)
                    session.flush()  # This will assign an ID to the item if it's new

                    for key, value in show_data.items():
                        if isinstance(value, (list, dict)):
                            value = json.dumps(value)
                        metadata = Metadata(item_id=item.id, key=key, value=str(value), provider='trakt')
                        session.add(metadata)
                    
                    session.commit()
                except IntegrityError:
                    # If the item already exists, rollback and fetch it
                    session.rollback()
                    item = session.query(Item).filter_by(imdb_id=imdb_id, type='show').first()
                    if item:
                        # Update existing metadata
                        for key, value in show_data.items():
                            if isinstance(value, (list, dict)):
                                value = json.dumps(value)
                            metadata = session.query(Metadata).filter_by(item_id=item.id, key=key).first()
                            if metadata:
                                metadata.value = str(value)
                            else:
                                metadata = Metadata(item_id=item.id, key=key, value=str(value), provider='trakt')
                                session.add(metadata)
                        session.commit()

                return show_data, "trakt"

            return None, None

from flask import render_template, request, jsonify, send_file, redirect, url_for
from app import app
from app.settings import Settings
from app.metadata_manager import MetadataManager
import io
import logging
from app.trakt_metadata import TraktMetadata
from flask import flash
from sqlalchemy import inspect
from app.database import Session, Item, Metadata, Season, Poster  # Add this line
from app.trakt_metadata import TraktMetadata  # Add this import at the top of the file
import json

settings = Settings()

@app.route('/')
def home():
    db_stats = MetadataManager.get_stats()
    stats = {
        'total_providers': len(settings.providers),
        'active_providers': sum(1 for provider in settings.providers if provider['enabled']),
        'total_items': db_stats['total_items'],
        'total_metadata': db_stats['total_metadata'],
        'last_update': db_stats['last_update'].strftime('%Y-%m-%d %H:%M:%S') if db_stats['last_update'] else 'N/A',
        'update_frequency': f"{settings.update_frequency} minutes"
    }
    return render_template('home.html', stats=stats)

@app.route('/debug')
def debug():
    items = MetadataManager.get_all_items()
    for item in items:
        # Find the year from metadata
        year_metadata = next((m.value for m in item.item_metadata if m.key == 'year'), None)
        
        # Use the metadata year if available, otherwise use the item's year
        item.display_year = year_metadata or item.year
        
    return render_template('debug.html', items=items)

@app.route('/debug/delete_item/<imdb_id>', methods=['POST'])
def delete_item(imdb_id):
    success = MetadataManager.delete_item(imdb_id)
    return jsonify({"success": success})

@app.route('/metadata')
def metadata():
    all_metadata = MetadataManager.get_all_metadata()
    return render_template('metadata.html', metadata=all_metadata)

@app.route('/api/movie/metadata/<imdb_id>', methods=['GET'])
def get_movie_metadata(imdb_id):
    try:
        print(f"Fetching movie metadata for IMDB ID: {imdb_id}")
        metadata, source = MetadataManager.get_movie_metadata(imdb_id)
        if metadata:
            print(f"Successfully retrieved movie metadata for IMDB ID: {imdb_id} from {source}")
            return jsonify({"data": metadata, "source": source})
        else:
            logging.warning(f"Movie metadata not found for IMDB ID: {imdb_id}")
            return jsonify({"error": "Movie metadata not found"}), 404
    except Exception as e:
        logging.error(f"Error fetching movie metadata: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/movie/release_dates/<imdb_id>', methods=['GET'])
def get_movie_release_dates(imdb_id):
    try:
        print(f"Fetching movie release dates for IMDB ID: {imdb_id}")
        release_dates = MetadataManager.get_release_dates(imdb_id)
        if release_dates:
            print(f"Successfully retrieved movie release dates for IMDB ID: {imdb_id}")
            return jsonify(release_dates)
        else:
            logging.warning(f"Movie release dates not found for IMDB ID: {imdb_id}")
            return jsonify({"error": "Movie release dates not found"}), 404
    except Exception as e:
        logging.error(f"Error fetching movie release dates: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/episode/metadata/<imdb_id>', methods=['GET'])
def get_episode_metadata(imdb_id):
    try:
        print(f"Fetching episode metadata for IMDB ID: {imdb_id}")
        metadata, source = MetadataManager.get_metadata_by_episode_imdb(imdb_id)
        if metadata:
            print(f"Successfully retrieved episode metadata for IMDB ID: {imdb_id} from {source}")
            return jsonify({"data": metadata, "source": source})
        else:
            logging.warning(f"Episode metadata not found for IMDB ID: {imdb_id}")
            return jsonify({"error": "Episode metadata not found"}), 404
    except Exception as e:
        logging.error(f"Error fetching episode metadata: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/show/metadata/<imdb_id>', methods=['GET'])
def get_show_metadata(imdb_id):
    try:
        print(f"Fetching show metadata for IMDB ID: {imdb_id}")
        metadata, source = MetadataManager.get_show_metadata(imdb_id)
        if metadata:
            print(f"Successfully retrieved show metadata for IMDB ID: {imdb_id} from {source}")
            return jsonify({"data": metadata, "source": source})
        else:
            logging.warning(f"Show metadata not found for IMDB ID: {imdb_id}")
            return jsonify({"error": "Show metadata not found"}), 404
    except Exception as e:
        logging.error(f"Error fetching show metadata: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/show/seasons/<imdb_id>', methods=['GET'])
def get_show_seasons(imdb_id):
    try:
        print(f"Fetching seasons for IMDB ID: {imdb_id}")
        seasons = MetadataManager.get_seasons(imdb_id)
        if seasons:
            print(f"Successfully retrieved seasons for IMDB ID: {imdb_id}")
            return jsonify(seasons)
        else:
            logging.warning(f"Seasons not found for IMDB ID: {imdb_id}")
            return jsonify({"error": "Seasons not found"}), 404
    except Exception as e:
        logging.error(f"Error fetching seasons: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/providers')
def providers():
    settings = Settings()
    providers = settings.providers
    
    # Ensure all providers have both rank types
    for i, provider in enumerate(providers, start=1):
        if 'metadata_rank' not in provider:
            provider['metadata_rank'] = i
        if 'poster_rank' not in provider:
            provider['poster_rank'] = i
    
    settings.providers = providers
    settings.save()
    
    any_provider_enabled = any(provider['enabled'] for provider in providers)
    
    # Check if Trakt is authenticated and enabled
    trakt = TraktMetadata()
    trakt_authenticated = trakt.is_authenticated()
    trakt_enabled = next((provider['enabled'] for provider in providers if provider['name'] == 'trakt'), False)
    
    return render_template('providers.html', 
                           providers=providers, 
                           any_provider_enabled=any_provider_enabled,
                           trakt_authenticated=trakt_authenticated,
                           trakt_enabled=trakt_enabled)

@app.route('/set_active_provider', methods=['POST'])
def set_active_provider():
    data = request.json
    provider = data.get('provider')
    settings = Settings()
    if provider == 'none' or any(p['name'] == provider and p['enabled'] for p in settings.providers):
        settings.active_provider = provider
        settings.save()
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Invalid provider'}), 400

@app.route('/toggle_provider', methods=['POST'])
def toggle_provider():
    data = request.json
    provider_name = data.get('provider')
    action = data.get('action')
    
    settings = Settings()
    providers = settings.providers

    for provider in providers:
        if provider['name'] == provider_name:
            provider['enabled'] = (action == 'enable')
            break
    else:
        return jsonify({'success': False, 'error': 'Provider not found'}), 404
    
    settings.providers = providers
    settings.save()

    return jsonify({
        'success': True, 
        'providers': providers
    })

@app.route('/update_provider_rank', methods=['POST'])
def update_provider_rank():
    data = request.json
    provider_name = data.get('provider')
    rank_type = data.get('type')
    new_rank = data.get('rank')

    if rank_type not in ['metadata', 'poster']:
        return jsonify({'success': False, 'error': 'Invalid rank type'}), 400

    MetadataManager.update_provider_rank(provider_name, rank_type, new_rank)

    settings = Settings()
    return jsonify({
        'success': True,
        'providers': settings.providers
    })

@app.route('/settings')
def settings_page():
    return render_template('settings.html', settings=settings.get_all())

@app.route('/save_settings', methods=['POST'])
def save_settings():
    try:
        new_settings = request.form.to_dict()
        
        # Log received data for debugging
        print(f"Received settings data: {new_settings}")
        
        # Handle checkboxes (convert to boolean)
        for key, value in new_settings.items():
            if value == 'true':
                new_settings[key] = True
            elif value == 'false':
                new_settings[key] = False

        # Handle providers separately
        new_settings['providers'] = request.form.getlist('providers')

        # Update settings
        settings.update(new_settings)

        return jsonify({"success": True})
    except Exception as e:
        logging.error(f"Error saving settings: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)})

@app.route('/authorize_trakt')
def authorize_trakt():
    trakt = TraktMetadata()
    if not trakt.client_id:
        return jsonify({"error": "Trakt client ID is not set. Please configure it in the settings and save before authorizing."})
    auth_url = trakt.get_authorization_url()
    return jsonify({"auth_url": auth_url})

@app.route('/trakt_callback')
def trakt_callback():
    trakt = TraktMetadata()
    auth_code = request.args.get('code')
    if auth_code:
        success = trakt.exchange_code_for_token(auth_code)
        if success:
            flash("Trakt authorization successful!", "success")
        else:
            flash("Trakt authorization failed. Please try again.", "error")
    else:
        flash("No authorization code received from Trakt.", "error")
    return redirect(url_for('settings_page'))  # Change 'settings' to 'settings_page'

@app.route('/check_trakt_auth')
def check_trakt_auth():
    trakt = TraktMetadata()
    return jsonify({"is_authenticated": trakt.is_authenticated()})

@app.route('/debug/schema')
def debug_schema():
    with Session() as session:
        inspector = inspect(session.bind)
        tables = inspector.get_table_names()
        schema = {}
        for table in tables:
            columns = inspector.get_columns(table)
            schema[table] = [{"name": column['name'], "type": str(column['type'])} for column in columns]
        return jsonify(schema)

@app.route('/debug/item/<imdb_id>')
def debug_item(imdb_id):
    settings = Settings()
    if not any(provider['enabled'] for provider in settings.providers):
        return jsonify({"error": "No active metadata provider"}), 400
    
    with Session() as session:
        item = session.query(Item).filter_by(imdb_id=imdb_id).first()
        if not item:
            return jsonify({"error": f"No item found for IMDB ID: {imdb_id}"}), 404
        
        metadata = {m.key: m.value for m in item.item_metadata}
        seasons = [{'season': s.season_number, 'episode_count': s.episode_count} for s in item.seasons]
        
        return jsonify({
            "item": {
                "id": item.id,
                "imdb_id": item.imdb_id,
                "title": item.title,
                "type": item.type,
                "year": item.year
            },
            "metadata": metadata,
            "seasons": seasons
        })

@app.route('/api/tmdb_to_imdb/<tmdb_id>', methods=['GET'])
def tmdb_to_imdb(tmdb_id):
    try:
        print(f"Converting TMDB ID to IMDB ID: {tmdb_id}")
        imdb_id = MetadataManager.tmdb_to_imdb(tmdb_id)
        
        if imdb_id:
            print(f"Successfully converted TMDB ID {tmdb_id} to IMDB ID {imdb_id}")
            return jsonify({"imdb_id": imdb_id})
        else:
            logging.warning(f"No IMDB ID found for TMDB ID: {tmdb_id}")
            return jsonify({"error": f"No IMDB ID found for TMDB ID: {tmdb_id}"}), 404
    except Exception as e:
        logging.error(f"Error in tmdb_to_imdb conversion: {str(e)}", exc_info=True)
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.context_processor
def inject_stats():
    stats = MetadataManager.get_stats()
    return dict(stats=stats)
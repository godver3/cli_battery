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

@app.route('/debug/add_item', methods=['POST'])
def add_item():
    data = request.json
    year = int(data['year']) if data['year'] else None
    item_id = MetadataManager.add_or_update_item(data['imdb_id'], data['title'], year)
    for key, value in data.get('metadata', {}).items():
        MetadataManager.add_or_update_metadata(item_id, key, value, data['provider'])
    return jsonify({"success": True, "item_id": item_id})

@app.route('/debug/delete_item/<imdb_id>', methods=['POST'])
def delete_item(imdb_id):
    success = MetadataManager.delete_item(imdb_id)
    return jsonify({"success": success})

@app.route('/poster/<imdb_id>')
def get_poster(imdb_id):
    settings = Settings()
    if all(provider['name'] == 'trakt' for provider in settings.providers if provider['enabled']):
        return jsonify({
            "error": "Posters not available",
            "message": "Posters are not available through the Trakt API. Enable another metadata provider to access posters."
        }), 404
    
    try:
        poster = MetadataManager.get_poster(imdb_id)
        if poster:
            return send_file(io.BytesIO(poster), mimetype='image/jpeg')
        else:
            return jsonify({
                "error": "Poster not found",
                "message": f"No poster found for IMDB ID: {imdb_id}"
            }), 404
    except Exception as e:
        logging.error(f"Error fetching poster for {imdb_id}: {str(e)}", exc_info=True)
        return jsonify({"error": "An unexpected error occurred"}), 500

@app.route('/metadata')
def metadata():
    all_metadata = MetadataManager.get_all_metadata()
    return render_template('metadata.html', metadata=all_metadata)

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
        logging.info(f"Received settings data: {new_settings}")
        
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

@app.route('/api/metadata/<imdb_id>', methods=['GET'])
def get_metadata(imdb_id):
    settings = Settings()
    if not any(provider['enabled'] for provider in settings.providers):
        return jsonify({"error": "No active metadata provider"}), 400

    metadata_type = request.args.get('type', 'all')
    force_refresh = request.args.get('refresh', 'false').lower() == 'true'
    
    logging.info(f"Fetching metadata for IMDB ID: {imdb_id}, type: {metadata_type}, force refresh: {force_refresh}")
    
    try:
        result = MetadataManager.get_metadata(imdb_id, metadata_type, force_refresh)
        
        if result:
            logging.info(f"Metadata for {imdb_id} found. Source: {result['source']}")
            return jsonify(result)
        else:
            return jsonify({"error": "Item not found"}), 404
    except Exception as e:
        logging.error(f"Error fetching metadata for {imdb_id}: {str(e)}", exc_info=True)
        return jsonify({"error": "An unexpected error occurred"}), 500

@app.route('/api/seasons/<imdb_id>', methods=['GET'])
def get_seasons(imdb_id):
    try:
        logging.info(f"Fetching seasons for IMDB ID: {imdb_id}")
        seasons = MetadataManager.get_seasons(imdb_id)
        if seasons:
            logging.info(f"Successfully retrieved seasons for IMDB ID: {imdb_id}")
            return jsonify({"seasons": seasons})
        else:
            logging.warning(f"No seasons found for IMDB ID: {imdb_id}")
            # Check if the item exists and if it's a TV show
            item = MetadataManager.get_metadata(imdb_id)
            if not item:
                logging.error(f"No item found for IMDB ID: {imdb_id}")
                return jsonify({"error": f"No item found for IMDB ID: {imdb_id}"}), 404
            elif item.get('type') != 'show':
                logging.error(f"Item with IMDB ID {imdb_id} is not a TV show")
                return jsonify({"error": f"Item with IMDB ID {imdb_id} is not a TV show"}), 400
            else:
                logging.error(f"No seasons found for TV show with IMDB ID: {imdb_id}")
                return jsonify({"error": f"No seasons found for TV show with IMDB ID: {imdb_id}"}), 404
    except Exception as e:
        logging.error(f"Error in get_seasons: {str(e)}", exc_info=True)
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

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

@app.context_processor
def inject_stats():
    stats = MetadataManager.get_stats()
    return dict(stats=stats)
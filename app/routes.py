from flask import render_template, request, jsonify, send_file, redirect, url_for
from app import app
from settings import Settings
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
    poster = MetadataManager.get_poster(imdb_id)
    if poster and poster.image_data:
        return send_file(io.BytesIO(poster.image_data), mimetype='image/jpeg')
    else:
        return 'Poster not found', 404

@app.route('/metadata')
def metadata():
    all_metadata = MetadataManager.get_all_metadata()
    return render_template('metadata.html', metadata=all_metadata)

@app.route('/providers')
def providers():
    settings = Settings()
    providers = settings.providers
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

    if provider_name == 'none':
        # Disable all providers
        for provider in providers:
            provider['enabled'] = False
    else:
        for provider in providers:
            if provider['name'] == provider_name:
                provider['enabled'] = (action == 'enable')
                if provider['enabled'] and provider_name != 'trakt':
                    # Disable all other providers except Trakt
                    for other_provider in providers:
                        if other_provider['name'] != provider_name and other_provider['name'] != 'trakt':
                            other_provider['enabled'] = False
                break
        else:
            return jsonify({'success': False, 'error': 'Provider not found'}), 404
    
    settings.providers = providers
    settings.save()

    return jsonify({
        'success': True, 
        'providers': providers
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
    
    local_metadata = MetadataManager.get_metadata(imdb_id, metadata_type)
    
    if local_metadata and not force_refresh:
        logging.info(f"Metadata for {imdb_id} found in local battery.")
        return jsonify({"source": "battery", "type": local_metadata.get('type', 'unknown'), "metadata": local_metadata})
    
    # If force_refresh is True or no local metadata, fetch from Trakt
    trakt = TraktMetadata()
    if not trakt.is_authenticated():
        return jsonify({"error": "Trakt is not authenticated"}), 401
    
    trakt_data = trakt.get_metadata(imdb_id)
    
    if trakt_data:
        metadata = trakt_data['metadata']
        metadata['type'] = trakt_data['type']  # Ensure type is included in metadata
        
        # Update this line to pass the correct arguments
        MetadataManager.add_or_update_metadata(imdb_id, metadata, 'Trakt')
        
        if trakt_data['type'] == 'show':
            seasons_data = trakt.get_show_seasons(imdb_id)
            if seasons_data:
                MetadataManager.add_or_update_seasons(imdb_id, seasons_data, 'Trakt')
        
        logging.info(f"Metadata for {imdb_id} fetched from Trakt and saved to battery.")
        
        # Filter metadata based on metadata_type if needed
        if metadata_type != 'all':
            filtered_metadata = {k: v for k, v in metadata.items() if k == metadata_type}
            return jsonify({"source": "trakt", "type": trakt_data['type'], "metadata": filtered_metadata})
        
        return jsonify({"source": "trakt", "type": trakt_data['type'], "metadata": metadata})
    else:
        return jsonify({"error": "Item not found"}), 404

@app.route('/api/seasons/<imdb_id>', methods=['GET'])
def get_seasons(imdb_id):
    settings = Settings()
    if not any(provider['enabled'] for provider in settings.providers):
        return jsonify({"error": "No active metadata provider"}), 400
        
    try:
        seasons = MetadataManager.get_seasons(imdb_id)
        if seasons:
            return jsonify({"seasons": seasons})
        else:
            # Check if the item exists and if it's a TV show
            item = MetadataManager.get_metadata(imdb_id)
            if not item:
                return jsonify({"error": f"No item found for IMDB ID: {imdb_id}"}), 404
            elif item.get('type') != 'show':
                return jsonify({"error": f"Item with IMDB ID {imdb_id} is not a TV show"}), 400
            else:
                return jsonify({"error": f"No seasons found for TV show with IMDB ID: {imdb_id}"}), 404
    except Exception as e:
        logging.error(f"Error in get_seasons: {str(e)}")
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
    return redirect(url_for('settings'))

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
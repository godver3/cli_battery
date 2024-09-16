import json
from app.logger_config import logger
import os
from datetime import timedelta

class Settings:
    def __init__(self):
        self.config_file = '/user/config/settings.json'
        self.active_provider = 'none'
        self.providers = [
            {'name': 'trakt', 'enabled': False},
            # Add more providers here as they become available
        ]
        self.trakt_client_id = ''
        self.trakt_client_secret = ''
        self.staleness_threshold = 7  # in days
        self.max_entries = 1000  # default value, adjust as needed
        self.log_level = 'INFO'
        self.Trakt = {
            'client_id': '',
            'client_secret': '',
            'access_token': '',
            'refresh_token': '',
            'expires_at': None
        }
        self.load()

    def save(self):
        config = {
            'active_provider': self.active_provider,
            'providers': self.providers,
            'trakt_client_id': self.trakt_client_id,
            'trakt_client_secret': self.trakt_client_secret,
            'staleness_threshold': self.staleness_threshold,
            'max_entries': self.max_entries,
            'log_level': self.log_level,
            'Trakt': self.Trakt
        }
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=4)

    def load(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            self.active_provider = config.get('active_provider', 'none')
            self.providers = config.get('providers', self.providers)
            self.trakt_client_id = config.get('trakt_client_id', '')
            self.trakt_client_secret = config.get('trakt_client_secret', '')
            self.staleness_threshold = config.get('staleness_threshold', 7)
            self.max_entries = config.get('max_entries', 1000)
            self.log_level = config.get('log_level', 'INFO')
            self.Trakt = config.get('Trakt', self.Trakt)
            
            # Add debug logging
            logger.debug(f"Loaded settings: Trakt={self.Trakt}")
        else:
            logger.warning(f"Config file not found: {self.config_file}")

    def get_all(self):
        return {
            "staleness_threshold": self.staleness_threshold,
            "max_entries": self.max_entries,
            "providers": self.providers,
            "log_level": self.log_level,
            "Trakt": self.Trakt
        }

    def update(self, new_settings):
        self.staleness_threshold = int(new_settings.get('staleness_threshold', self.staleness_threshold))
        self.max_entries = int(new_settings.get('max_entries', self.max_entries))
        self.log_level = new_settings.get('log_level', self.log_level)

        enabled_providers = new_settings.get('providers', [])
        for provider in self.providers:
            provider['enabled'] = provider['name'] in enabled_providers
            api_key = new_settings.get(f"provider_{provider['name']}_api_key")
            if api_key is not None:
                provider['api_key'] = api_key

        # Update Trakt settings
        if 'Trakt[client_id]' in new_settings:
            self.Trakt['client_id'] = new_settings['Trakt[client_id]']
        if 'Trakt[client_secret]' in new_settings:
            self.Trakt['client_secret'] = new_settings['Trakt[client_secret]']

        # Update other Trakt settings if needed
        self.Trakt['access_token'] = new_settings.get('trakt_access_token', self.Trakt.get('access_token', ''))
        self.Trakt['refresh_token'] = new_settings.get('trakt_refresh_token', self.Trakt.get('refresh_token', ''))
        self.Trakt['expires_at'] = new_settings.get('trakt_expires_at', self.Trakt.get('expires_at', 0))

        # Save settings to file
        self.save()

        # Log updated Trakt settings for debugging
        logger.info(f"Updated Trakt settings: {self.Trakt}")

    def save_settings(self):
        settings = self.get_all()
        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            with open(self.config_file, 'w') as f:
                json.dump(settings, f, indent=4)
            logger.info("Settings saved successfully.")
        except IOError as e:
            logger.error(f"Error saving settings to file: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error while saving settings: {str(e)}")

    def toggle_provider(self, provider_name, enable):
        for provider in self.providers:
            if provider['name'] == provider_name:
                provider['enabled'] = enable
                return True
        return False

    def get_default_settings(self):
        return {
            # ... (existing default settings)
            'Trakt': {
                'client_id': '',
                'client_secret': '',
            }
        }

    @property
    def staleness_threshold_timedelta(self):
        return timedelta(days=self.staleness_threshold)
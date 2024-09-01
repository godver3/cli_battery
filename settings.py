import json
import logging
import os

class Settings:
    def __init__(self):
        self.config_file = 'config.json'
        self.active_provider = 'none'
        self.providers = [
            {'name': 'trakt', 'enabled': False},
            # Add more providers here as they become available
        ]
        self.trakt_client_id = ''
        self.trakt_client_secret = ''
        self.update_frequency = 60  # in minutes
        self.max_entries = 1000  # default value, adjust as needed
        self.log_level = 'INFO'
        self.database_path = 'db_content/cli_battery.db'
        self.Trakt = {
            'client_id': '',
            'client_secret': '',
            'update_frequency': 60,
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
            'update_frequency': self.update_frequency,
            'max_entries': self.max_entries,
            'log_level': self.log_level,
            'database_path': self.database_path,
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
            self.update_frequency = config.get('update_frequency', 60)
            self.max_entries = config.get('max_entries', 1000)
            self.log_level = config.get('log_level', 'INFO')
            self.database_path = config.get('database_path', 'db_content/cli_battery.db')
            self.Trakt = config.get('Trakt', self.Trakt)

    def get_all(self):
        return {
            "update_frequency": self.update_frequency,
            "max_entries": self.max_entries,
            "providers": self.providers,
            "log_level": self.log_level,
            "database_path": self.database_path,
            "Trakt": self.Trakt
        }

    def update(self, new_settings):
        self.update_frequency = int(new_settings.get('update_frequency', self.update_frequency))
        self.max_entries = int(new_settings.get('max_entries', self.max_entries))
        self.log_level = new_settings.get('log_level', self.log_level)
        self.database_path = new_settings.get('database_path', self.database_path)

        enabled_providers = new_settings.get('providers', [])
        for provider in self.providers:
            provider['enabled'] = provider['name'] in enabled_providers
            api_key = new_settings.get(f"provider_{provider['name']}_api_key")
            if api_key is not None:
                provider['api_key'] = api_key

        # Update Trakt settings
        self.Trakt['client_id'] = new_settings.get('trakt_client_id', self.Trakt['client_id'])
        self.Trakt['client_secret'] = new_settings.get('trakt_client_secret', self.Trakt['client_secret'])
        self.Trakt['update_frequency'] = int(new_settings.get('trakt_update_frequency', self.Trakt['update_frequency']))
        self.Trakt['access_token'] = new_settings.get('trakt_access_token', self.Trakt['access_token'])
        self.Trakt['refresh_token'] = new_settings.get('trakt_refresh_token', self.Trakt['refresh_token'])
        self.Trakt['expires_at'] = new_settings.get('trakt_expires_at', self.Trakt['expires_at'])

        # Save settings to file
        self.save_settings()

        # Log updated Trakt settings for debugging
        logging.info(f"Updated Trakt settings: {self.Trakt}")

    def save_settings(self):
        settings = self.get_all()
        try:
            with open(self.config_file, 'w') as f:
                json.dump(settings, f, indent=4)
            logging.info("Settings saved successfully.")
        except IOError:
            logging.error("Error saving settings to file.")

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
                'update_frequency': 60,  # in minutes
            }
        }
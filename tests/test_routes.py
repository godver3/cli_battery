import unittest
from unittest.mock import patch, MagicMock
from app import app
from app.metadata_manager import MetadataManager
from app.trakt_metadata import TraktMetadata
from app.settings import Settings
from flask import url_for  # Import the Flask url_for function

class TestRoutes(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    @patch('app.routes.MetadataManager.get_stats')
    @patch('app.routes.Settings')
    def test_home_route(self, mock_settings, mock_get_stats):
        # Setup mocks
        mock_settings.return_value.providers = [{'enabled': True}]
        mock_settings.return_value.update_frequency = 60
        mock_get_stats.return_value = {
            'total_items': 10,
            'total_metadata': 20,
            'last_update': None
        }

        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        
        # Check for the presence of key elements
        self.assertIn(b'<title>cli_battery - Home</title>', response.data)
        self.assertIn(b'<h2>CLI Battery Dashboard</h2>', response.data)
        
        # Check for the stats
        self.assertIn(b'<p class="stat-value">10</p>', response.data)  # Total Items
        self.assertIn(b'<p class="stat-value">20</p>', response.data)  # Total Metadata
        self.assertIn(b'<p class="stat-value">1</p>', response.data)   # Total Providers
        self.assertIn(b'<p class="stat-value">N/A</p>', response.data) # Last Update
        self.assertIn(b'<p class="stat-value">60 minutes</p>', response.data) # Update Frequency

    @patch('app.routes.MetadataManager.get_all_items')
    def test_debug_route(self, mock_get_all_items):
        # Setup mock
        mock_item = MagicMock()
        mock_item.item_metadata = [MagicMock(key='year', value='2021')]
        mock_get_all_items.return_value = [mock_item]

        response = self.app.get('/debug')
        self.assertEqual(response.status_code, 200)

    @patch('app.routes.MetadataManager.add_or_update_item')
    @patch('app.routes.MetadataManager.add_or_update_metadata')
    def test_add_item_route(self, mock_add_metadata, mock_add_item):
        mock_add_item.return_value = 1
        data = {
            'imdb_id': 'tt1234567',
            'title': 'Test Movie',
            'year': '2021',
            'metadata': {'key': 'value'},
            'provider': 'test_provider'
        }
        response = self.app.post('/debug/add_item', json=data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"success": True, "item_id": 1})

    @patch('app.routes.MetadataManager.delete_item')
    def test_delete_item_route(self, mock_delete_item):
        mock_delete_item.return_value = True
        response = self.app.post('/debug/delete_item/tt1234567')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"success": True})

    @patch('app.routes.MetadataManager.get_poster')
    def test_get_poster_route(self, mock_get_poster):
        mock_poster = MagicMock()
        mock_poster.image_data = b'fake_image_data'
        mock_get_poster.return_value = mock_poster
        response = self.app.get('/poster/tt1234567')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b'fake_image_data')

    @patch('app.routes.Settings')
    @patch('app.routes.TraktMetadata')
    def test_providers_route(self, mock_trakt, mock_settings):
        mock_settings.return_value.providers = [{'name': 'trakt', 'enabled': True}]
        mock_trakt.return_value.is_authenticated.return_value = True
        response = self.app.get('/providers')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'trakt', response.data)

    @patch('app.routes.Settings')
    def test_set_active_provider_route(self, mock_settings):
        mock_settings.return_value.providers = [{'name': 'trakt', 'enabled': True}]
        response = self.app.post('/set_active_provider', json={'provider': 'trakt'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {'success': True})

    @patch('app.routes.Settings')
    def test_toggle_provider_route(self, mock_settings):
        mock_settings.return_value.providers = [{'name': 'trakt', 'enabled': False}]
        response = self.app.post('/toggle_provider', json={'provider': 'trakt', 'action': 'enable'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['success'], True)
        self.assertTrue(response.json['providers'][0]['enabled'])

    @patch('app.routes.Settings')
    def test_toggle_provider_route(self, mock_settings):
        mock_settings.return_value.providers = [{'name': 'trakt', 'enabled': False}]
        response = self.app.post('/toggle_provider', json={'provider': 'trakt', 'action': 'enable'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['success'], True)
        self.assertTrue(response.json['providers'][0]['enabled'])

    @patch('app.routes.MetadataManager.get_metadata')
    @patch('app.routes.TraktMetadata')
    def test_get_metadata_route(self, mock_trakt, mock_get_metadata):
        mock_get_metadata.return_value = {'title': 'Test Movie', 'year': 2021}
        mock_trakt.return_value.is_authenticated.return_value = True
        response = self.app.get('/api/metadata/tt1234567')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['metadata']['title'], 'Test Movie')

    @patch('app.routes.MetadataManager.get_seasons')
    def test_get_seasons_route(self, mock_get_seasons):
        mock_get_seasons.return_value = [{'season': 1, 'episode_count': 10}]
        response = self.app.get('/api/seasons/tt1234567')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['seasons'][0]['season'], 1)

    @patch('app.routes.TraktMetadata')
    def test_authorize_trakt_route(self, mock_trakt):
        mock_trakt.return_value.get_authorization_url.return_value = 'http://trakt.auth.url'
        response = self.app.get('/authorize_trakt')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['auth_url'], 'http://trakt.auth.url')

    @patch('app.routes.TraktMetadata')
    @patch('app.routes.flash')
    def test_trakt_callback_route(self, mock_flash, mock_trakt):
        mock_trakt.return_value.exchange_code_for_token.return_value = True
        with app.test_request_context():  # Use the actual Flask app here
            response = self.app.get('/trakt_callback?code=test_code')
            self.assertEqual(response.status_code, 302)  # Redirect status code
            self.assertEqual(response.location, url_for('settings_page'))  # Check redirect location
        mock_flash.assert_called_once_with("Trakt authorization successful!", "success")

    @patch('app.routes.inspect')
    @patch('app.routes.Session')
    def test_debug_schema_route(self, mock_session, mock_inspect):
        mock_inspector = MagicMock()
        mock_inspect.return_value = mock_inspector
        mock_inspector.get_table_names.return_value = ['items', 'metadata']
        mock_inspector.get_columns.return_value = [
            {'name': 'id', 'type': 'INTEGER'},
            {'name': 'title', 'type': 'VARCHAR'}
        ]

        response = self.app.get('/debug/schema')
        self.assertEqual(response.status_code, 200)
        self.assertIn('items', response.json)
        self.assertIn('metadata', response.json)
        self.assertEqual(len(response.json['items']), 2)

    @patch('app.routes.Settings')
    @patch('app.routes.Session')
    def test_debug_item_route(self, mock_session, mock_settings):
        mock_settings.return_value.providers = [{'enabled': True}]
        mock_session_instance = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_session_instance
        mock_item = MagicMock(id=1, imdb_id='tt1234567', title='Test Movie', type='movie', year=2021)
        mock_item.item_metadata = [MagicMock(key='genre', value='Action')]
        mock_item.seasons = [MagicMock(season_number=1, episode_count=10)]
        mock_session_instance.query.return_value.filter_by.return_value.first.return_value = mock_item

        response = self.app.get('/debug/item/tt1234567')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['item']['imdb_id'], 'tt1234567')
        self.assertEqual(response.json['metadata']['genre'], 'Action')
        self.assertEqual(response.json['seasons'][0]['season'], 1)

if __name__ == '__main__':
    unittest.main()
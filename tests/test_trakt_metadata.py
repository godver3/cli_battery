import unittest
from unittest.mock import patch, MagicMock
from app.trakt_metadata import TraktMetadata
from datetime import datetime, timedelta, timezone
import iso8601

class TestTraktMetadata(unittest.TestCase):

    @patch('app.trakt_metadata.requests.get')
    def test_get_movie_metadata(self, mock_get):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'title': 'Test Movie', 'year': 2021}
        mock_get.return_value = mock_response

        trakt = TraktMetadata()
        metadata = trakt.get_movie_metadata('tt1234567')

        self.assertIsNotNone(metadata)
        self.assertEqual(metadata['title'], 'Test Movie')
        self.assertEqual(metadata['year'], 2021)

    @patch('app.trakt_metadata.TraktMetadata.get_device_code')
    @patch('app.trakt_metadata.Settings')
    def test_ensure_trakt_auth(self, mock_settings, mock_get_device_code):
        mock_settings.return_value.Trakt = {
            'client_id': 'test_client_id',
            'client_secret': 'test_client_secret'
        }
        mock_get_device_code.return_value = {
            'user_code': 'TEST123',
            'device_code': 'DEVICE123',
            'verification_url': 'http://example.com/verify'
        }
        trakt = TraktMetadata()
        result = trakt.ensure_trakt_auth()
        self.assertIsNotNone(result)
        self.assertEqual(result['user_code'], 'TEST123')
        self.assertEqual(result['device_code'], 'DEVICE123')
        self.assertEqual(result['verification_url'], 'http://example.com/verify')

    @patch('app.trakt_metadata.Settings')
    @patch('app.trakt_metadata.datetime')
    def test_is_authenticated(self, mock_datetime, mock_settings):
        mock_now = datetime.now(timezone.utc)
        mock_datetime.now.return_value = mock_now
        
        mock_settings.return_value.Trakt = {
            'client_id': 'test_client_id',
            'client_secret': 'test_client_secret',
            'access_token': 'test_token',
            'expires_at': (mock_now + timedelta(hours=1)).isoformat()
        }
        trakt = TraktMetadata()
        self.assertTrue(trakt.is_authenticated())

        mock_settings.return_value.Trakt['expires_at'] = (mock_now - timedelta(hours=1)).isoformat()
        self.assertFalse(trakt.is_authenticated())

    # Add more test methods for other TraktMetadata functions

if __name__ == '__main__':
    unittest.main()
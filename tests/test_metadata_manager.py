import unittest
from unittest.mock import patch, MagicMock
from app.metadata_manager import MetadataManager
from app.database import Item, Metadata
from datetime import datetime
from sqlalchemy import func

class TestMetadataManager(unittest.TestCase):

    @patch('app.metadata_manager.Session')
    def test_add_or_update_item(self, mock_session):
        # Setup mock session
        mock_session_instance = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_session_instance
        
        # Setup mock query to return None (simulating item not found)
        mock_query = mock_session_instance.query.return_value
        mock_query.filter_by.return_value.first.return_value = None
        
        # Test adding a new item
        MetadataManager.add_or_update_item('tt1234567', 'Test Movie', 2021)
        
        # Assert that a new Item was created and added to the session
        mock_session_instance.add.assert_called_once()
        mock_session_instance.commit.assert_called_once()

    @patch('app.metadata_manager.Session')
    def test_get_item(self, mock_session):
        # Setup mock session and query
        mock_session_instance = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_session_instance
        mock_query = mock_session_instance.query.return_value
        mock_query.options.return_value.filter_by.return_value.first.return_value = Item(id=1, imdb_id='tt1234567', title='Test Movie')

        # Test getting an item
        item = MetadataManager.get_item('tt1234567')

        self.assertIsNotNone(item)
        self.assertEqual(item.imdb_id, 'tt1234567')
        self.assertEqual(item.title, 'Test Movie')

    @patch('app.metadata_manager.Session')
    @patch('app.metadata_manager.func.max')
    def test_get_stats(self, mock_func_max, mock_session):
        mock_session_instance = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_session_instance
        
        # Set up the mock to return specific values for different queries
        mock_session_instance.query.return_value.scalar.side_effect = [10, 20, datetime.now()]
        mock_func_max.return_value = 'mocked_max'

        stats = MetadataManager.get_stats()
        self.assertEqual(stats['total_items'], 10)
        self.assertEqual(stats['total_metadata'], 20)
        self.assertIsNotNone(stats['last_update'])

    @patch('app.metadata_manager.Session')
    def test_get_seasons(self, mock_session):
        mock_session_instance = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_session_instance
        mock_session_instance.query.return_value.filter_by.return_value.all.return_value = [
            MagicMock(season_number=1, episode_count=10),
            MagicMock(season_number=2, episode_count=12)
        ]

        seasons = MetadataManager.get_seasons('tt1234567')
        self.assertEqual(len(seasons), 2)
        self.assertEqual(seasons[0]['season'], 1)
        self.assertEqual(seasons[0]['episode_count'], 10)
        self.assertEqual(seasons[1]['season'], 2)
        self.assertEqual(seasons[1]['episode_count'], 12)

    # Add more test methods for other MetadataManager functions

if __name__ == '__main__':
    unittest.main()
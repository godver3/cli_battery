import unittest
from unittest.mock import patch, create_autospec, MagicMock, patch
from app.metadata_manager import MetadataManager
from app.database import Item, Metadata
from datetime import datetime
from sqlalchemy import func
from app.database import Item, Season, Episode
from app.trakt_metadata import TraktMetadata

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
    @patch('app.metadata_manager.TraktMetadata')
    def test_get_seasons(self, mock_trakt, mock_session):
        mock_session_instance = mock_session.return_value.__enter__.return_value

        # Test case 1: Data available in local database
        self._setup_local_db_mocks(mock_session_instance)
        seasons = MetadataManager.get_seasons('tt1234567')
        print(f"Test case 1 - Seasons from database: {seasons}")  # Add this line
        self._assert_seasons_data(seasons)

        # Reset mocks for the second test case
        mock_session_instance.reset_mock()

        # Test case 2: Data not in local database, fetch from Trakt
        self._setup_trakt_mocks(mock_trakt, mock_session_instance)
        seasons = MetadataManager.get_seasons('tt7654321')
        print(f"Test case 2 - Seasons from Trakt: {seasons}")  # Add this line
        self._assert_seasons_data(seasons)

    def _setup_local_db_mocks(self, mock_session_instance):
        mock_item = MagicMock(spec=Item, id=1)
        mock_session_instance.query.return_value.filter_by.return_value.first.return_value = mock_item

        mock_seasons = [
            MagicMock(spec=Season, id=1, season_number=1, episode_count=10),
            MagicMock(spec=Season, id=2, season_number=2, episode_count=12)
        ]
        mock_episodes = [
            [MagicMock(spec=Episode, episode_number=1, title="S1E1", first_aired=datetime.now(), runtime=30),
            MagicMock(spec=Episode, episode_number=2, title="S1E2", first_aired=datetime.now(), runtime=30)],
            [MagicMock(spec=Episode, episode_number=1, title="S2E1", first_aired=datetime.now(), runtime=30),
            MagicMock(spec=Episode, episode_number=2, title="S2E2", first_aired=datetime.now(), runtime=30)]
        ]

        def side_effect(*args, **kwargs):
            if args[0] == Item:
                return mock_session_instance.query.return_value
            elif args[0] == Season:
                return MagicMock(filter_by=MagicMock(return_value=MagicMock(all=MagicMock(return_value=mock_seasons))))
            elif args[0] == Episode:
                return MagicMock(filter_by=MagicMock(return_value=MagicMock(all=MagicMock(side_effect=mock_episodes))))
            return MagicMock()

        mock_session_instance.query.side_effect = side_effect
    def _setup_trakt_mocks(self, mock_trakt, mock_session_instance):
        # Mock empty database results
        mock_session_instance.query.return_value.filter_by.return_value.first.return_value = MagicMock(spec=Item, id=1)
        mock_session_instance.query.return_value.filter_by.return_value.all.return_value = []

        mock_trakt_instance = mock_trakt.return_value
        mock_trakt_instance.get_show_seasons.return_value = [
            {'season': 1, 'episode_count': 10},
            {'season': 2, 'episode_count': 12}
        ]
        mock_trakt_instance.get_show_episodes.return_value = [
            {'season': 1, 'episode': 1, 'title': 'S1E1', 'first_aired': datetime.now(), 'runtime': 30},
            {'season': 1, 'episode': 2, 'title': 'S1E2', 'first_aired': datetime.now(), 'runtime': 30},
            {'season': 2, 'episode': 1, 'title': 'S2E1', 'first_aired': datetime.now(), 'runtime': 30},
            {'season': 2, 'episode': 2, 'title': 'S2E2', 'first_aired': datetime.now(), 'runtime': 30}
        ]

    def _assert_seasons_data(self, seasons):
        self.assertIsNotNone(seasons)
        self.assertIsInstance(seasons, dict)
        self.assertEqual(len(seasons), 2)
        
        for season_number, season_data in seasons.items():
            self.assertIn('episode_count', season_data)
            self.assertIn('episodes', season_data)
            self.assertIsInstance(season_data['episodes'], dict)
            
            if season_number == 1:
                self.assertEqual(season_data['episode_count'], 10)
            elif season_number == 2:
                self.assertEqual(season_data['episode_count'], 12)
            
            for episode_number, episode_data in season_data['episodes'].items():
                self.assertIn('title', episode_data)
                self.assertIn('first_aired', episode_data)
                self.assertIn('runtime', episode_data)

    # Add more test methods for other MetadataManager functions

if __name__ == '__main__':
    unittest.main()
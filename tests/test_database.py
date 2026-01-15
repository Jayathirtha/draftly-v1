"""Tests for database operations"""
import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session
from draftly_v1.services.database import (
    get_db_session,
    get_creds_from_db,
    store_user
)
from draftly_v1.model.User import User


@pytest.fixture
def mock_session():
    """Mock database session"""
    with patch('draftly_v1.services.database.SessionLocal') as mock:
        session = MagicMock(spec=Session)
        mock.return_value = session
        yield session


class TestDatabase:
    """Test database operations"""
    
    def test_get_db_session(self):
        """Test getting a database session"""
        session = get_db_session()
        assert session is not None
    
    @patch('draftly_v1.services.database.User')
    @patch('json.load')
    @patch('builtins.open')
    @patch('pathlib.Path.exists')
    def test_get_creds_from_db_success(self, mock_exists, mock_open, mock_json_load, mock_user_class, mock_session):
        """Test retrieving user credentials from database"""
        # Mock user instance
        mock_user = MagicMock()
        mock_user.email = 'test@example.com'
        mock_user.refresh_token = 'test_refresh_token'
        
        # Mock the query chain using filter (not filter_by)
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_filter.first.return_value = mock_user
        mock_query.filter.return_value = mock_filter
        mock_session.query.return_value = mock_query
        
        # Mock client secrets file
        mock_exists.return_value = True
        mock_json_load.return_value = {
            "web": {
                "client_id": "test_client_id",
                "client_secret": "test_client_secret"
            }
        }
        
        with patch('draftly_v1.services.database.get_db_session', return_value=mock_session):
            creds = get_creds_from_db('test@example.com')
        
        # Verify credentials dictionary structure
        assert creds is not None
        assert isinstance(creds, dict)
        assert creds['refresh_token'] == 'test_refresh_token'
        assert creds['client_id'] == 'test_client_id'
        assert creds['client_secret'] == 'test_client_secret'
        assert creds['token_uri'] == 'https://oauth2.googleapis.com/token'
    
    def test_get_creds_from_db_user_not_found(self, mock_session):
        """Test error when user not found in database"""
        # Mock the query chain to return None
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_filter.first.return_value = None
        mock_query.filter.return_value = mock_filter
        mock_session.query.return_value = mock_query
        
        with patch('draftly_v1.services.database.get_db_session', return_value=mock_session):
            with pytest.raises(ValueError, match='not found'):
                get_creds_from_db('notfound@example.com')
    
    def test_store_user_new_user(self, mock_session):
        """Test storing a new user"""
        # Mock the query chain to return None (no existing user)
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_filter.first.return_value = None
        mock_query.filter.return_value = mock_filter
        mock_session.query.return_value = mock_query
        
        with patch('draftly_v1.services.database.get_db_session', return_value=mock_session), \
             patch('draftly_v1.services.database.User') as mock_user_class:
            
            mock_user_instance = MagicMock()
            mock_user_class.return_value = mock_user_instance
            
            result = store_user(
                email='newuser@example.com',
                refresh_token='new_token',
                style_profile='Professional'
            )
        
        # Verify User was created with correct parameters
        mock_user_class.assert_called_once_with(
            email='newuser@example.com',
            refresh_token='new_token',
            style_profile='Professional'
        )
        mock_session.add.assert_called_once_with(mock_user_instance)
        mock_session.commit.assert_called_once()
    
    def test_store_user_existing_user(self, mock_session):
        """Test updating existing user credentials"""
        mock_user = MagicMock(spec=User)
        mock_user.email = 'existing@example.com'
        mock_user.refresh_token = 'old_token'
        mock_user.style_profile = 'Old Style'
        
        # Mock the query chain
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_filter.first.return_value = mock_user
        mock_query.filter.return_value = mock_filter
        mock_session.query.return_value = mock_query
        
        with patch('draftly_v1.services.database.get_db_session', return_value=mock_session):
            result = store_user(
                email='existing@example.com',
                refresh_token='updated_token',
                style_profile='Casual'
            )
        
        # Check that user attributes were updated
        assert mock_user.refresh_token == 'updated_token'
        assert mock_user.style_profile == 'Casual'
        mock_session.commit.assert_called_once()
    
    def test_store_user_rollback_on_error(self, mock_session):
        """Test rollback on error during user storage"""
        mock_session.commit.side_effect = Exception('Database error')
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        with patch('draftly_v1.services.database.get_db_session', return_value=mock_session):
            with pytest.raises(Exception):
                store_user(
                    email='error@example.com',
                    refresh_token='token',
                    style_profile=None
                )
        
        mock_session.rollback.assert_called_once()

"""Tests for session management"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from fastapi import HTTPException, Request
from draftly_v1.services.utils.session_mangement import create_user_session, validate_session
from draftly_v1.model.UserSession import UserSession


@pytest.fixture
def mock_db_session():
    """Mock database session"""
    with patch('draftly_v1.services.utils.session_mangement.get_db_session') as mock:
        db = MagicMock()
        mock.return_value = db
        yield db


class TestSessionManagement:
    """Test session management functions"""
    
    def test_create_user_session(self, mock_db_session):
        """Test creating a new user session"""
        # Mock query to return None (no existing session)
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = None
        
        email = 'test@example.com'
        token = create_user_session(email)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
    
    def test_update_existing_user_session(self, mock_db_session):
        """Test updating an existing user session"""
        # Mock existing session
        mock_existing_session = MagicMock()
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = mock_existing_session
        
        email = 'test@example.com'
        token = create_user_session(email)
        
        assert token is not None
        assert isinstance(token, str)
        # Should not call add when updating
        mock_db_session.add.assert_not_called()
        mock_db_session.commit.assert_called_once()
    
    def test_create_user_session_rollback_on_error(self, mock_db_session):
        """Test session creation rolls back on error"""
        mock_db_session.commit.side_effect = Exception('DB Error')
        
        with pytest.raises(Exception, match='Error creating user session'):
            create_user_session('test@example.com')
        
        mock_db_session.rollback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_session_valid_token(self, mock_db_session):
        """Test validating a valid session token"""
        # Create a mock session
        mock_session = MagicMock()
        mock_session.user_email = 'test@example.com'
        mock_session.expires_at = datetime.now() + timedelta(hours=1)
        
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = mock_session
        
        email = await validate_session(session_token='valid_token')
        
        assert email == 'test@example.com'
    
    @pytest.mark.asyncio
    async def test_validate_session_invalid_token(self, mock_db_session):
        """Test validating an invalid session token"""
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            await validate_session(session_token='invalid_token')
        
        assert exc_info.value.status_code == 401
        assert 'Invalid session' in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_validate_session_expired_token(self, mock_db_session):
        """Test validating an expired session token"""
        mock_session = MagicMock()
        mock_session.user_email = 'test@example.com'
        mock_session.expires_at = datetime.now() - timedelta(hours=1)  # Expired
        
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = mock_session
        
        with pytest.raises(HTTPException) as exc_info:
            await validate_session(session_token='expired_token')
        
        assert exc_info.value.status_code == 401
        assert 'expired' in exc_info.value.detail.lower()
        mock_db_session.delete.assert_called_once_with(mock_session)
        mock_db_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_session_from_cookie(self, mock_db_session):
        """Test validating session from cookie when header is missing"""
        mock_session = MagicMock()
        mock_session.user_email = 'test@example.com'
        mock_session.expires_at = datetime.now() + timedelta(hours=1)
        
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = mock_session
        
        # Create proper mock request with cookies
        mock_request = MagicMock()
        mock_request.cookies = {'session_token': 'cookie_token'}
        
        with patch('draftly_v1.services.utils.session_mangement.get_db_session', return_value=mock_db_session):
            email = await validate_session(session_token=None, request=mock_request)
        
        assert email == 'test@example.com'
    
    @pytest.mark.asyncio
    async def test_validate_session_no_token(self, mock_db_session):
        """Test validation fails when no token is provided"""
        mock_request = MagicMock(spec=Request)
        mock_request.cookies.get.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            await validate_session(session_token=None, request=mock_request)
        
        assert exc_info.value.status_code == 401
        assert 'No session token' in exc_info.value.detail

"""Tests for authentication routes"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
from draftly_v1.app import app

client = TestClient(app)



@pytest.fixture
def mock_flow():
    """Mock OAuth flow"""
    with patch('draftly_v1.routes.auth_routes.Flow') as mock:
        flow_instance = MagicMock()
        flow_instance.authorization_url.return_value = ('http://auth.url', 'state123')
        mock.from_client_secrets_file.return_value = flow_instance
        yield mock


@pytest.fixture
def mock_credentials():
    """Mock credentials"""
    creds = MagicMock()
    creds.token = 'test_token_123'
    return creds


class TestAuthRoutes:
    """Test authentication routes"""
    
    def test_get_current_user_without_cookie(self):
        """Test /auth/me without authentication cookie"""
        response = client.get('/auth/me')
        assert response.status_code == 401
        assert 'Not authenticated' in response.json()['detail']
    
    def test_get_current_user_with_cookie(self):
        """Test /auth/me with authentication cookie"""
        client.cookies.set('user_email', 'test@example.com')
        response = client.get('/auth/me')
        assert response.status_code == 200
        assert response.json()['email'] == 'test@example.com'
        assert response.json()['authenticated'] is True
    
    def test_logout(self):
        """Test logout endpoint"""
        response = client.post('/auth/logout')
        assert response.status_code == 200
        assert response.json()['message'] == 'Logged out successfully'
    
    def test_login_redirect(self, mock_flow):
        """Test login redirects to OAuth provider"""
        response = client.get('/auth/login', follow_redirects=False)
        assert response.status_code in [302, 307]  # Redirect status codes
        mock_flow.from_client_secrets_file.assert_called_once()
    
    @patch('draftly_v1.routes.auth_routes.build')
    @patch('draftly_v1.routes.auth_routes.store_user')
    @patch('draftly_v1.routes.auth_routes.create_user_session')
    def test_auth_callback(self, mock_create_session, mock_store_user, mock_build, mock_flow):
        """Test OAuth callback"""
        # Setup mocks
        mock_create_session.return_value = 'session_token_123'
        
        user_info_service = MagicMock()
        user_info_service.userinfo().get().execute.return_value = {'email': 'test@example.com'}
        mock_build.return_value = user_info_service
        
        flow_instance = mock_flow.from_client_secrets_file.return_value
        flow_instance.credentials.token = 'oauth_token_123'
        
        response = client.get(
            '/auth/callback?code=auth_code_123&state=state_123',
            follow_redirects=False
        )
        
        assert response.status_code == 302
        assert 'home' in response.headers['location']
        mock_store_user.assert_called_once()
        mock_create_session.assert_called_once_with(user_email='test@example.com')

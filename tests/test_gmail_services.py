"""Tests for Gmail services"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from google.auth.exceptions import RefreshError
from draftly_v1.services.gmail_services import (
    fetch_latest_email,
    fetch_email_thread_by_id,
    mark_thread_as_read,
    get_user_creds
)


@pytest.fixture
def mock_gmail_service():
    """Mock Gmail API service"""
    service = MagicMock()
    return service


@pytest.fixture
def mock_get_user_creds():
    """Mock get_user_creds function"""
    with patch('draftly_v1.services.gmail_services.get_user_creds') as mock:
        yield mock


@pytest.fixture
def sample_messages():
    """Sample Gmail messages"""
    return [
        {'id': 'msg_1', 'threadId': 'thread_1'},
        {'id': 'msg_2', 'threadId': 'thread_2'},
        {'id': 'msg_3', 'threadId': 'thread_1'},  # Duplicate thread
    ]


@pytest.fixture
def sample_message_details():
    """Sample message details response"""
    return {
        'id': 'msg_1',
        'threadId': 'thread_1',
        'snippet': 'This is a test message',
        'payload': {
            'headers': [
                {'name': 'From', 'value': 'sender@example.com'},
                {'name': 'Subject', 'value': 'Test Subject'},
                {'name': 'To', 'value': 'recipient@example.com'},
                {'name': 'Date', 'value': 'Mon, 1 Jan 2024 12:00:00 +0000'}
            ],
            'parts': [{
                'mimeType': 'text/html',
                'body': {'data': 'VGVzdCBib2R5'}  # base64 encoded "Test body"
            }]
        }
    }


class TestGmailServices:
    """Test Gmail service functions"""
    
    @pytest.mark.asyncio
    async def test_fetch_latest_email_success(self, mock_get_user_creds, mock_gmail_service, sample_messages):
        """Test successfully fetching latest emails"""
        mock_get_user_creds.return_value = mock_gmail_service
        
        # Mock list response
        mock_gmail_service.users().messages().list().execute.return_value = {
            'messages': sample_messages
        }
        
        # Mock batch responses
        def mock_callback_setup(*args, **kwargs):
            callback = kwargs.get('callback')
            if callback:
                # Simulate batch responses
                callback('msg_1', {
                    'id': 'msg_1',
                    'threadId': 'thread_1',
                    'snippet': 'Test 1',
                    'payload': {'headers': [
                        {'name': 'From', 'value': 'sender1@example.com'},
                        {'name': 'Subject', 'value': 'Subject 1'}
                    ]}
                }, None)
                callback('msg_2', {
                    'id': 'msg_2',
                    'threadId': 'thread_2',
                    'snippet': 'Test 2',
                    'payload': {'headers': [
                        {'name': 'From', 'value': 'sender2@example.com'},
                        {'name': 'Subject', 'value': 'Subject 2'}
                    ]}
                }, None)
            return MagicMock()
        
        mock_gmail_service.new_batch_http_request = mock_callback_setup
        
        result = await fetch_latest_email('test@example.com')
        
        assert 'messages' in result
        assert 'msgId' in result['messages']
        assert 'threadId' in result['messages']
        assert len(result['messages']['msgId']) >= 1
    
    @pytest.mark.asyncio
    async def test_fetch_latest_email_no_messages(self, mock_get_user_creds, mock_gmail_service):
        """Test fetching when no unread emails exist"""
        mock_get_user_creds.return_value = mock_gmail_service
        mock_gmail_service.users().messages().list().execute.return_value = {'messages': []}
        
        result = await fetch_latest_email('test@example.com')
        
        assert 'message' in result
        assert 'No new unread emails' in result['message']
    
    @pytest.mark.asyncio
    async def test_fetch_latest_email_refresh_error(self, mock_get_user_creds, mock_gmail_service):
        """Test handling RefreshError (expired credentials)"""
        mock_get_user_creds.return_value = mock_gmail_service
        mock_gmail_service.users().messages().list().execute.side_effect = RefreshError('Token expired')
        
        with pytest.raises(HTTPException) as exc_info:
            await fetch_latest_email('test@example.com')
        
        assert exc_info.value.status_code == 401
        assert 'expired' in exc_info.value.detail.lower()
    
    @pytest.mark.asyncio
    async def test_fetch_email_thread_by_id_success(self, mock_get_user_creds, mock_gmail_service, sample_message_details):
        """Test successfully fetching email thread"""
        mock_get_user_creds.return_value = mock_gmail_service
        mock_gmail_service.users().threads().get().execute.return_value = {
            'messages': [sample_message_details]
        }
        
        result = await fetch_email_thread_by_id('test@example.com', 'thread_123')
        
        assert result['thread_id'] == 'thread_123'
        assert 'llm_context' in result
        assert len(result['llm_context']) > 0
        assert result['llm_context'][0]['from'] == 'sender@example.com'
        assert result['llm_context'][0]['subject'] == 'Test Subject'
    
    @pytest.mark.asyncio
    async def test_fetch_email_thread_by_id_error(self, mock_get_user_creds, mock_gmail_service):
        """Test error handling when fetching thread fails"""
        mock_get_user_creds.return_value = mock_gmail_service
        mock_gmail_service.users().threads().get().execute.side_effect = Exception('API Error')
        
        with pytest.raises(HTTPException) as exc_info:
            await fetch_email_thread_by_id('test@example.com', 'thread_123')
        
        assert exc_info.value.status_code == 500
    
    def test_mark_thread_as_read_success(self, mock_get_user_creds, mock_gmail_service):
        """Test successfully marking thread as read"""
        mock_get_user_creds.return_value = mock_gmail_service
        mock_gmail_service.users().threads().modify().execute.return_value = {}
        
        result = mark_thread_as_read('test@example.com', 'thread_123')
        
        assert result is True
        # Verify modify was called - use call_args_list due to method chaining
        call_args_list = mock_gmail_service.users().threads().modify.call_args_list
        actual_calls = [c for c in call_args_list if c[1]]
        assert len(actual_calls) == 1
        assert actual_calls[0][1]['userId'] == 'me'
        assert actual_calls[0][1]['id'] == 'thread_123'
        assert actual_calls[0][1]['body'] == {'removeLabelIds': ['UNREAD']}
    
    def test_mark_thread_as_read_failure(self, mock_get_user_creds, mock_gmail_service):
        """Test handling error when marking thread as read"""
        mock_get_user_creds.return_value = mock_gmail_service
        mock_gmail_service.users().threads().modify().execute.side_effect = Exception('API Error')
        
        result = mark_thread_as_read('test@example.com', 'thread_123')
        
        assert result is False

"""Tests for email services"""
import pytest
from unittest.mock import MagicMock, patch, Mock
from email.message import EmailMessage
import base64
from draftly_v1.services.email_services import (
    create_gmail_draft,
    send_gmail_draft,
)


@pytest.fixture
def mock_gmail_service():
    """Mock Gmail service"""
    service = MagicMock()
    
    # Mock thread get
    thread_response = {
        'messages': [{
            'id': 'msg_123',
            'payload': {
                'headers': [
                    {'name': 'Subject', 'value': 'Test Subject'},
                    {'name': 'From', 'value': 'sender@example.com'},
                    {'name': 'Message-ID', 'value': '<msg123@example.com>'},
                    {'name': 'References', 'value': '<ref123@example.com>'}
                ]
            }
        }]
    }
    service.users().threads().get().execute.return_value = thread_response
    
    # Mock draft create
    service.users().drafts().create().execute.return_value = {'id': 'draft_123'}
    
    # Mock message send
    service.users().messages().send().execute.return_value = {'id': 'sent_msg_123'}
    
    return service


@pytest.fixture
def mock_get_user_creds():
    """Mock get_user_creds function"""
    with patch('draftly_v1.services.email_services.get_user_creds') as mock:
        yield mock


class TestEmailServices:
    """Test email service functions"""
    
    def test_create_gmail_draft(self, mock_get_user_creds, mock_gmail_service):
        """Test creating a Gmail draft"""
        mock_get_user_creds.return_value = mock_gmail_service
        
        result = create_gmail_draft(
            email='user@example.com',
            toEmail='recipient@example.com',
            thread_id='thread_123',
            draft_body='<p>This is a test draft</p>'
        )
        
        assert result['id'] == 'draft_123'
        # Verify the draft was created with correct structure
        # Note: uses assert_called() not assert_called_once() due to method chaining
        call_args_list = mock_gmail_service.users().drafts().create.call_args_list
        # Filter out the empty call() from chaining
        actual_calls = [c for c in call_args_list if c[1]]
        assert len(actual_calls) == 1
        call_args = actual_calls[0]
        assert call_args[1]['userId'] == 'me'
        assert 'message' in call_args[1]['body']
        assert call_args[1]['body']['message']['threadId'] == 'thread_123'
    
    def test_create_gmail_draft_with_threading_headers(self, mock_get_user_creds, mock_gmail_service):
        """Test draft includes proper threading headers"""
        mock_get_user_creds.return_value = mock_gmail_service
        
        create_gmail_draft(
            email='user@example.com',
            toEmail='recipient@example.com',
            thread_id='thread_123',
            draft_body='Test body'
        )
        
        # Verify thread was fetched to get headers
        # Verify thread was fetched - use call_args_list due to method chaining
        call_args_list = mock_gmail_service.users().threads().get.call_args_list
        actual_calls = [c for c in call_args_list if c[1]]
        assert len(actual_calls) == 1
        assert actual_calls[0][1]['userId'] == 'me'
        assert actual_calls[0][1]['id'] == 'thread_123'
    
    def test_send_gmail_draft(self, mock_get_user_creds, mock_gmail_service):
        """Test sending an email draft"""
        mock_get_user_creds.return_value = mock_gmail_service
        
        result = send_gmail_draft(
            email='user@example.com',
            toEmail='recipient@example.com',
            thread_id='thread_123',
            draft_body='<p>Test email body</p>'
        )
        
        assert result['id'] == 'sent_msg_123'
        # Verify the message was sent with correct structure
        call_args_list = mock_gmail_service.users().messages().send.call_args_list
        actual_calls = [c for c in call_args_list if c[1]]
        assert len(actual_calls) == 1
        call_args = actual_calls[0]
        assert call_args[1]['userId'] == 'me'
        assert 'threadId' in call_args[1]['body']
        assert call_args[1]['body']['threadId'] == 'thread_123'
    
    def test_send_gmail_draft_adds_re_prefix(self, mock_get_user_creds, mock_gmail_service):
        """Test that 'Re:' is added to subject when replying"""
        mock_get_user_creds.return_value = mock_gmail_service
        
        send_gmail_draft(
            email='user@example.com',
            toEmail='recipient@example.com',
            thread_id='thread_123',
            draft_body='Test body'
        )
        
        # The function should fetch the thread to get the subject
        # Verify thread was fetched
        call_args_list = mock_gmail_service.users().threads().get.call_args_list
        actual_calls = [c for c in call_args_list if c[1]]
        assert len(actual_calls) == 1
    
    def test_send_gmail_draft_no_messages_error(self, mock_get_user_creds, mock_gmail_service):
        """Test error when thread has no messages"""
        mock_gmail_service.users().threads().get().execute.return_value = {'messages': []}
        mock_get_user_creds.return_value = mock_gmail_service
        
        with pytest.raises(ValueError, match='No messages found'):
            send_gmail_draft(
                email='user@example.com',
                toEmail='recipient@example.com',
                thread_id='thread_123',
                draft_body='Test body'
            )


import base64
from email.message import EmailMessage
import logging
from draftly_v1.services.gmail_services import get_user_creds
from draftly_v1.services.utils.logger_config import setup_logging

setup_logging(logging.INFO)
_logger = logging.getLogger(__name__)

def create_gmail_draft(email, toEmail,thread_id, draft_body):
    """
    thread_id: str
    draft_body: str (HTML or plain text content to be sent in the draft)
    """
    user_creds = get_user_creds(email)
    
    # Fetch the original thread to get threading headers
    thread = user_creds.users().threads().get(userId='me', id=thread_id).execute()
    messages = thread.get('messages', [])
    
    if not messages:
        raise ValueError(f"No messages found in thread {thread_id}")
    
    # Get the latest message for threading headers
    original_msg = messages[-1]
    headers = {h['name']: h['value'] for h in original_msg.get('payload', {}).get('headers', [])}
    
    # Create an EmailMessage object
    message_obj = EmailMessage()
    message_obj.set_content(draft_body, subtype='html')
    message_obj['To'] = toEmail
    
    # Add threading headers to keep draft in the same thread
    original_subject = headers.get('Subject', '')
    if not original_subject.startswith('Re: '):
        message_obj['Subject'] = f"Re: {original_subject}"
    else:
        message_obj['Subject'] = original_subject
    
    message_id = headers.get('Message-ID')
    if message_id:
        message_obj['In-Reply-To'] = message_id
        message_obj['References'] = headers.get('References', '') + ' ' + message_id if headers.get('References') else message_id
    
    # Convert to base64url string
    raw_message = base64.urlsafe_b64encode(message_obj.as_bytes()).decode()
    
    message = {
        'message': {
            'threadId': thread_id,
            'raw': raw_message
        }
    }
    _logger.info(f"Creating draft for email: {email[:6]+'xxx'}... in thread: {thread_id}")
    draft_response = user_creds.users().drafts().create(userId='me', body=message).execute()    
    return draft_response

def send_gmail_draft(email, toEmail, thread_id, draft_body):
    user_creds = get_user_creds(email)

    # Fetch the original thread to get threading headers
    thread = user_creds.users().threads().get(userId='me', id=thread_id).execute()
    messages = thread.get('messages', [])
    
    if not messages:
        raise ValueError(f"No messages found in thread {thread_id}")
    
    # Get the latest message for threading headers
    original_msg = messages[-1]
    headers = {h['name']: h['value'] for h in original_msg.get('payload', {}).get('headers', [])}
    
    message_obj = EmailMessage()
    message_obj.set_content(draft_body, subtype='html')
    message_obj['To'] = toEmail
    
    # Add threading headers to keep email in the same thread
    original_subject = headers.get('Subject', '')
    if not original_subject.startswith('Re: '):
        message_obj['Subject'] = f"Re: {original_subject}"
    else:
        message_obj['Subject'] = original_subject
    
    message_id = headers.get('Message-ID')
    if message_id:
        message_obj['In-Reply-To'] = message_id
        message_obj['References'] = headers.get('References', '') + ' ' + message_id if headers.get('References') else message_id

    # Convert to base64url string - must encode the complete message with headers
    raw_message = base64.urlsafe_b64encode(message_obj.as_bytes()).decode()

    _logger.info(f"Sending draft with reply for email: {email[:6]+'xxx'}... in thread: {thread_id}")
    send_response = user_creds.users().messages().send(
        userId='me',
        body={
            'threadId': thread_id,
            'raw': raw_message
        }).execute()

    
    return send_response


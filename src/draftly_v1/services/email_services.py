import base64
from email.message import EmailMessage

def create_threaded_draft(service, user_id, original_msg_metadata, draft_content):
    """
    original_msg_metadata: dict containing 'threadId', 'Message-ID', 'Subject', 'From'
    """
    message = EmailMessage()
    message.set_content(draft_content)
    
    # Essential headers for threading 
    message['To'] = original_msg_metadata['From']
    message['Subject'] = f"Re: {original_msg_metadata['Subject']}"
    message['In-Reply-To'] = original_msg_metadata['Message-ID']
    message['References'] = original_msg_metadata['Message-ID']
    
    # Convert to base64url string
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    
    draft_body = {
        'message': {
            'threadId': original_msg_metadata['threadId'],
            'raw': raw_message
        }
    }
    
    # Execute the draft creation [cite: 24, 62]
    return service.users().drafts().create(userId=user_id, body=draft_body).execute()


def create_gmail_draft(service, thread_id, draft_body):
    """
    thread_id: str
    draft_body: dict
    """
    message = {
        'message': {
            'threadId': thread_id,
            'raw': draft_body
        }
    }
    return service.users().drafts().create(userId='me', body=message).execute()
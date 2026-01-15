import logging
import re
import base64
from fastapi import HTTPException
from googleapiclient.discovery import build 
from google.oauth2.credentials import Credentials
from google.auth.exceptions import RefreshError
from draftly_v1.services.database import get_creds_from_db
from draftly_v1.services.utils.logger_config import setup_logging
from fastapi import HTTPException, status



setup_logging(logging.INFO)
_logger = logging.getLogger(__name__)


def get_gmail_service(user_credentials_dict):
    creds = Credentials(**user_credentials_dict) 
    return build('gmail', 'v1', credentials=creds)

def get_user_creds(email: str):
    user_creds = get_creds_from_db(email) 
    try:
        service = get_gmail_service(user_creds)
    except Exception as e:
        _logger.error(f"Error getting Gmail service for {email}: {str(e)}")
        raise
    return service

async def get_subjects_batch(service, message_ids):
    subjects = {}

    #callback function to process each response in the batch
    def callback(request_id, response, exception):
        if exception is not None:
            _logger.error(f"Error for {request_id}: {exception}")
        else:
            # Extract Subject from headers
            headers = response.get('payload', {}).get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "No Subject")
            subjects[request_id] = subject

    batch = service.new_batch_http_request(callback=callback) # batch request GmailAPI

    for msg_id in message_ids:
        batch.add(service.users().messages().get(
            userId='me', 
            id=msg_id, 
            format='metadata', 
            metadataHeaders=['Subject']
        ), request_id=msg_id)

    batch.execute()
    
    return subjects

def get_threads_batch(service, thread_ids):
    threads_results = {}
    #callback function to process each response in the batch
    def callback(request_id, response, exception):
        if exception:
            _logger.error(f"Error fetching thread {request_id}: {exception}")
        else:
            # response is the full Thread resource containing all messages
            threads_results[request_id] = response.get('messages', [])

    batch = service.new_batch_http_request(callback=callback)

    # 3. Add each threadId to the batch
    for t_id in thread_ids:
        # We request the 'threads.get' method for each ID
        batch.add(
            service.users().threads().get(userId='me', id=t_id),
            request_id=t_id
        )

    # 4. Execute the batch
    batch.execute()

    return threads_results

async def get_snippets_batch(user_creds, message_ids):
    snippet_results = {}
    def callback(request_id, response, exception):
        if exception:
            _logger.error(f"Error fetching snippet for {request_id}: {exception}")
        else:
            snippet = response.get('snippet', '')
            snippet_results[request_id] = snippet
        
    batch = user_creds.new_batch_http_request(callback=callback)    
    for msg_id in message_ids:
        batch.add(user_creds.users().messages().get(
            userId='me',
            id=msg_id,
            format='minimal'  # minimal to get snippet
        ), request_id=msg_id)           
    batch.execute()
    return snippet_results

async def fetch_latest_email(email: str):
    _logger.info(f"Fetching latest email for user: {email[:6]}XXX")
    
    query = "in:inbox is:unread -category:{promotions social updates forums}" #category:primary is:unread
    try:
        user_creds = get_user_creds(email)
        # Fetch message IDs first
        results = user_creds.users().messages().list(userId='me', q=query, maxResults=10).execute()
        messages = results.get('messages', [])
        
        if not messages:
            return {"message": "No new unread emails found."}
        
        # Batch fetch all message details
        message_details = {}
        
        def callback(request_id, response, exception):
            if exception:
                _logger.error(f"Error fetching message {request_id}: {exception}")
            else:
                headers = response.get('payload', {}).get('headers', [])
                message_details[request_id] = {
                    'id': response['id'],
                    'threadId': response['threadId'],
                    'from': next((h['value'] for h in headers if h['name'] == 'From'), "Unknown"),
                    'to': next((h['value'] for h in headers if h['name'] == 'To'), "Unknown"),
                    'subject': next((h['value'] for h in headers if h['name'] == 'Subject'), "No Subject"),
                    'snippet': response.get('snippet', '')
                }
        
        batch = user_creds.new_batch_http_request(callback=callback)
        for msg in messages:
            batch.add(
            user_creds.users().messages().get(
                userId='me',
                id=msg['id'],
                format='metadata',
                metadataHeaders=['From', 'To', 'Subject']
            ),
            request_id=msg['id']
            )
        batch.execute()

         # Use a set avoid duplicates
        unique_threads = set()
        for msg in messages:
            unique_threads.add(msg['threadId'])
        # Sort and filter to only keep first occurrence of each thread
        sorted_message_details = {}
        for msg_id in message_details.keys():
            t_id = message_details[msg_id]['threadId']
            _logger.info(f"Processing message {msg_id} in thread {t_id}")
            if t_id in unique_threads:
                sorted_message_details[msg_id] = message_details[msg_id]
                unique_threads.remove(t_id)

        msg_thread_ids = {
            'msgId': list(sorted_message_details.keys()),
            'threadId': [m['threadId'] for m in sorted_message_details.values()],
            'from': [m['from'] for m in sorted_message_details.values()],
            'subject': [m['subject'] for m in sorted_message_details.values()],
            'snippet': [m['snippet'] for m in sorted_message_details.values()],
            'toEmail': [m['to'] for m in sorted_message_details.values()]   
        }
        
        return {"messages": msg_thread_ids}
    except RefreshError:
        _logger.error(f"Error fetching latest emails for {email[:6]}XXX: RefreshError.")
        raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Refresh token expired or revoked. Please login again."
                    )
    except Exception as e:
        _logger.error(f"Error fetching latest emails for {email[:6]}XXX: {str(e)}")
        raise

async def fetch_email_thread_by_id(email: str, thread_id: str):
    _logger.info(f"Fetching email thread for user: {email[:6]}XXX, Thread ID: {thread_id}")
    user_creds = get_user_creds(email)
    try:
        # Use format='full' to get complete message data without marking as read
        thread = user_creds.users().threads().get(
            userId='me', 
            id=thread_id,
            format='full'
        ).execute()
    except Exception as e:
        _logger.error(f"Error fetching email thread {thread_id} for {email[:6]}XXX: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching email thread: {str(e)}")
    
    messages = thread.get('messages', [])

    llm_context = []
    

    for idx, msg in enumerate(messages):
        parts = msg.get('payload', {}).get('parts', [])
        body = ""
        if parts:
            for part in parts:
                
                    if part.get('mimeType') == 'text/html':
                        data = part.get('body', {}).get('data', '')
                        if data:
                            if idx == len(messages) - 1: 
                                # keep only the data before gmail_quote
                                cleaned_data = re.split(r'<div class="gmail_quote', base64.urlsafe_b64decode(data).decode('utf-8'))[0]
                                cleaned_data = re.sub(r'[\r\n\t]+', ' ', cleaned_data).strip()
                                body += cleaned_data
                                
                            else:
                                body += base64.urlsafe_b64decode(data).decode('utf-8')
                                body = re.sub(r'[\r\n\t]+', ' ', body).strip()
                    else:
                        pass
        else:
            data = msg.get('payload', {}).get('body', {}).get('data', '')
            if data:
                body += base64.urlsafe_b64decode(data).decode('utf-8')
                body = re.sub(r'[\r\n\t]+', ' ', body).strip()
        
        llm_context.append({
                "message_id": msg['id'],
                "from": next((h['value'] for h in msg.get('payload', {}).get('headers', []) if h['name'] == 'From'), "Unknown Sender"),
                "to": next((h['value'] for h in msg.get('payload', {}).get('headers', []) if h['name'] == 'To'), "Unknown Recipient"),
                "date": next((h['value'] for h in msg.get('payload', {}).get('headers', []) if h['name'] == 'Date'), "Unknown Date"),
                "subject": next((h['value'] for h in msg.get('payload', {}).get('headers', []) if h['name'] == 'Subject'), "No Subject"),
                "body": body
        })
    
    # Reverse the order so LLM reads oldest to newest
    llm_context.reverse()
    
    _logger.info(f"Fetched messages in thread {thread_id} for user {email[:6]}XXX")
    _logger.debug(f"Fetched {llm_context} messages in thread {thread_id} for user {email[:6]}XXX")

    return {"thread_id": thread_id, "llm_context": llm_context}

def mark_thread_as_read(email: str, thread_id: str) -> bool:
    """Removes the 'UNREAD' label from all messages in the thread."""
    user_cred = get_user_creds(email)
    try:
        user_cred.users().threads().modify(
            userId='me',
            id=thread_id,
            body={
                'removeLabelIds': ['UNREAD']  #mark as read
            }
        ).execute()
        return True
    except Exception as e:
        _logger.error(f"Failed to mark thread as read: {e}")
        return False
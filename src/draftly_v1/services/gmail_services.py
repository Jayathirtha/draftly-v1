from googleapiclient.discovery import build 
from google.oauth2.credentials import Credentials
from draftly_v1.services.database import get_creds_from_db
from draftly_v1.services.email_services import create_gmail_draft, create_threaded_draft
from draftly_v1.services.database import log_draft_in_db
from draftly_v1.services.llm_services import generate_draft

def get_gmail_service(user_credentials_dict):
    creds = Credentials(**user_credentials_dict)
    return build('gmail', 'v1', credentials=creds)

def fetch_recent_thread(service, thread_id): # fetch the last 5 messages in the thread
    thread = service.users().threads().get(userId='me', id=thread_id).execute()
    messages = thread.get('messages', [])
    # Context logic: extract the last 3-5 message bodies for the LLM
    context = [msg['snippet'] for msg in messages[-5:]]
    print(context)
    return " \n".join(context)

async def generate_all_pending_drafts(user_id: int, draft_tone: str):
    # 1. Retrieve stored credentials from your DB [cite: 60, 56]
    user_creds = get_creds_from_db(user_id) 
    service = get_gmail_service(user_creds)

    # 2. List recent unread messages [cite: 33]
    # Query: 'is:unread' fetches only unread emails
    results = service.users().messages().list(userId='me', q='is:unread', maxResults=5).execute()
    messages = results.get('messages', [])

    if not messages:
        return {"message": "No new unread emails found."}

    generated_drafts = []
    for msg in messages:
        thread_id = msg['threadId']
        user_style = draft_tone
        
        # 3. TRIGGER: Fetch the full context of the thread [cite: 34, 38]
        thread_context = fetch_recent_thread(service, thread_id)
        
        # 4. Pass context to AI for drafting [cite: 36, 39]
        # (Assuming you have the generate_draft function from previous steps)
        ai_draft_content = generate_draft(thread_context, user_style)
        
        # 5. Create the draft in Gmail [cite: 44, 45]
        draft_response = create_threaded_draft(service, 'me', thread_id, ai_draft_content)
        
        # 6. Log the action in your DB [cite: 46, 48]
        log_draft_in_db(user_id, thread_id, "SUGGESTED")
        
        generated_drafts.append(draft_response['id'])

    return {"status": "success", "drafts_created": len(generated_drafts)}
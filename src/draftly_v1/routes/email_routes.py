"""Email management routes"""
import re
import logging
import time
from draftly_v1.services.utils.session_mangement import validate_session
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from draftly_v1.services.gmail_services import fetch_email_thread_by_id, mark_thread_as_read, fetch_latest_email
from draftly_v1.services.email_services import  create_gmail_draft, send_gmail_draft
from draftly_v1.services.llm_services import generate_draft, clean_html_for_llm
from draftly_v1.services.database import (get_creds_from_db, save_thread_context,
                                          update_user_preferences, get_user_preferences,
                                          get_user_by_email, delete_thread_context, get_thread_context)
from draftly_v1.config import MAX_EMAIL_LENGTH

_logger = logging.getLogger(__name__)
router = APIRouter(prefix="/email", tags=["email"])


def sanitize_draft_content(content: str) -> str:
    """Basic sanitization of draft content"""
    if len(content) > MAX_EMAIL_LENGTH:
        raise HTTPException(400, f"Draft too long. Maximum {MAX_EMAIL_LENGTH} characters allowed.")
    return content


@router.post("/fetch_latest")
async def fetch_unread_email(request: Request):
    
    
    """Fetch latest unread emails ids from inbox"""
    _logger.info("Fetch Unread Email Endpoint Hit")
    body = await request.json()
    req_email = await validate_session(request)
    
    if not req_email:
        raise HTTPException(status_code=400, detail="Email is required in the request body.")
    
    try:
        latest_msgs = await fetch_latest_email(email=req_email)
        _logger.debug(f"Latest messages retrieved: {latest_msgs}")
        return JSONResponse(content=latest_msgs)
    except HTTPException:
        raise
    except Exception as e:
        _logger.error(f"Error in fetch_latest_email: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching emails: {str(e)}")


@router.post("/regenerate_draft")
async def regenerate_email_draft(request: Request):
    """Regenerate email draft with different style"""
    _logger.info("Regenerate Email Draft Endpoint Hit")
    body = await request.json()
    user_email = await validate_session(request)
    thread_id = body.get("thread_id")
    email_context = get_thread_context(user_email, thread_id).thread_context
    user_style = body.get("user_style")
    try:
        # Save user's style preference
        user = get_user_by_email(user_email)
        if user and user_style:
            update_user_preferences(user.id, {"user_style": user_style})
        
        # Clean HTML content for LLM
        cleaned_context = clean_html_for_llm(email_context)
        #("Cleaned Context:", cleaned_context)
        email_draft = generate_draft(email_context=cleaned_context, user_style=user_style, sender_name=body.get("sender_name"))
        _logger.debug(f"Regenerated draft: {email_draft}")
        save_thread_context(user_email, thread_id,email_context, email_draft)
        return JSONResponse(
            content={"draft": email_draft}, 
            headers={"Content-Type": "application/json"}
        )
    except Exception as e:
        _logger.error(f"Error in regenerate_email_draft: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error regenerating email draft: {str(e)}")

@router.post("/draft")
async def fetch_email_thread(request: Request):
    """Fetch email thread and generate AI draft"""
    _logger.info("Fetch Email thread Endpoint Hit")
    body = await request.json()
    req_email = await validate_session(request)
    tone = body.get("tone")
    thread_id = body.get("threadId")

    try:
        # Get user's preferred style if no tone specified
        if not tone:
            user = get_creds_from_db(req_email)
            if user:
                preferences = get_user_preferences(user.id)
                tone = preferences.get("user_style", "Professional")  # Default to Professional
        
        thread_context = await fetch_email_thread_by_id(email=req_email, thread_id=thread_id)
        _logger.debug(f"Thread context retrieved: {thread_context}")
        
        cleaned_context = clean_html_for_llm(thread_context.get("llm_context"))
        email_draft = generate_draft(
            email_context=cleaned_context, 
            user_style=tone,
            sender_name=req_email
        )
        email_draft = re.sub(r'[\r\n\t]+', ' ', email_draft).strip()
        _logger.info("Email draft generated successfully")
        
        response_content = {
            "draft": email_draft, 
            "thread_context": thread_context
        }
        
        # Save thread context to database for future reference
        save_thread_context(user_email=req_email, thread_id=thread_id, thread_context=thread_context.get("llm_context"), draft_content= email_draft)
        return JSONResponse(content=response_content, headers={"Content-Type": "application/json"})
    except Exception as e:
        _logger.error(f"Error in fetch_email_thread_by_id: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching email thread: {str(e)}")
    
@router.post("/send")
async def send_email(request: Request):
    """Send or save email draft with automatic retry on failure"""
    _logger.info("Send Email or Draft Endpoint Hit")
    body = await request.json()
    await validate_session(request)
    user_email = body.get("email")
    recipient_email = body.get("toEmail")
    thread_id = body.get("thread_id")
    draft_only = body.get("draft_only", True)
    draft_body = sanitize_draft_content(body.get("draft_body", ""))

    # Retry configuration
    max_retries = 3
    retry_delays = [1, 2, 4]  # Exponential backoff in seconds
    
    last_error = None
    for attempt in range(max_retries):
        try:
            if draft_only:
                draft_response = create_gmail_draft(user_email, recipient_email, thread_id, draft_body)
                _logger.info(f"Draft saved successfully: {draft_response}")
                mark_thread_as_read(user_email, thread_id)
                 # Delete thread context from database after successful send
                delete_thread_context(user_email, thread_id, draft_response.get('id'))
                return JSONResponse(content={
                    "message": "Draft saved successfully", 
                    "draft_id": draft_response.get("id")
                })
            
            else:
                response = send_gmail_draft(user_email, recipient_email, thread_id, draft_body)
                _logger.info(f"Email sent successfully: {response}")
                mark_thread_as_read(user_email, thread_id)
                # Delete thread context from database after successful send
                delete_thread_context(user_email, thread_id, response.get('id'))
                return JSONResponse(content={
                    "message": "Email sent successfully", 
                    "message_id": response.get("id")
                })
        except Exception as e:
            last_error = e
            error_str = str(e).lower()
            
            # Check for specific error types that shouldn't be retried
            if any(token_error in error_str for token_error in 
                   ["token_expired", "invalid_grant", "invalid_token", "unauthorized", "401"]):
                _logger.error(f"Authentication error in send_email (attempt {attempt + 1}): {str(e)}", exc_info=True)
                raise HTTPException(
                    status_code=401, 
                    detail="Your authentication token has expired. Please log in again to continue."
                )
            
            if any(perm_error in error_str for perm_error in 
                   ["quota", "rate limit", "permission denied", "forbidden", "403"]):
                _logger.error(f"Permission/quota error in send_email: {str(e)}", exc_info=True)
                raise HTTPException(
                    status_code=403, 
                    detail=f"Unable to send email due to permission or quota restrictions: {str(e)}"
                )
            
            # retry with exponential backoff
            if attempt < max_retries - 1:
                retry_delay = retry_delays[attempt]
                _logger.warning(
                    f"Attempt {attempt + 1} failed to send email. Retrying in {retry_delay}s. Error: {str(e)}"
                )
                time.sleep(retry_delay)
            else:
                _logger.error(f"All {max_retries} attempts failed to send email: {str(e)}", exc_info=True)
    
    raise HTTPException(
        status_code=500, 
        detail=f"Failed to send email after {max_retries} attempts. Please try again later. Last error: {str(last_error)}"
    )


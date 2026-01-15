import logging
import os
from draftly_v1.services.database import get_db_session
from draftly_v1.model.UserSession import UserSession
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi import Header, HTTPException, Depends, Request
from draftly_v1.services.utils.logger_config import setup_logging

setup_logging(logging.INFO)
_logger = logging.getLogger(__name__)

async def validate_session(
    request: Request = None,
    session_token: str = None
):
    _logger.info("Validating session token")
    
    token = session_token
    
    if request and not token:
        token = request.cookies.get("session_token")
    
    if not token:
        raise HTTPException(status_code=401, detail="No session token provided")
    
    db: Session = get_db_session()
    session = db.query(UserSession).filter_by(session_token=token).first()
    
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")
    

    if datetime.now() > session.expires_at:
        db.delete(session)
        db.commit()
        raise HTTPException(status_code=401, detail="Session expired. Please log in again.")
    
    return session.user_email




def create_user_session(user_email: str):
    _logger.info(f"Creating user session for {user_email}")
    db = get_db_session()
    try:
        rawString = datetime.now().isoformat() + "-" + user_email + "-" + os.urandom(16).hex()

        sessionToken = rawString.encode('utf-8').hex()
        expiration_time = datetime.now() + timedelta(hours=2) # 2 hours session
    
        # Check if session already exists for this user
        existing_session = db.query(UserSession).filter_by(user_email=user_email).first()
        
        if existing_session:
            # Update existing session
            _logger.info(f"Updating existing session for {user_email}")
            existing_session.session_token = sessionToken
            existing_session.expires_at = expiration_time
            db.commit()
            return sessionToken
        else:
            # Create new session
            _logger.info(f"Creating new session for {user_email}")
            new_session = UserSession(
                user_email=user_email,
                session_token=sessionToken,
                expires_at=expiration_time
            )
        
            db.add(new_session)
            db.commit()
            return sessionToken
    except Exception as e:
        db.rollback()
        _logger.error(f"Error creating user session for {user_email}: {str(e)}", exc_info=True)
        raise Exception("Error creating user session")
    finally:
        db.close()
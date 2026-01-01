from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime, timezone
from pathlib import Path
import json
import os
import logging
from draftly_v1.model.DraftLog import DraftLog, get_db
from draftly_v1.model.User import User  # Local import to avoid cyclic issues

_logger = logging.getLogger(__name__)

Base = declarative_base()




# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./draftly.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db_session() -> Session:
    """Get a database session"""
    db = SessionLocal()
    try:
        return db
    finally:
        pass  # Session will be closed by caller

def get_creds_from_db(user_id: int) -> dict:
    
    """
    Retrieve user credentials from the database and return in format for Google OAuth Credentials.
    
    Args:
        user_id (int): The user's ID in the database
        
    Returns:
        dict: Credentials dictionary with token, refresh_token, token_uri, client_id, client_secret, scopes
        
    Raises:
        ValueError: If user is not found in database
    """
    db = get_db_session()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise ValueError(f"User with id {user_id} not found in database")
        
        # Get client secrets from the JSON file
        BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
        CLIENT_SECRETS_FILE = BASE_DIR / "resources" / "client_secret_695824097654-6bmqmtgpd8t23tkve76kvmje9u0fga9f.apps.googleusercontent.com.json"
        
        if not CLIENT_SECRETS_FILE.exists():
            raise FileNotFoundError(f"Client secrets file not found at: {CLIENT_SECRETS_FILE}")
        
        with open(CLIENT_SECRETS_FILE, 'r') as f:
            client_secrets = json.load(f)
        
        # Extract client_id and client_secret from the JSON structure
        # Google OAuth JSON typically has structure: {"web": {"client_id": "...", "client_secret": "..."}}
        if "web" in client_secrets:
            client_id = client_secrets["web"]["client_id"]
            client_secret = client_secrets["web"]["client_secret"]
        elif "installed" in client_secrets:
            client_id = client_secrets["installed"]["client_id"]
            client_secret = client_secrets["installed"]["client_secret"]
        else:
            # Fallback: assume top-level keys
            client_id = client_secrets.get("client_id")
            client_secret = client_secrets.get("client_secret")
        
        if not client_id or not client_secret:
            raise ValueError("Could not extract client_id and client_secret from secrets file")
        
        # Return credentials in the format expected by google.oauth2.credentials.Credentials
        creds_dict = {
            "token": None,  # Access token will be refreshed automatically
            "refresh_token": user.refresh_token,
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": client_id,
            "client_secret": client_secret,
            "scopes": [
                'https://www.googleapis.com/auth/gmail.modify',
                'https://www.googleapis.com/auth/gmail.readonly'
            ]
        }
        
        return creds_dict
        
    except Exception as e:
        _logger.error(f"Error retrieving credentials from DB for user {user_id}: {str(e)}", exc_info=True)
        raise
    finally:
        db.close() 



def store_user(db_session, user_id, email, refresh_token, style_profile):
    """
    Store a new user or update existing user in the database.
    """
   
    user = db_session.query(User).filter(User.id == user_id).first()
    if user:
        # Update fields if user exists
        user.email = email
        user.refresh_token = refresh_token
        if style_profile:
            user.style_profile = style_profile
    else:
        user = User(id=user_id, email=email, refresh_token=refresh_token, style_profile=style_profile)
        db_session.add(user)
    db_session.commit()
    return user

def log_draft_in_db(user_id, thread_id, status, draft_id=None):
    """
    Store a draft log in the database.
    """
    
    db = next(get_db())
    try:
        draft_log = DraftLog(
            user_id=user_id,
            thread_id=thread_id,
            status=status,
            draft_id=draft_id
        )
        db.add(draft_log)
        db.commit()
        return draft_log
    finally:
        db.close()



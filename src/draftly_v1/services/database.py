import json
import os
import logging
from sqlalchemy import create_engine
from datetime import datetime, timezone
from sqlalchemy.orm import sessionmaker, Session
from pathlib import Path
from draftly_v1.model.base import Base
from draftly_v1.model.User import User
from draftly_v1.model.UserSession import UserSession
from draftly_v1.model.DraftLog import DraftLog

_logger = logging.getLogger(__name__)


DATABASE_URL=os.getenv("DATABASE_URL")


engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

def get_db_session() -> Session:
    """Get a database session"""
    
    db = SessionLocal()
    try:
        return db
    finally:
        pass  # Session will be closed by caller

def get_user_by_email(email: str) -> User | None:
    """
    Retrieve user from the database by email.
    
    Args:
        email (str): The user's email address
        
    Returns:
        User | None: User object if found, None otherwise
    """
    db = get_db_session()
    try:
        user = db.query(User).filter(User.email == email).first()
        return user
    except Exception as e:
        _logger.error(f"Error retrieving user by email {email}: {str(e)}", exc_info=True)
        raise
    finally:
        db.close()

def get_creds_from_db(email: str,) -> dict:
    
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
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            raise ValueError(f"User with email {email} not found in database")
        
        # Get client secrets from the JSON file
        BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
        CLIENT_SECRETS_FILE = BASE_DIR / "resources" / "client_secret.json"
        
        if not CLIENT_SECRETS_FILE.exists():
            raise FileNotFoundError(f"Client secrets file not found at: {CLIENT_SECRETS_FILE}")
        
        with open(CLIENT_SECRETS_FILE, 'r') as f:
            client_secrets = json.load(f)
        
        # Extract client_id and client_secret from the JSON structure
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
        _logger.error(f"Error retrieving credentials from DB for user {email}: {str(e)}", exc_info=True)
        raise
    finally:
        db.close() 

def store_user(email: str, refresh_token: str, style_profile: str = None) -> User:
    """Create or update a user record."""
    session = get_db_session()
    try:
        user = session.query(User).filter(User.email == email).first()
        if user:
            user.email = email
            user.refresh_token = refresh_token
            if style_profile is not None:
                user.style_profile = style_profile
        else:
            user = User(
                email=email,
                refresh_token=refresh_token,
                style_profile=style_profile
            )
            session.add(user)

        session.commit()
        session.refresh(user)
        return user
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()



def update_user_preferences(user_id: int, preferences: dict) -> bool:
    """Update user style_profile with recent style preference."""
    session = get_db_session()
    try:
        user = session.query(User).filter(User.id == user_id).first()
        if user:
            # Update style_profile with user_style from preferences
            if "user_style" in preferences:
                user.style_profile = preferences["user_style"]
                session.commit()
                _logger.info(f"Style profile updated for user {user_id}: {preferences['user_style']}")
                return True
        return False
    except Exception as e:
        session.rollback()
        _logger.error(f"Error updating style profile: {str(e)}")
        return False
    finally:
        session.close()


def get_user_preferences(user_id: int) -> dict:
    """Get user style preferences from style_profile."""
    session = get_db_session()
    try:
        user = session.query(User).filter(User.id == user_id).first()
        if user and user.style_profile:
            return {"user_style": user.style_profile}
        return {}
    except Exception as e:
        _logger.error(f"Error retrieving preferences: {str(e)}")
        return {}
    finally:
        session.close()


def save_thread_context(user_email: str, thread_id: str, thread_context: list, draft_content: str = None) -> bool:
    """Save email thread context to database for future reference."""
    session = get_db_session()
    try:
        user = session.query(User).filter(User.email == user_email).first()
        if not user:
            _logger.error(f"User not found: {user_email}")
            return False
        
        # Check if thread context already exists
        draft = session.query(DraftLog).filter(
            DraftLog.user_id == user.id,
            DraftLog.thread_id == thread_id,
            DraftLog.status == 'DRAFT'
        ).first()
        
        # Extract recipient email (the one that's NOT the user's email)
        recipient_email = ""
        subject = ""
        if thread_context and len(thread_context) > 0:
            initial_msg = thread_context[-1]
            from_email = initial_msg.get("from", "")
            to_email = initial_msg.get("to", "")
            
            # Select the email that's not the user's email
            if from_email and from_email.lower() != user_email.lower():
                recipient_email = from_email
            elif to_email and to_email.lower() != user_email.lower():
                recipient_email = to_email
            
            subject = initial_msg.get("subject", "")
        
        if draft and draft.thread_context:
            draft.thread_context = thread_context
            if recipient_email:
                draft.recipient_email = recipient_email
            if subject:
                draft.subject = subject
            draft.last_updated_at = datetime.now(timezone.utc)
            draft.draft_content = draft_content if draft_content else ""
        else:
            # Create new draft log entry with thread context
            draft = DraftLog(
                user_id=user.id,
                thread_id=thread_id,
                recipient_email=recipient_email,
                subject=subject,
                draft_content= draft_content if draft_content else "",
                thread_context=thread_context,
                status='DRAFT'
            )
            session.add(draft)
        
        session.commit()
        _logger.info(f"Thread context saved for thread {thread_id}")
        return True
    except Exception as e:
        session.rollback()
        _logger.error(f"Error saving thread context: {str(e)}")
        return False
    finally:
        session.close()


def delete_thread_context(user_email: str, thread_id: str, gmail_draft_id: str) -> bool:
    """Delete thread context from database after email is sent."""
    session = get_db_session()
    try:
        user = session.query(User).filter(User.email == user_email).first()
        if not user:
            return False
        
        # Find and update draft to clear thread context
        draft = session.query(DraftLog).filter(
            DraftLog.user_id == user.id,
            DraftLog.thread_id == thread_id,
            DraftLog.status == 'DRAFT'
        ).first()
        
        if draft:
            draft.thread_context = None
            draft.status = 'SENT'
            draft.last_updated_at = datetime.now(timezone.utc)
            draft.gmail_draft_id = gmail_draft_id
            session.commit()
            _logger.info(f"Thread context deleted for thread {thread_id}")
            return True
        return False
    except Exception as e:
        session.rollback()
        _logger.error(f"Error deleting thread context: {str(e)}")
        return False
    finally:
        session.close()


def get_thread_context(user_email: str, thread_id: str) -> list:
    """Get saved thread context from database."""
    session = get_db_session()
    try:
        user = session.query(User).filter(User.email == user_email).first()
        if not user:
            _logger.warning(f"User not found: {user_email}")
            return []
        
        # Find draft with thread context
        draft = session.query(DraftLog).filter(
            DraftLog.user_id == user.id,
            DraftLog.thread_id == thread_id,
            DraftLog.status == 'DRAFT'
        ).first()
        
        if draft and draft.thread_context:
            _logger.info(f"Thread context retrieved for thread {thread_id}")
            return draft
        
        _logger.info(f"No thread context found for thread {thread_id}")
        return []
    except Exception as e:
        _logger.error(f"Error retrieving thread context: {str(e)}")
        return []
    finally:
        session.close()

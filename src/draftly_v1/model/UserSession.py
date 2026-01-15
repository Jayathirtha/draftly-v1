from sqlalchemy import Column, DateTime, Integer, String
from draftly_v1.model.base import Base

class UserSession(Base):
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True)
    user_email = Column(String, index=True)
    session_token = Column(String, unique=True)
    expires_at = Column(DateTime)
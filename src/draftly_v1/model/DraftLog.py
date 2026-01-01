from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timezone

Base = declarative_base()


class DraftLog(Base):
    __tablename__ = "draft_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    thread_id = Column(String)
    status = Column(String) # e.g., "PENDING", "APPROVED", "SENT"
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
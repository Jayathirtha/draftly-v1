from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from datetime import datetime, timezone
from draftly_v1.model.base import Base


class DraftLog(Base):
    """Store email drafts with content and metadata"""
    __tablename__ = "draft_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    thread_id = Column(String, nullable=False, index=True)
    recipient_email = Column(String, nullable=False)
    subject = Column(String)
    draft_content = Column(Text, nullable=False)  # HTML content of the draft
    gmail_draft_id = Column(String)  # Gmail draft ID if saved to Gmail
    thread_context = Column(JSON, nullable=True)  # Store thread context for reference
    status = Column(String, nullable=False, index=True)  # DRAFT, SENT, DELETED
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

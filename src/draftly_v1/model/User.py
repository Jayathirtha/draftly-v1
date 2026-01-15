from sqlalchemy import Column, Integer, String, JSON
from draftly_v1.model.base import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False, index=True)
    refresh_token = Column(String, nullable=False)
    style_profile = Column(String, nullable=True) 
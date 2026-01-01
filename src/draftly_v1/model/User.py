from sqlalchemy import Column, Integer, String, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    refresh_token = Column(String, nullable=False)
    style_profile = Column(JSON, nullable=True) # Stores learned tone and phrases
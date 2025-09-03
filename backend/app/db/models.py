# backend/app/db/models.py
from sqlalchemy import Column, String, DateTime
from datetime import datetime
from .database import Base 

class Domain(Base):
    __tablename__ = "domains"

    domain_name = Column(String, primary_key=True, index=True)
    updated_on = Column(DateTime, default=datetime.utcnow)

class AliasDomain(Base):
    __tablename__ = "alias_domains"

    domain_name = Column(String, primary_key=True, index=True)
    updated_on = Column(DateTime, default=datetime.utcnow)
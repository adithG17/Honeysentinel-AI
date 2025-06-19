from sqlalchemy import Column, Integer, String, Float, Boolean
from .database import Base

class AnalyzedMessage(Base):
    __tablename__ = "analyzed_messages"

    id = Column(Integer, primary_key=True, index=True)
    message = Column(String, nullable=False)
    label = Column(String, nullable=False)
    score = Column(Float, nullable=False)
    risk = Column(Boolean, nullable=False)
    keywords = Column(String)
    honeytrap_risk = Column(Boolean, nullable=True)  # ✅ ADD THIS

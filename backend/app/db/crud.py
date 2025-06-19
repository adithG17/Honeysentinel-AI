from sqlalchemy.orm import Session
from . import models

def save_analysis(db: Session, message: str, label: str, score: float, risk: bool, keywords: list):
    db_message = models.AnalyzedMessage(
        message=message,
        label=label,
        score=score,
        risk=risk,
        keywords=",".join(keywords)  # ✅ join keywords list into a string
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message

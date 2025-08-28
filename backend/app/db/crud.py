from sqlalchemy.orm import Session
from . import models, schemas
from datetime import datetime
from backend.app.db import models

def bulk_insert_domains(db: Session, domains: list[str]):
    for d in domains:
        if not db.query(models.Domain).filter(models.Domain.domain_name == d).first():
            db.add(models.Domain(domain_name=d, updated_on=datetime.utcnow()))
    db.commit()


def is_disposable(db: Session, domain: str) -> bool:
    """Check if a domain exists in the disposable domains table"""
    domain = domain.strip().lower()
    result = db.query(models.Domain).filter(models.Domain.domain_name == domain).first()
    return result is not None


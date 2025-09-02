from sqlalchemy.orm import Session
from app.db.models import Domain
from backend.app.analyzers.gmail_analyzer import extract_domain

def check_domain(email: str, db: Session) -> dict:
    """Check if the domain of the email exists in the disposable/bad domains DB"""
    try:
        domain = extract_domain(email)
    except Exception:
        return {"valid": False, "reason": "Invalid email format"}

    match = db.query(Domain).filter_by(domain_name=domain).first()

    if match:
        return {"valid": False, "reason": "Domain is disposable/banned", "domain": domain}
    else:
        return {"valid": True, "reason": "Domain is allowed", "domain": domain}

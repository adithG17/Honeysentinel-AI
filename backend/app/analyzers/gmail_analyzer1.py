from sqlalchemy.orm import Session
from backend.app.db.models import Domain,AliasDomain 
from backend.app.analyzers.gmail_analyzer import extract_domain
import whois
from datetime import datetime
import socket
import time
from backend.app.db import crud

def check_domain(email: str, db: Session) -> dict:
    """
    Comprehensive domain check including disposable validation and WHOIS information
    """
    domain = extract_domain(email)
    
    if not domain:
        return {
            "valid": False,
            "reason": "Invalid email format",
            "domain": "",
            "whois": None,
            "status": "Invalid email"
        }

    # Check if domain is disposable
    match_disposable = db.query(Domain).filter_by(domain_name=domain).first()
    is_disposable = match_disposable is not None

    # Check if domain is an alias
    match_alias = db.query(AliasDomain).filter_by(domain_name=domain).first()
    is_alias = match_alias is not None

    # Get WHOIS information
    whois_info = get_whois_info(domain)
    
    # Build comprehensive result
    result = {
        "email": email,
        "domain": domain,
        "valid": not is_disposable,
        "status": "Disposable email" if is_disposable else "Legit email",
        "reason": "Domain is disposable/banned" if is_disposable else "Domain is Alias" if is_alias else "Domain is allowed",
        "whois_info": whois_info if whois_info["success"] else {"error": whois_info["error"]}
    }
    
    # Add domain age analysis if WHOIS was successful
    if whois_info["success"] and "domain_age_years" in whois_info["data"]:
        domain_age = whois_info["data"]["domain_age_years"]
        result["domain_age_years"] = domain_age
        result["domain_age_analysis"] = "Old domain (likely legitimate)" if domain_age > 1 else "New domain (exercise caution)"
    
    return result

def get_whois_info(domain: str) -> dict:
    """
    Get WHOIS information for a domain with error handling and timeout protection
    """
    try:
        socket.setdefaulttimeout(10)
        whois_data = whois.whois(domain)
        
        whois_info = {
            "domain_name": whois_data.domain_name,
            "registrar": whois_data.registrar,
            "creation_date": whois_data.creation_date,
            "expiration_date": whois_data.expiration_date,
            "updated_date": whois_data.updated_date,
            "name_servers": whois_data.name_servers,
            "status": whois_data.status,
            "emails": whois_data.emails,
            "org": whois_data.org,
            "country": whois_data.country,
            "city": whois_data.city,
            "state": whois_data.state,
        }
        
        # Convert dates to strings for JSON serialization
        date_fields = ["creation_date", "expiration_date", "updated_date"]
        for field in date_fields:
            if whois_info[field]:
                if isinstance(whois_info[field], list):
                    whois_info[field] = [date.isoformat() if hasattr(date, 'isoformat') else str(date) 
                                      for date in whois_info[field]]
                elif hasattr(whois_info[field], 'isoformat'):
                    whois_info[field] = whois_info[field].isoformat()
        
        # Calculate domain age
        if whois_info["creation_date"]:
            if isinstance(whois_info["creation_date"], list):
                creation_date_str = whois_info["creation_date"][0]
            else:
                creation_date_str = whois_info["creation_date"]
            
            try:
                if 'T' in creation_date_str:
                    creation_date = datetime.fromisoformat(creation_date_str.replace('Z', '+00:00'))
                else:
                    creation_date = datetime.strptime(creation_date_str.split('T')[0], '%Y-%m-%d')
                
                domain_age = datetime.now().year - creation_date.year
                whois_info["domain_age_years"] = domain_age
            except (ValueError, TypeError):
                pass
        
        return {"success": True, "data": whois_info, "error": None}
        
    except whois.parser.PywhoisError as e:
        return {"success": False, "data": None, "error": f"WHOIS lookup failed: {str(e)}"}
    except socket.timeout:
        return {"success": False, "data": None, "error": "WHOIS lookup timed out"}
    except Exception as e:
        return {"success": False, "data": None, "error": f"Unexpected error: {str(e)}"}
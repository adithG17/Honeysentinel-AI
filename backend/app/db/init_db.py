# backend/app/db/init_db.py
from .database import engine, SessionLocal, Base
from .models import Domain
import requests
from datetime import datetime

def init_db():
    Base.metadata.create_all(bind=engine)

def load_domains():
    urls = [
        "https://raw.githubusercontent.com/disposable/disposable-email-domains/master/domains.txt",
        "https://raw.githubusercontent.com/7c/fakefilter/main/txt/data.txt"
    ]

    db = SessionLocal()

    for url in urls:
        try:
            response = requests.get(url)
            response.raise_for_status()
            domains = response.text.splitlines()

            for domain in domains:
                domain = domain.strip().lower()
                if domain and not db.query(Domain).filter_by(domain_name=domain).first():
                    db.add(Domain(domain_name=domain, updated_on=datetime.utcnow()))

            db.commit()
            print(f"✅ Loaded domains from {url}")

        except Exception as e:
            print(f"❌ Failed to load {url}: {e}")

    db.close()

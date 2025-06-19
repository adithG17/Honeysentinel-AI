from app.db.database import Base, engine
from app.db import models

print("Creating database tables...")
Base.metadata.create_all(bind=engine)
print("✅ Tables created successfully.")

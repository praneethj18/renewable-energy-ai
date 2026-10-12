from backend.app.db.database import Base, engine
from backend.app.db import models

def create_tables():
    Base.metadata.create_all(bind=engine)
    print("SUCCESS: All database tables created successfully.")

if __name__ == "__main__":
    create_tables()
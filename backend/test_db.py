from sqlalchemy import text

from backend.app.db.database import engine

try:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT version()"))
        print("PostgreSQL connection successful!")
        print(result.scalar())
except Exception as exc:
    print("PostgreSQL connection failed:")
    print(exc)
from sqlalchemy import create_engine, text
from config import Config

uri = Config.SQLALCHEMY_DATABASE_URI
engine = create_engine(uri)

with engine.connect() as conn:
    print("--- USERS IN DB ---")
    result = conn.execute(text("SELECT id, email, is_verified FROM users"))
    for row in result:
        print(row)

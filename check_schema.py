from sqlalchemy import create_engine, text
from config import Config

uri = Config.SQLALCHEMY_DATABASE_URI
engine = create_engine(uri)

with engine.connect() as conn:
    print("--- USERS TABLE COLUMNS ---")
    result = conn.execute(text("SHOW COLUMNS FROM users"))
    for row in result:
        print(row[0])

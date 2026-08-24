import os
from sqlalchemy import create_engine, text
from config import Config

def migrate():
    # Use the connection URI from config
    uri = Config.SQLALCHEMY_DATABASE_URI
    print(f"Connecting to database to run migration...")
    
    engine = create_engine(uri)
    
    with engine.begin() as conn:
        try:
            # Add is_verified column
            print("Adding is_verified column...")
            conn.execute(text("ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT FALSE NOT NULL;"))
            
            # Default existing users to verified so they aren't locked out
            print("Setting existing users to verified...")
            conn.execute(text("UPDATE users SET is_verified = TRUE;"))
            
            # Add verification code columns
            print("Adding verification_code columns...")
            conn.execute(text("ALTER TABLE users ADD COLUMN verification_code VARCHAR(6);"))
            conn.execute(text("ALTER TABLE users ADD COLUMN verification_code_expires_at DATETIME;"))
            
            print("Migration completed successfully!")
        except Exception as e:
            print(f"An error occurred (columns might already exist): {e}")

if __name__ == "__main__":
    migrate()

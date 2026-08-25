import sys
import traceback
from datetime import datetime, timedelta
sys.path.append('.')
from app import create_app
from database.models import db, User
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    try:
        new_user = User(
            name="Debug Tester",
            email="debug@example.com",
            password=generate_password_hash("password123"),
            business_name="Test Business",
            business_type="Retail",
            role='Admin',
            is_verified=False,
            verification_code="123456",
            verification_code_expires_at=datetime.utcnow() + timedelta(minutes=10)
        )
        db.session.add(new_user)
        db.session.commit()
        print("SUCCESS! User added.")
    except Exception as e:
        print("ERROR IN DB COMMIT:")
        traceback.print_exc()
        db.session.rollback()

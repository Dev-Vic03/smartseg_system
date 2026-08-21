import os
import time
import io

# Set env var before importing create_app so config.py picks it up
os.environ['DATABASE_URL'] = 'sqlite:///:memory:' 

from app import create_app
from database.models import db, User, Customer, Segment

def test_batch_upload():
    print("Initializing test app...")
    app = create_app()
    
    # Overwrite just in case config uses a different key or hardcodes it
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.test_client() as client:
        with app.app_context():
            # Drop everything and recreate in the test DB
            db.drop_all()
            db.create_all()
            
            # Create a test user
            user = User(name='Test User', email='test@example.com', password='password123', role='Admin')
            db.session.add(user)
            db.session.commit()
            user_id = user.id
            print(f"Created Test User with ID: {user_id}")

            # Simulate login by modifying the session
            with client.session_transaction() as sess:
                sess['user_id'] = user_id
                sess['role'] = 'Admin'
                
            # Read the mock CSV file
            with open('mock_rfm_data.csv', 'rb') as f:
                csv_data = f.read()
                
            print(f"Loaded CSV data, size: {len(csv_data)} bytes")
            
            data = {
                'file': (io.BytesIO(csv_data), 'mock_rfm_data.csv')
            }

            print("Testing /upload_csv endpoint...")
            start_time = time.time()
            response = client.post('/upload_csv', data=data, content_type='multipart/form-data')
            end_time = time.time()
            
            print(f"Response Status: {response.status_code}")
            print(f"Response Data: {response.json}")
            print(f"Time Taken: {end_time - start_time:.4f} seconds")
            
            if response.status_code == 200:
                customer_count = Customer.query.count()
                segment_count = Segment.query.count()
                print(f"Total Customers inserted: {customer_count}")
                print(f"Total Segments inserted: {segment_count}")
                
                assert customer_count == response.json['processed'], "Customer count mismatch!"
                assert segment_count == response.json['processed'], "Segment count mismatch!"
                print("All integrity checks passed successfully!")
            else:
                print("Test failed!")

if __name__ == '__main__':
    test_batch_upload()

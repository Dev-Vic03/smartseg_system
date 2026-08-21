import io, time
from app import create_app
from database.models import db, User

t_start = time.time()
print(f"[{time.time() - t_start:.2f}s] Starting test script...")

app = create_app()
with app.app_context():
    print(f"[{time.time() - t_start:.2f}s] App context created. Querying user...")
    user = User.query.first()
    
    if user:
        print(f"[{time.time() - t_start:.2f}s] User found. Reading mock data...")
        with open('mock_rfm_data.csv', 'r') as f:
            content = f.read()
        
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['user_id'] = user.id
                sess['user_name'] = user.name
                sess['user_role'] = user.role
                sess['fresh_login'] = True
            
            print(f"[{time.time() - t_start:.2f}s] Sending POST to /api/upload_csv...")
            data = {'file': (io.BytesIO(content.encode()), 'mock_rfm_data.csv')}
            
            t0 = time.time()
            res = client.post('/api/upload_csv', data=data, content_type='multipart/form-data')
            t1 = time.time()
            
            print(f"\n====================================")
            print(f'Upload API response time: {round((t1-t0)*1000, 2)} ms')
            print(f"====================================\n")
            
            print('Status code:', res.status_code)
            try:
                print('Response payload:', res.get_json())
            except:
                print('No JSON payload returned')
    else:
        print("No user found in DB.")

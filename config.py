import os
from pathlib import Path
from urllib.parse import quote_plus

BASE_DIR = Path(__file__).resolve().parent

# Safely load .env file
env_file = BASE_DIR / '.env'
if env_file.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(env_file, override=True)
    except ImportError:
        # Fallback simple parser if python-dotenv is not installed
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    os.environ[k.strip()] = v.strip()

def get_database_uri():
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        return database_url.replace('mysql://', 'mysql+pymysql://', 1)

    password = quote_plus(os.environ.get('DB_PASSWORD', ''))
    host = os.environ.get('DB_HOST', '127.0.0.1')
    port = os.environ.get('DB_PORT', '3306')
    database = os.environ.get('DB_NAME', 'smartseg_db')
    username = quote_plus(os.environ.get('DB_USER', 'root'))

    # If DB_TYPE is set to sqlite or if local dev uses sqlite fallback
    if os.environ.get('USE_SQLITE', 'false').lower() == 'true':
        return f"sqlite:///{BASE_DIR / 'instance' / 'smartseg.db'}"

    return f'mysql+pymysql://{username}:{password}@{host}:{port}/{database}'


CA_CERT = BASE_DIR / 'ca.pem'
connect_args = {}
if CA_CERT.exists():
    connect_args['ssl'] = {'ca': str(CA_CERT)}

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'mr.tee2008')

    SQLALCHEMY_DATABASE_URI = get_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 280,
        'pool_pre_ping': True,
        'connect_args': connect_args,
    }

    # Flask-Mail SMTP Configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() in ['true', 'on', '1']
    MAIL_USE_SSL = False
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'taiwoaroma2234@gmail.com')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')  # Set in Render Environment Variables
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', ('SmartSeg System', 'taiwoaroma2234@gmail.com'))
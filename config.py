import os
from pathlib import Path
from urllib.parse import quote_plus


BASE_DIR = Path(__file__).resolve().parent


def get_database_uri():
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        return database_url.replace('mysql://', 'mysql+pymysql://', 1)

    password = quote_plus(os.environ.get('AIVEN_DB_PASSWORD', ''))
    host = os.environ.get(
        'AIVEN_DB_HOST',
        'mysql-1d0fe3b3-taiwoaroma2234-e45f.j.aivencloud.com'
    )
    port = os.environ.get('AIVEN_DB_PORT', '16545')
    database = os.environ.get('AIVEN_DB_NAME', 'defaultdb')
    username = quote_plus(os.environ.get('AIVEN_DB_USER', 'avnadmin'))

    return f'mysql+pymysql://{username}:{password}@{host}:{port}/{database}'


CA_CERT = BASE_DIR / 'ca.pem'

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'mr.tee2008')

    SQLALCHEMY_DATABASE_URI = get_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 280,
        'pool_pre_ping': True,
        'connect_args': {
            'ssl': {'ca': str(CA_CERT)},
        },
    }

    # Flask-Mail SMTP Configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() in ['true', 'on', '1']
    MAIL_USE_SSL = False
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'taiwoaroma2234@gmail.com')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')  # Set in Render Environment Variables
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', ('SmartSeg System', 'taiwoaroma2234@gmail.com'))
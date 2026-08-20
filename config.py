import os

class Config:
        SECRET_KEY = os.environ.get('SECRET_KEY', 'mr.tee2008')
        SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:mr.tee2008@localhost/smartseg_db'
        SQLALCHEMY_TRACK_MODIFICATIONS = False

        # Flask-Mail SMTP Configuration
        MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
        MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
        MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() in ['true', 'on', '1']
        MAIL_USE_SSL = False
        MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'taiwoaroma2234@gmail.com')
        MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', 'vayt iiwc qkiv lqom')  # 16-character App Password
        MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', ('SmartSeg System', 'taiwoaroma2234@gmail.com'))

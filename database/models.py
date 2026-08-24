from datetime import datetime
import pyotp
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'

    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(100), nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password      = db.Column(db.String(255), nullable=False)
    business_name = db.Column(db.String(150))
    business_type = db.Column(db.String(50))
    
    role          = db.Column(db.String(20), default='Admin', nullable=False)
    mfa_secret    = db.Column(db.String(32), default=pyotp.random_base32)
    mfa_enabled   = db.Column(db.Boolean, default=False, nullable=False)
    
    # Email Verification
    is_verified   = db.Column(db.Boolean, default=False, nullable=False)
    verification_code = db.Column(db.String(6), nullable=True)
    verification_code_expires_at = db.Column(db.DateTime, nullable=True)
    
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships with cascades
    customers     = db.relationship('Customer', backref='owner', cascade="all, delete-orphan", lazy=True)
    sales         = db.relationship('Sale', backref='owner', cascade="all, delete-orphan", lazy=True)
    integrations  = db.relationship('Integration', backref='owner', cascade="all, delete-orphan", lazy=True)


class Customer(db.Model):
    __tablename__ = 'customers'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=True)
    age = db.Column(db.Integer, nullable=True)
    gender = db.Column(db.String(20), nullable=True)
    phone = db.Column(db.String(30), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    location = db.Column(db.String(100), nullable=True)
    occupation = db.Column(db.String(100), nullable=True)
    is_anonymized = db.Column(db.Boolean, default=False) 
class Sale(db.Model):
    __tablename__ = 'sales'

    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False, index=True)
    product     = db.Column(db.String(150))
    quantity    = db.Column(db.Integer, default=1)
    price       = db.Column(db.Float, nullable=False)
    sale_date   = db.Column(db.DateTime, default=datetime.utcnow)


class Segment(db.Model):
    __tablename__ = 'segments'

    id            = db.Column(db.Integer, primary_key=True)
    customer_id   = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False, index=True)
    recency       = db.Column(db.Integer)
    frequency     = db.Column(db.Integer)
    monetary      = db.Column(db.Float)
    cluster_label = db.Column(db.Integer)
    segment_name  = db.Column(db.String(50), index=True)
    computed_at   = db.Column(db.DateTime, default=datetime.utcnow)


class Integration(db.Model):
    __tablename__ = 'integrations'

    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    platform     = db.Column(db.String(50), nullable=False)
    api_key      = db.Column(db.String(255))
    is_active    = db.Column(db.Boolean, default=True)
    connected_at = db.Column(db.DateTime, default=datetime.utcnow)


class Campaign(db.Model):
    __tablename__ = 'campaigns'

    id            = db.Column(db.Integer, primary_key=True)
    segment_name  = db.Column(db.String(50), nullable=False)
    title         = db.Column(db.String(150), nullable=False)
    subject       = db.Column(db.String(200), nullable=False)
    body_template = db.Column(db.Text, nullable=False)
    user_id       = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)


class WorkspaceSetting(db.Model):
    __tablename__ = 'workspace_settings'

    id               = db.Column(db.Integer, primary_key=True)
    user_id          = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    api_key          = db.Column(db.String(64), nullable=True)
    theme_preference = db.Column(db.String(10), default='dark')
    currency_symbol  = db.Column(db.String(5), default='$')
    updated_at       = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
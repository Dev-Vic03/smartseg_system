from functools import wraps
from flask import session, redirect, url_for, flash
from database.models import User

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or not session.get('user_name') or not session.get('user_role'):
            session.clear()
            flash("Session expired or invalid. Please log in again.", "error")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or not session.get('user_role'):
            session.clear()
            flash("Session expired or invalid. Please log in again.", "error")
            return redirect(url_for('auth.login'))
        
        user_role = session.get('user_role', 'View-Only')
        if user_role != 'Admin':
            flash('Access denied. Admin privileges are required for this action.', 'error')
            return redirect(url_for('dashboard'))
            
        return f(*args, **kwargs)
    return decorated_function

def analyst_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or not session.get('user_role'):
            session.clear()
            flash("Session expired or invalid. Please log in again.", "error")
            return redirect(url_for('auth.login'))
            
        user_role = session.get('user_role', 'View-Only')
        if user_role not in ['Admin', 'Analyst']:
            flash('Access denied. You need Analyst or Admin access for this feature.', 'error')
            return redirect(url_for('dashboard'))
            
        return f(*args, **kwargs)
    return decorated_function
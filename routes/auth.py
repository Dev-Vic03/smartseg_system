from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature
from flask_mail import Mail, Message
import pyotp
import random
from datetime import datetime, timedelta
from database.models import db, User

auth_bp = Blueprint('auth', __name__)
mail = Mail()


def generate_reset_token(email):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps(email, salt='password-reset-salt')


def verify_reset_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = serializer.loads(token, salt='password-reset-salt', max_age=expiration)
    except (SignatureExpired, BadTimeSignature):
        return None
    return email

def generate_verification_code():
    return str(random.randint(100000, 999999))

def send_verification_email(email, code):
    try:
        msg = Message(
            subject="Verify your SmartSeg Account",
            recipients=[email],
            body=f"Hello,\n\nYour 6-digit verification code is: {code}\n\nThis code will expire in 10 minutes.\n\nIf you did not request this, please ignore this email."
        )
        mail.send(msg)
        return True
    except Exception as e:
        print(f"[MAIL ERROR] Failed to send verification email to {email}: {e}")
        return False

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            name = request.form.get('fullname')
            email = request.form.get('email')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            business_name = request.form.get('business_name', '')
            business_type = request.form.get('business_type', '')

            if not all([name, email, password, confirm_password]):
                flash('All required fields must be filled.', 'error')
                return render_template('register.html')

            if password != confirm_password:
                flash('Passwords do not match.', 'error')
                return render_template('register.html')

            # This might throw an error if the users table is completely missing
            if User.query.filter_by(email=email).first():
                flash('An account with this email already exists.', 'error')
                return render_template('register.html')

            new_user = User(
                name=name,
                email=email,
                password=generate_password_hash(password),
                business_name=business_name,
                business_type=business_type,
                role='Admin',  
                is_verified=True,  # Verification bypassed
                verification_code=None,
                verification_code_expires_at=None
            )
            db.session.add(new_user)
            db.session.commit()

            # Bypass email sending and instantly log the user in
            session.clear()
            session['user_id'] = new_user.id
            session['user_name'] = new_user.name
            session['user_role'] = new_user.role
            session['fresh_login'] = True

            flash('Account created successfully. Welcome to SmartSeg!', 'success')
            return redirect(url_for('dashboard'))

        except Exception as e:
            db.session.rollback()
            # If the database tables were manually dropped, recreate them instantly as a fallback
            if 'users' in str(e).lower() and ('doesn\'t exist' in str(e).lower() or 'not found' in str(e).lower()):
                db.create_all()
                flash("Database automatically repaired. Please submit the form again.", 'info')
            else:
                flash(f"Registration Error: {str(e)}", 'error')
            return render_template('register.html')
            
    return render_template('register.html')

@auth_bp.route('/verify-email', methods=['GET', 'POST'])
def verify_email():
    email = request.args.get('email') or request.form.get('email')
    
    if not email:
        return redirect(url_for('auth.login'))
        
    user = User.query.filter_by(email=email).first()
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('auth.register'))
        
    if user.is_verified:
        flash('Account already verified. Please log in.', 'info')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        code = request.form.get('code')
        
        if not code or len(code) != 6:
            flash('Please enter a valid 6-digit code.', 'error')
            return render_template('verify_email.html', email=email)
            
        if user.verification_code != code:
            flash('Invalid verification code.', 'error')
            return render_template('verify_email.html', email=email)
            
        if user.verification_code_expires_at and datetime.utcnow() > user.verification_code_expires_at:
            flash('Verification code has expired. Please request a new one.', 'error')
            return render_template('verify_email.html', email=email)
            
        # Success!
        user.is_verified = True
        user.verification_code = None
        user.verification_code_expires_at = None
        db.session.commit()
        
        flash('Email verified successfully! You can now log in.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('verify_email.html', email=email)

@auth_bp.route('/resend-verification')
def resend_verification():
    email = request.args.get('email')
    if not email:
        return redirect(url_for('auth.login'))
        
    user = User.query.filter_by(email=email).first()
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('auth.register'))
        
    if user.is_verified:
        flash('Account already verified. Please log in.', 'info')
        return redirect(url_for('auth.login'))
        
    # Generate new code
    code = generate_verification_code()
    user.verification_code = code
    user.verification_code_expires_at = datetime.utcnow() + timedelta(minutes=10)
    db.session.commit()
    
    email_sent = send_verification_email(user.email, code)
    if not email_sent:
        flash(f'⚠️ DEMO MODE: Email server unavailable. Your NEW verification code is: {code}', 'info')
    else:
        flash('A new verification code has been sent to your email.', 'success')
        
    return redirect(url_for('auth.verify_email', email=email))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            # If Multi-Factor Authentication is enabled on this account
            if user.mfa_enabled:
                session.clear()
                session['pending_user_id'] = user.id
                return redirect(url_for('auth.mfa_verify'))

            # Standard Direct Login Session Setup
            session.clear()
            session['user_id'] = user.id
            session['user_name'] = user.name
            session['user_role'] = user.role
            session['fresh_login'] = True
            return redirect(url_for('dashboard'))

        flash('Invalid email or password.', 'error')
        return render_template('login.html')

    return render_template('login.html')


@auth_bp.route('/mfa-verify', methods=['GET', 'POST'])
def mfa_verify():
    if 'pending_user_id' not in session:
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        otp_code = request.form.get('otp_code')
        user = User.query.get(session['pending_user_id'])

        if user and user.mfa_secret:
            totp = pyotp.TOTP(user.mfa_secret)
            if totp.verify(otp_code):
                session.pop('pending_user_id', None)
                session['user_id'] = user.id
                session['user_name'] = user.name
                session['user_role'] = user.role
                session['fresh_login'] = True
                flash('Authentication successful.', 'success')
                return redirect(url_for('dashboard'))

        flash('Invalid OTP authentication code.', 'error')

    return render_template('mfa_verify.html')


@auth_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        user = User.query.filter_by(email=email).first()

        # Always return success message for security (prevents user enumeration)
        if user:
            try:
                token = generate_reset_token(user.email)
                reset_url = url_for('auth.reset_password', token=token, _external=True)

                msg = Message(
                    subject="Reset Your SmartSeg Password",
                    recipients=[email],
                    body=f"Hello,\n\nClick the link below to reset your password:\n{reset_url}\n\nIf you did not request this, ignore this email."
                )
                mail.send(msg)
            except Exception as e:
                # Prints the exact SMTP error in your terminal terminal for debugging
                print(f"[MAIL ERROR] Failed to send reset email to {email}: {e}")
                flash("An error occurred while dispatching the email. Please try again later.", "error")
                return render_template('forgot_password.html')

        flash("If an account exists with that email, a password reset link has been sent.", "info")
        return redirect(url_for('auth.login'))

    return render_template('forgot_password.html')


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    email = verify_reset_token(token)
    if not email:
        flash('That is an invalid or expired token.', 'error')
        return redirect(url_for('auth.forgot_password'))

    user = User.query.filter_by(email=email).first_or_404()

    if request.method == 'POST':
        new_password = request.form.get('password')
        if not new_password or len(new_password) < 8:
            flash('Password must be at least 8 characters long.', 'error')
            return render_template('reset_password.html')

        user.password = generate_password_hash(new_password)
        db.session.commit()
        flash('Your password has been updated! You can now log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('reset_password.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))
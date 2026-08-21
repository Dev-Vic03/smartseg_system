from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature
from flask_mail import Mail, Message
import pyotp
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


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('fullname')
        email = request.form.get('email')
        password = request.form.get('password')
        business_name = request.form.get('business_name')
        business_type = request.form.get('business_type')

        if not all([name, email, password]):
            flash('All required fields must be filled.', 'error')
            return render_template('register.html')

        if User.query.filter_by(email=email).first():
            flash('An account with this email already exists.', 'error')
            return render_template('register.html')

        new_user = User(
            name=name,
            email=email,
            password=generate_password_hash(password),
            business_name=business_name,
            business_type=business_type,
            role='Admin'  # Default role for initial registrant
        )
        db.session.add(new_user)
        db.session.commit()

        flash('Account created successfully. Please log in.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('register.html')


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
                    recipients=[email],  # Dynamic recipient
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
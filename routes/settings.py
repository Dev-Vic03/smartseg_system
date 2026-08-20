import secrets
from flask import Blueprint, render_template, request, jsonify, session
from database.models import db, WorkspaceSetting
from utils.decorators import login_required

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/settings')
@login_required
def index():
    user_id = session['user_id']
    setting = WorkspaceSetting.query.filter_by(user_id=user_id).first()
    if not setting:
        setting = WorkspaceSetting(user_id=user_id, api_key=secrets.token_hex(16))
        db.session.add(setting)
        db.session.commit()
    return render_template('settings.html', setting=setting)

@settings_bp.route('/api/settings/generate-key', methods=['POST'])
@login_required
def generate_key():
    user_id = session['user_id']
    setting = WorkspaceSetting.query.filter_by(user_id=user_id).first()
    setting.api_key = secrets.token_hex(16)
    db.session.commit()
    return jsonify({'api_key': setting.api_key})
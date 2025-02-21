from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from functools import wraps
from .user_management import UserManager
from .api_security import APIKeyManager

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
user_manager = None
api_key_manager = None

def init_admin_routes(app, session_factory):
    """Initialize admin routes with the app and session factory"""
    global user_manager, api_key_manager
    user_manager = UserManager(session_factory)
    api_key_manager = APIKeyManager(app)
    app.register_blueprint(admin_bp)

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.can_manage_users:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """Admin dashboard view"""
    return render_template('admin/dashboard.html')

@admin_bp.route('/users')
@admin_required
def users():
    """User management view"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    users = user_manager.list_users(page=page, per_page=per_page)
    return render_template('admin/users.html', users=users)

@admin_bp.route('/api-keys')
@admin_required
def api_keys():
    """API key management view"""
    return render_template('admin/api_keys.html')

@admin_bp.route('/audit')
@admin_required
def audit_log():
    """Audit log view"""
    return render_template('admin/audit_log.html') 
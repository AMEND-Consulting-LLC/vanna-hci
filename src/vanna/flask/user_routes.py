from flask import Blueprint, jsonify, request, abort, g
from functools import wraps
from .user_management import UserManager
from typing import Optional

user_bp = Blueprint('user_management', __name__)
user_manager: Optional[UserManager] = None

def init_user_routes(app, session_factory):
    """Initialize user routes with the app and session factory"""
    global user_manager
    user_manager = UserManager(session_factory)
    app.register_blueprint(user_bp, url_prefix='/api/users')

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not g.get('user'):
            abort(401, description="Authentication required")
        return f(*args, **kwargs)
    return decorated

def require_admin(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not g.get('user') or not g.user.can_manage_users:
            abort(403, description="Admin access required")
        return f(*args, **kwargs)
    return decorated

@user_bp.before_request
def load_user():
    """Load user into request context"""
    g.user = None
    if 'user' in request.headers:
        user_id = request.headers.get('user')
        g.user = user_manager.get_user_by_id(user_id)

# User Management Endpoints

@user_bp.route('/', methods=['GET'])
@require_admin
def list_users():
    """List all users with pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    users = user_manager.list_users(page=page, per_page=per_page)
    return jsonify([{
        'id': user.id,
        'email': user.email,
        'name': user.name,
        'role': user.role,
        'is_active': user.is_active,
        'created_at': user.created_at.isoformat(),
        'last_login': user.last_login.isoformat() if user.last_login else None
    } for user in users])

@user_bp.route('/<int:user_id>', methods=['GET'])
@require_auth
def get_user(user_id):
    """Get user details"""
    # Users can only view their own details unless they're admin
    if user_id != g.user.id and not g.user.can_manage_users:
        abort(403)
    
    user = user_manager.get_user_by_id(user_id)
    if not user:
        abort(404)
    
    return jsonify({
        'id': user.id,
        'email': user.email,
        'name': user.name,
        'role': user.role,
        'is_active': user.is_active,
        'created_at': user.created_at.isoformat(),
        'last_login': user.last_login.isoformat() if user.last_login else None,
        'permissions': {
            'can_create_api_keys': user.can_create_api_keys,
            'can_view_audit_logs': user.can_view_audit_logs,
            'can_manage_users': user.can_manage_users,
            'api_rate_limit': user.api_rate_limit
        }
    })

@user_bp.route('/<int:user_id>/role', methods=['PUT'])
@require_admin
def update_role(user_id):
    """Update user role"""
    data = request.get_json()
    new_role = data.get('role')
    
    if not new_role or new_role not in ['admin', 'power_user', 'user']:
        abort(400, description="Invalid role specified")
    
    if user_manager.update_user_role(user_id, new_role):
        return jsonify({'message': 'Role updated successfully'})
    abort(404)

@user_bp.route('/<int:user_id>/status', methods=['PUT'])
@require_admin
def update_status(user_id):
    """Activate or deactivate user"""
    data = request.get_json()
    is_active = data.get('is_active')
    
    if is_active is None:
        abort(400, description="is_active status required")
    
    if is_active:
        # Reactivate user
        user = user_manager.get_user_by_id(user_id)
        if user:
            user.is_active = True
            return jsonify({'message': 'User activated successfully'})
    else:
        # Deactivate user
        if user_manager.deactivate_user(user_id):
            return jsonify({'message': 'User deactivated successfully'})
    
    abort(404)

@user_bp.route('/<int:user_id>/api-keys', methods=['GET'])
@require_auth
def list_user_api_keys(user_id):
    """List user's API keys"""
    # Users can only view their own API keys unless they're admin
    if user_id != g.user.id and not g.user.can_manage_users:
        abort(403)
    
    keys = user_manager.get_user_api_keys(user_id)
    return jsonify([{
        'key': key.key,
        'role': key.role,
        'description': key.description,
        'created_at': key.created_at.isoformat(),
        'last_used': key.last_used.isoformat() if key.last_used else None,
        'expires_at': key.expires_at.isoformat() if key.expires_at else None,
        'is_active': key.is_active
    } for key in keys])

# Current User Endpoints

@user_bp.route('/me', methods=['GET'])
@require_auth
def get_current_user():
    """Get current user details"""
    return get_user(g.user.id)

@user_bp.route('/me/api-keys', methods=['GET'])
@require_auth
def get_current_user_api_keys():
    """Get current user's API keys"""
    return list_user_api_keys(g.user.id) 
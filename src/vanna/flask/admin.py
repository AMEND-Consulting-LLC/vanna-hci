from datetime import datetime, timedelta
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from .models import User, APIKey, db
from .security import require_role

admin = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    """Decorator to require admin role for routes"""
    @wraps(f)
    @login_required
    @require_role(['admin'])
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function

@admin.route('/')
@admin_required
def dashboard():
    """Admin dashboard showing key metrics and recent activity"""
    stats = {
        'total_users': User.query.count(),
        'active_users': User.query.filter_by(is_active=True).count(),
        'active_keys': APIKey.query.filter(APIKey.expires_at > datetime.utcnow()).count(),
        'expiring_soon': APIKey.query.filter(
            APIKey.expires_at.between(
                datetime.utcnow(),
                datetime.utcnow() + timedelta(days=7)
            )
        ).count(),
        'api_requests_24h': 0,  # TODO: Implement API request tracking
        'request_change': 0  # TODO: Calculate change percentage
    }

    recent_activity = []
    # Get recent user registrations
    recent_users = User.query.order_by(User.created_at.desc()).limit(5)
    for user in recent_users:
        recent_activity.append({
            'type': 'user',
            'description': f'New user registered: {user.name}',
            'user': user.email,
            'timestamp': user.created_at
        })

    # Get recent API key creations
    recent_keys = APIKey.query.order_by(APIKey.created_at.desc()).limit(5)
    for key in recent_keys:
        recent_activity.append({
            'type': 'api_key',
            'description': f'API key created for {key.user.name}',
            'user': key.user.email,
            'timestamp': key.created_at
        })

    # Sort combined activity by timestamp
    recent_activity.sort(key=lambda x: x['timestamp'], reverse=True)
    recent_activity = recent_activity[:10]  # Keep only 10 most recent items

    return render_template('admin/dashboard.html', stats=stats, recent_activity=recent_activity)

@admin.route('/users')
@admin_required
def users():
    """User management page"""
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@admin.route('/users/<int:user_id>/role', methods=['POST'])
@admin_required
def update_user_role(user_id):
    """Update a user's role"""
    user = User.query.get_or_404(user_id)
    new_role = request.form.get('role')
    
    if new_role not in ['user', 'admin']:
        flash('Invalid role specified', 'error')
        return redirect(url_for('admin.users'))
    
    # Prevent removing the last admin
    if user.role == 'admin' and new_role != 'admin':
        admin_count = User.query.filter_by(role='admin').count()
        if admin_count <= 1:
            flash('Cannot remove the last admin user', 'error')
            return redirect(url_for('admin.users'))
    
    user.role = new_role
    db.session.commit()
    flash(f'Role updated for {user.email}', 'success')
    return redirect(url_for('admin.users'))

@admin.route('/users/<int:user_id>/status', methods=['POST'])
@admin_required
def toggle_user_status(user_id):
    """Toggle a user's active status"""
    user = User.query.get_or_404(user_id)
    
    # Prevent deactivating the last admin
    if user.role == 'admin' and user.is_active:
        active_admins = User.query.filter_by(role='admin', is_active=True).count()
        if active_admins <= 1:
            flash('Cannot deactivate the last active admin', 'error')
            return redirect(url_for('admin.users'))
    
    user.is_active = not user.is_active
    db.session.commit()
    status = 'activated' if user.is_active else 'deactivated'
    flash(f'User {user.email} has been {status}', 'success')
    return redirect(url_for('admin.users'))

@admin.route('/api-keys')
@admin_required
def api_keys():
    """API key management page"""
    api_keys = APIKey.query.all()
    users = User.query.all()
    return render_template('admin/api_keys.html', api_keys=api_keys, users=users)

@admin.route('/api-keys', methods=['POST'])
@admin_required
def create_api_key():
    """Create a new API key"""
    user_id = request.form.get('user_id')
    description = request.form.get('description', '')
    expiration_days = int(request.form.get('expiration_days', 30))
    role = request.form.get('role', 'user')

    user = User.query.get_or_404(user_id)
    expires_at = datetime.utcnow() + timedelta(days=expiration_days)

    api_key = APIKey(
        user_id=user.id,
        description=description,
        expires_at=expires_at,
        role=role
    )
    db.session.add(api_key)
    db.session.commit()

    flash(f'API key created for {user.email}', 'success')
    return redirect(url_for('admin.api_keys'))

@admin.route('/api-keys/<int:key_id>/revoke', methods=['POST'])
@admin_required
def revoke_api_key(key_id):
    """Revoke an API key"""
    api_key = APIKey.query.get_or_404(key_id)
    api_key.revoked = True
    db.session.commit()
    flash(f'API key for {api_key.user.email} has been revoked', 'success')
    return redirect(url_for('admin.api_keys'))

@admin.route('/api-keys/<int:key_id>/extend', methods=['POST'])
@admin_required
def extend_api_key(key_id):
    """Extend an API key's expiration"""
    api_key = APIKey.query.get_or_404(key_id)
    days = int(request.form.get('days', 30))
    
    if api_key.revoked:
        flash('Cannot extend a revoked API key', 'error')
    else:
        api_key.expires_at = datetime.utcnow() + timedelta(days=days)
        db.session.commit()
        flash(f'API key expiration extended by {days} days', 'success')
    
    return redirect(url_for('admin.api_keys')) 
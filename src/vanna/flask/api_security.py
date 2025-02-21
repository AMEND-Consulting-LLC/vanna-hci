import hmac
import hashlib
import time
from functools import wraps
from typing import Dict, List, Optional, Any, Callable
from flask import Flask, request, abort, current_app, g, jsonify
import re
from datetime import datetime, timedelta
import secrets
import json
import bleach
from .db_models import APIKey, KeyAuditLog, init_db

class APISecurityMiddleware:
    def __init__(
        self,
        app: Flask,
        signing_secret: str = None,
        max_request_age: int = 300,  # 5 minutes
        input_validation_rules: Dict[str, Dict] = None,
        sanitize_output: bool = True
    ):
        """
        Initialize API security middleware.
        
        Args:
            app: Flask application instance
            signing_secret: Secret for request signing
            max_request_age: Maximum age of requests in seconds
            input_validation_rules: Dictionary of endpoint validation rules
            sanitize_output: Whether to sanitize JSON output
        """
        self.app = app
        self.signing_secret = signing_secret or secrets.token_hex(32)
        self.max_request_age = max_request_age
        self.input_validation_rules = input_validation_rules or {}
        self.sanitize_output = sanitize_output
        
        # Initialize database
        self.Session = init_db(app.config)
        
        # API key rate limiting
        self.request_history: Dict[str, List[float]] = {}
        
        # Configure middleware
        self._configure_middleware()
    
    def _configure_middleware(self):
        """Configure API security middleware"""
        # API key authentication
        self.app.before_request(self._authenticate_api_key)
        
        # Request signature verification
        self.app.before_request(self._verify_signature)
        
        # Input validation
        self.app.before_request(self._validate_input)
        
        # Output sanitization
        if self.sanitize_output:
            self.app.after_request(self._sanitize_output)
    
    def _authenticate_api_key(self):
        """Authenticate API key"""
        if request.path.startswith('/api/'):
            api_key = request.headers.get('X-API-Key')
            if not api_key:
                abort(401, description="API key required")
            
            # Get API key from database
            session = self.Session()
            try:
                key_record = session.query(APIKey).filter_by(
                    key=api_key,
                    is_active=True
                ).first()
                
                if not key_record:
                    abort(401, description="Invalid API key")
                
                # Check expiration
                if key_record.expires_at and key_record.expires_at < datetime.utcnow():
                    abort(401, description="API key expired")
                
                # Store API key role in request context
                g.api_role = key_record.role
                g.api_key_id = key_record.id
                
                # Update last used timestamp
                key_record.last_used = datetime.utcnow()
                
                # Log key usage
                audit_log = KeyAuditLog(
                    api_key_id=key_record.id,
                    event_type='used',
                    details=f"Accessed {request.path}",
                    ip_address=request.remote_addr
                )
                session.add(audit_log)
                session.commit()
                
                # Rate limiting per API key
                now = time.time()
                if api_key in self.request_history:
                    # Clean old requests
                    self.request_history[api_key] = [
                        t for t in self.request_history[api_key]
                        if now - t < 60
                    ]
                    # Check rate limit (different limits based on role)
                    max_requests = 1000 if g.api_role == 'admin' else 100
                    if len(self.request_history[api_key]) >= max_requests:
                        abort(429, description="Rate limit exceeded")
                else:
                    self.request_history[api_key] = []
                
                self.request_history[api_key].append(now)
                
            finally:
                session.close()
    
    def _verify_signature(self):
        """Verify request signature"""
        if request.path.startswith('/api/'):
            timestamp = request.headers.get('X-Request-Timestamp')
            signature = request.headers.get('X-Request-Signature')
            
            if not timestamp or not signature:
                abort(401, description="Request signature required")
            
            # Check request age
            try:
                request_time = int(timestamp)
                if abs(time.time() - request_time) > self.max_request_age:
                    abort(401, description="Request expired")
            except ValueError:
                abort(401, description="Invalid timestamp")
            
            # Verify signature
            expected_signature = self._generate_signature(
                timestamp,
                request.method,
                request.path,
                request.get_data()
            )
            
            if not hmac.compare_digest(signature, expected_signature):
                abort(401, description="Invalid signature")
    
    def _generate_signature(
        self,
        timestamp: str,
        method: str,
        path: str,
        body: bytes
    ) -> str:
        """Generate request signature"""
        message = f"{timestamp}{method}{path}"
        if body:
            message += body.decode('utf-8')
        
        return hmac.new(
            self.signing_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def _validate_input(self):
        """Validate request input"""
        if request.path.startswith('/api/'):
            rules = self.input_validation_rules.get(request.path)
            if rules:
                data = request.get_json() if request.is_json else {}
                
                for field, rule in rules.items():
                    value = data.get(field)
                    
                    # Required field check
                    if rule.get('required', False) and value is None:
                        abort(400, description=f"Missing required field: {field}")
                    
                    if value is not None:
                        # Type check
                        expected_type = rule.get('type')
                        if expected_type and not isinstance(value, expected_type):
                            abort(400, description=f"Invalid type for field: {field}")
                        
                        # Pattern check
                        pattern = rule.get('pattern')
                        if pattern and not re.match(pattern, str(value)):
                            abort(400, description=f"Invalid format for field: {field}")
                        
                        # Range check
                        min_val = rule.get('min')
                        max_val = rule.get('max')
                        if min_val is not None and value < min_val:
                            abort(400, description=f"Value too small for field: {field}")
                        if max_val is not None and value > max_val:
                            abort(400, description=f"Value too large for field: {field}")
    
    def _sanitize_output(self, response):
        """Sanitize response output"""
        if response.mimetype == 'application/json':
            try:
                data = json.loads(response.get_data())
                sanitized = self._recursively_sanitize(data)
                response.set_data(json.dumps(sanitized))
            except Exception:
                pass
        return response
    
    def _recursively_sanitize(self, data: Any) -> Any:
        """Recursively sanitize data structure"""
        if isinstance(data, str):
            return bleach.clean(data)
        elif isinstance(data, dict):
            return {k: self._recursively_sanitize(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._recursively_sanitize(item) for item in data]
        return data

def require_api_role(role: str):
    """Decorator to require specific API role"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'api_role'):
                abort(401, description="API key required")
            if g.api_role != role and g.api_role != 'admin':
                abort(403, description="Insufficient permissions")
            return f(*args, **kwargs)
        return decorated_function
    return decorator

class APIKeyManager:
    def __init__(self, app: Flask):
        """
        Initialize API key manager.
        
        Args:
            app: Flask application instance
        """
        self.app = app
        self.Session = init_db(app.config)
        
        # Add API key management endpoints
        self._add_management_endpoints()
    
    def _add_management_endpoints(self):
        """Add API key management endpoints"""
        @self.app.route('/api/keys', methods=['POST'])
        @require_api_role('admin')
        def create_api_key():
            data = request.get_json()
            role = data.get('role', 'user')
            description = data.get('description', '')
            expires_in_days = data.get('expires_in_days')
            
            if role not in ['admin', 'user']:
                abort(400, description="Invalid role")
            
            session = self.Session()
            try:
                api_key = secrets.token_hex(32)
                expires_at = None
                if expires_in_days:
                    expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
                
                key_record = APIKey(
                    key=api_key,
                    role=role,
                    description=description,
                    expires_at=expires_at,
                    created_by=g.get('user_id', 'unknown')  # From Azure SSO
                )
                session.add(key_record)
                
                # Log key creation
                audit_log = KeyAuditLog(
                    api_key_id=key_record.id,
                    event_type='created',
                    details=f"Created {role} key with description: {description}",
                    ip_address=request.remote_addr
                )
                session.add(audit_log)
                session.commit()
                
                return jsonify({
                    'api_key': api_key,
                    'role': role,
                    'expires_at': expires_at.isoformat() if expires_at else None
                })
            finally:
                session.close()
        
        @self.app.route('/api/keys/<api_key>', methods=['DELETE'])
        @require_api_role('admin')
        def revoke_api_key(api_key):
            session = self.Session()
            try:
                key_record = session.query(APIKey).filter_by(key=api_key).first()
                if key_record:
                    key_record.is_active = False
                    
                    # Log key revocation
                    audit_log = KeyAuditLog(
                        api_key_id=key_record.id,
                        event_type='revoked',
                        details="Key revoked by admin",
                        ip_address=request.remote_addr
                    )
                    session.add(audit_log)
                    session.commit()
                
                return '', 204
            finally:
                session.close()
        
        @self.app.route('/api/keys', methods=['GET'])
        @require_api_role('admin')
        def list_api_keys():
            session = self.Session()
            try:
                keys = session.query(APIKey).all()
                return jsonify([{
                    'id': key.id,
                    'key': key.key,
                    'role': key.role,
                    'description': key.description,
                    'created_at': key.created_at.isoformat(),
                    'last_used': key.last_used.isoformat() if key.last_used else None,
                    'expires_at': key.expires_at.isoformat() if key.expires_at else None,
                    'is_active': key.is_active,
                    'created_by': key.created_by
                } for key in keys])
            finally:
                session.close()
        
        @self.app.route('/api/keys/audit', methods=['GET'])
        @require_api_role('admin')
        def get_audit_log():
            session = self.Session()
            try:
                logs = session.query(KeyAuditLog).order_by(KeyAuditLog.timestamp.desc()).limit(100)
                return jsonify([{
                    'id': log.id,
                    'api_key_id': log.api_key_id,
                    'event_type': log.event_type,
                    'timestamp': log.timestamp.isoformat(),
                    'details': log.details,
                    'ip_address': log.ip_address
                } for log in logs])
            finally:
                session.close() 
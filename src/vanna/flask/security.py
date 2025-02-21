from functools import wraps
from flask import Flask, request, abort, current_app
import time
from typing import List, Optional, Dict, Callable
from werkzeug.middleware.proxy_fix import ProxyFix
import ssl
import secrets

class SecurityMiddleware:
    def __init__(
        self,
        app: Flask,
        cors_origins: List[str] = None,
        rate_limit: int = 100,  # requests per minute
        force_https: bool = True,
        trusted_proxies: int = 1,
        content_security_policy: bool = True
    ):
        """
        Initialize security middleware.
        
        Args:
            app: Flask application instance
            cors_origins: List of allowed CORS origins
            rate_limit: Maximum number of requests per minute per IP
            force_https: Whether to force HTTPS
            trusted_proxies: Number of trusted proxies
            content_security_policy: Whether to enable CSP
        """
        self.app = app
        self.cors_origins = cors_origins or []
        self.rate_limit = rate_limit
        self.force_https = force_https
        self.request_history: Dict[str, List[float]] = {}
        
        # Configure app
        self._configure_app()
        
        # Add security headers
        self.app.after_request(self._add_security_headers)
        
        # Setup CORS
        self.app.before_request(self._handle_cors)
        
        # Rate limiting
        self.app.before_request(self._check_rate_limit)
        
        # Force HTTPS
        if force_https:
            self.app.before_request(self._force_https)
        
        # Trust proxy headers (important for HTTPS detection behind reverse proxy)
        self.app.wsgi_app = ProxyFix(
            self.app.wsgi_app, x_for=trusted_proxies, x_proto=trusted_proxies
        )

    def _configure_app(self):
        """Configure Flask app security settings"""
        # Generate strong secret key if not set
        if not self.app.secret_key:
            self.app.secret_key = secrets.token_hex(32)
        
        # Session configuration
        self.app.config.update(
            SESSION_COOKIE_SECURE=True,
            SESSION_COOKIE_HTTPONLY=True,
            SESSION_COOKIE_SAMESITE='Lax',
            PERMANENT_SESSION_LIFETIME=1800,  # 30 minutes
            
            # General security
            PREFERRED_URL_SCHEME='https',
            
            # Content Security Policy
            CSP={
                'default-src': ["'self'"],
                'script-src': ["'self'", "'unsafe-inline'"],  # Adjust based on needs
                'style-src': ["'self'", "'unsafe-inline'"],
                'img-src': ["'self'", 'data:', 'https:'],
                'connect-src': ["'self'"] + self.cors_origins
            }
        )

    def _add_security_headers(self, response):
        """Add security headers to response"""
        # HSTS: Force HTTPS for 1 year
        if self.force_https:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        # Prevent clickjacking
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        
        # XSS protection
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Content type options
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        # Referrer policy
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Content Security Policy
        if current_app.config.get('CSP'):
            csp = '; '.join(
                f"{key} {' '.join(values)}"
                for key, values in current_app.config['CSP'].items()
            )
            response.headers['Content-Security-Policy'] = csp
        
        return response

    def _handle_cors(self):
        """Handle CORS requests"""
        if not self.cors_origins:
            return
        
        origin = request.headers.get('Origin')
        if origin and origin in self.cors_origins:
            current_app.config['CORS_HEADERS'] = {
                'Access-Control-Allow-Origin': origin,
                'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                'Access-Control-Allow-Credentials': 'true'
            }
            
            if request.method == 'OPTIONS':
                response = current_app.make_default_options_response()
                for key, value in current_app.config['CORS_HEADERS'].items():
                    response.headers[key] = value
                return response

    def _check_rate_limit(self):
        """Check rate limiting"""
        if request.method == 'OPTIONS':
            return
            
        ip = request.remote_addr
        now = time.time()
        
        # Clean old requests
        if ip in self.request_history:
            self.request_history[ip] = [
                t for t in self.request_history[ip]
                if now - t < 60  # Keep last minute
            ]
        else:
            self.request_history[ip] = []
        
        # Check rate limit
        if len(self.request_history[ip]) >= self.rate_limit:
            abort(429)  # Too Many Requests
        
        self.request_history[ip].append(now)

    def _force_https(self):
        """Force HTTPS for all requests"""
        if not request.is_secure:
            url = request.url.replace('http://', 'https://', 1)
            return redirect(url, code=301)

def configure_ssl_context(
    cert_path: str,
    key_path: str,
    password: Optional[str] = None
) -> ssl.SSLContext:
    """
    Configure SSL context for Flask application.
    
    Args:
        cert_path: Path to SSL certificate
        key_path: Path to private key
        password: Optional password for private key
        
    Returns:
        Configured SSL context
    """
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(
        certfile=cert_path,
        keyfile=key_path,
        password=password
    )
    
    # Modern security settings
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.set_ciphers('ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256')
    context.options |= (
        ssl.OP_NO_TLSv1 |
        ssl.OP_NO_TLSv1_1 |
        ssl.OP_CIPHER_SERVER_PREFERENCE
    )
    
    return context 
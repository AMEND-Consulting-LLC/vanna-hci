from abc import ABC, abstractmethod
import os
from typing import Any, Dict
import msal
import flask
from flask import redirect, url_for, session, request, abort
import requests
from .auth import AuthInterface
from .user_management import UserManager
from .db_models import init_db

class AzureAuth(AuthInterface):
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Azure SSO authentication.
        
        Args:
            config: Dictionary containing Azure configuration:
                - client_id: Azure application client ID
                - client_secret: Azure application client secret
                - tenant_id: Azure tenant ID
                - redirect_uri: OAuth redirect URI
                - scopes: List of required scopes
        """
        self.client_id = config.get('client_id') or os.getenv('AZURE_CLIENT_ID')
        self.client_secret = config.get('client_secret') or os.getenv('AZURE_CLIENT_SECRET')
        self.tenant_id = config.get('tenant_id') or os.getenv('AZURE_TENANT_ID')
        self.redirect_uri = config.get('redirect_uri')
        self.scopes = config.get('scopes', ['User.Read'])
        
        if not all([self.client_id, self.client_secret, self.tenant_id, self.redirect_uri]):
            raise ValueError("Missing required Azure configuration parameters")
        
        # Initialize MSAL application
        self.msal_app = msal.ConfidentialClientApplication(
            client_id=self.client_id,
            client_credential=self.client_secret,
            authority=f"https://login.microsoftonline.com/{self.tenant_id}"
        )
        
        # Initialize user manager
        self.user_manager = None
    
    def init_app(self, app):
        """Initialize with Flask app to set up user management"""
        Session = init_db(app.config)
        self.user_manager = UserManager(Session)

    def get_user(self, flask_request) -> Any:
        """Get user information from session"""
        if 'user' not in session:
            return None
            
        # Get user from database if we have their Azure ID
        if self.user_manager and 'id' in session['user']:
            return self.user_manager.get_user_by_azure_id(session['user']['id'])
            
        return session['user']

    def is_logged_in(self, user: Any) -> bool:
        """Check if user is logged in and active"""
        return user is not None and (
            not hasattr(user, 'is_active') or user.is_active
        )

    def override_config_for_user(self, user: Any, config: dict) -> dict:
        """Override configuration based on user roles/permissions"""
        if not user:
            return config
        
        user_config = config.copy()
        
        # Add user's role and permissions
        if hasattr(user, 'role'):
            user_config['user_role'] = user.role
            user_config['can_create_api_keys'] = user.can_create_api_keys
            user_config['can_view_audit_logs'] = user.can_view_audit_logs
            user_config['can_manage_users'] = user.can_manage_users
            user_config['api_rate_limit'] = user.api_rate_limit
        
        return user_config

    def login_form(self) -> str:
        """Return login button HTML"""
        return '''
            <div style="text-align: center; padding: 20px;">
                <a href="/auth/login" style="
                    display: inline-block;
                    background-color: #0078d4;
                    color: white;
                    padding: 10px 20px;
                    text-decoration: none;
                    border-radius: 4px;
                    font-family: 'Segoe UI', sans-serif;">
                    Sign in with Microsoft
                </a>
            </div>
        '''

    def login_handler(self, flask_request) -> str:
        """Handle login request"""
        # Generate auth URL and redirect to Microsoft login
        auth_url = self.msal_app.get_authorization_request_url(
            scopes=self.scopes,
            redirect_uri=self.redirect_uri,
            state=flask.session.get("state", ""),
        )
        return redirect(auth_url)

    def callback_handler(self, flask_request) -> str:
        """Handle OAuth callback from Microsoft"""
        # Get token from auth code
        token_response = self.msal_app.acquire_token_by_authorization_code(
            code=flask_request.args.get('code'),
            scopes=self.scopes,
            redirect_uri=self.redirect_uri
        )
        
        if "error" in token_response:
            return f"Error: {token_response.get('error_description', 'Unknown error')}"
        
        if "access_token" not in token_response:
            return "Error: No access token received"
            
        # Get user info using the access token
        user_info = self._get_user_info(token_response['access_token'])
        
        if user_info:
            if self.user_manager:
                # Create or update user in database
                user = self.user_manager.get_or_create_user(user_info)
                if not user.is_active:
                    return "Error: Your account has been deactivated"
                
                # Store minimal user info in session
                session['user'] = {
                    'id': user.azure_id,
                    'email': user.email,
                    'name': user.name,
                    'role': user.role
                }
            else:
                # Fallback to session-only storage if no user manager
                session['user'] = {
                    'id': user_info.get('id'),
                    'email': user_info.get('mail') or user_info.get('userPrincipalName'),
                    'name': user_info.get('displayName'),
                    'roles': user_info.get('roles', [])
                }
            return redirect('/')
        
        return "Error: Could not get user information"

    def logout_handler(self, flask_request) -> str:
        """Handle logout request"""
        # Clear session
        session.clear()
        
        # Redirect to Azure logout
        return redirect(
            f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/logout"
            f"?post_logout_redirect_uri={self.redirect_uri}"
        )

    def _get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from Microsoft Graph API"""
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(
            'https://graph.microsoft.com/v1.0/me',
            headers=headers
        )
        
        if response.status_code == 200:
            return response.json()
        return None 
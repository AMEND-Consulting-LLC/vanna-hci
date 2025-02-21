from vanna.chromadb.chromadb_vector import ChromaDB_VectorStore
from vanna.openai.openai_chat import OpenAI_Chat
from vanna.flask import VannaFlaskApp
from vanna.flask.azure_auth import AzureAuth
from vanna.flask.security import SecurityMiddleware, configure_ssl_context
from vanna.flask.letsencrypt import setup_letsencrypt
from vanna.flask.api_security import APISecurityMiddleware, APIKeyManager
from vanna.flask.user_routes import init_user_routes
from vanna.flask.db_models import init_db
import os
from openai import AzureOpenAI
from flask_session import Session
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, current_user
from vanna.flask.models import db, User
from vanna.flask.auth import auth as auth_blueprint
from vanna.flask.admin import admin as admin_blueprint
from vanna.flask.security import SecurityMiddleware
from vanna.flask.letsencrypt import setup_letsencrypt
from vanna.flask.security import SecurityMiddleware
from vanna.flask.letsencrypt import setup_letsencrypt
from dotenv import load_dotenv
from vanna.flask.admin_routes import init_admin_routes

# Load environment variables
load_dotenv()

# Initialize ChromaDB with persistent storage
config = {
    "path": "./data",  # Store data in the data directory
    "client": "persistent",  # Use persistent storage
    # Azure OpenAI Configuration
    "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
    "azure_api_key": os.getenv("AZURE_OPENAI_API_KEY"),
    "azure_deployment": os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4"),
    "azure_api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
}

# Azure SSO Configuration
azure_auth_config = {
    "client_id": os.getenv("AZURE_CLIENT_ID"),
    "client_secret": os.getenv("AZURE_CLIENT_SECRET"),
    "tenant_id": os.getenv("AZURE_TENANT_ID"),
    "redirect_uri": os.getenv("AZURE_REDIRECT_URI", "http://localhost:8000/auth/callback"),
    "scopes": ["User.Read"]  # Add more scopes as needed
}

# Security Configuration
security_config = {
    "cors_origins": os.getenv("CORS_ORIGINS", "").split(","),
    "rate_limit": int(os.getenv("RATE_LIMIT", "100")),
    "force_https": os.getenv("FORCE_HTTPS", "true").lower() == "true",
    "trusted_proxies": int(os.getenv("TRUSTED_PROXIES", "1")),
    "ssl_cert": os.getenv("SSL_CERT_PATH"),
    "ssl_key": os.getenv("SSL_KEY_PATH"),
    "ssl_password": os.getenv("SSL_KEY_PASSWORD")
}

# Let's Encrypt Configuration
letsencrypt_config = {
    "enabled": os.getenv("USE_LETSENCRYPT", "false").lower() == "true",
    "domains": os.getenv("LETSENCRYPT_DOMAINS", "").split(","),
    "email": os.getenv("LETSENCRYPT_EMAIL"),
    "staging": os.getenv("LETSENCRYPT_STAGING", "false").lower() == "true"
}

# API Security Configuration
api_security_config = {
    "signing_secret": os.getenv("API_SIGNING_SECRET"),
    "max_request_age": int(os.getenv("API_MAX_REQUEST_AGE", "300")),
    "input_validation_rules": {
        "/api/query": {
            "query": {"required": True, "type": str, "min_length": 1},
            "context": {"type": dict},
            "max_results": {"type": int, "min": 1, "max": 100}
        }
    },
    "sanitize_output": True
}

# Create a class that combines ChromaDB for vector storage and OpenAI for chat
class VannaAzure(ChromaDB_VectorStore, OpenAI_Chat):
    def __init__(self, config=None):
        ChromaDB_VectorStore.__init__(self, config=config)
        
        # Initialize Azure OpenAI client
        client = AzureOpenAI(
            azure_endpoint=config["azure_endpoint"],
            api_key=config["azure_api_key"],
            api_version=config["azure_api_version"]
        )
        
        # Pass the Azure client to OpenAI_Chat
        OpenAI_Chat.__init__(self, client=client, config={"model": config["azure_deployment"]})

# Initialize the vector store with Azure OpenAI
vector_store = VannaAzure(config)

# Create the Flask app with our vector store and Azure authentication
auth = AzureAuth(azure_auth_config)
app = VannaFlaskApp(
    vn=vector_store,
    auth=auth,
    debug=True,
    allow_llm_to_see_data=True,  # Since we're using local storage
    title="Vanna.AI with Azure SSO",
    subtitle="Your AI-powered SQL assistant with Azure Authentication"
)

# Configure Flask session
app.flask_app.config['SESSION_TYPE'] = 'filesystem'
Session(app.flask_app)

# Initialize database
Session = init_db(app.flask_app.config)

# Initialize Azure auth with app
auth.init_app(app.flask_app)

# Initialize security middleware
SecurityMiddleware(
    app.flask_app,
    cors_origins=security_config["cors_origins"],
    rate_limit=security_config["rate_limit"],
    force_https=security_config["force_https"],
    trusted_proxies=security_config["trusted_proxies"]
)

# Initialize API security middleware
api_security = APISecurityMiddleware(
    app.flask_app,
    signing_secret=api_security_config["signing_secret"],
    max_request_age=api_security_config["max_request_age"],
    input_validation_rules=api_security_config["input_validation_rules"],
    sanitize_output=api_security_config["sanitize_output"]
)

# Initialize API key manager
api_key_manager = APIKeyManager(app.flask_app)

# Initialize user management routes
init_user_routes(app.flask_app, Session)

# Initialize admin routes
init_admin_routes(app.flask_app, Session)

def create_app():
    app = Flask(__name__)
    
    # Configure app
    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-key-change-this')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///app.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Security configuration
    security_config = {
        'CORS_ENABLED': os.getenv('CORS_ENABLED', 'false').lower() == 'true',
        'CORS_ORIGINS': os.getenv('CORS_ORIGINS', '*').split(','),
        'RATE_LIMIT_ENABLED': os.getenv('RATE_LIMIT_ENABLED', 'true').lower() == 'true',
        'RATE_LIMIT': int(os.getenv('RATE_LIMIT', '100')),
        'RATE_LIMIT_PERIOD': int(os.getenv('RATE_LIMIT_PERIOD', '3600')),
        'FORCE_HTTPS': os.getenv('FORCE_HTTPS', 'false').lower() == 'true',
        'HSTS_ENABLED': os.getenv('HSTS_ENABLED', 'false').lower() == 'true',
    }

    # Initialize security middleware
    SecurityMiddleware(app, security_config)

    # Initialize database
    db.init_app(app)

    # Initialize login manager
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(admin_blueprint)

    # Create database tables
    with app.app_context():
        db.create_all()
        # Create admin user if none exists
        if not User.query.filter_by(role='admin').first():
            admin_email = os.getenv('ADMIN_EMAIL')
            admin_name = os.getenv('ADMIN_NAME', 'Admin User')
            if admin_email:
                admin = User(
                    email=admin_email,
                    name=admin_name,
                    role='admin',
                    is_active=True
                )
                db.session.add(admin)
                db.session.commit()

    # Root route
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            if current_user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('dashboard'))  # Regular user dashboard
        return redirect(url_for('auth.login'))

    # Configure SSL if enabled
    if os.getenv('USE_LETSENCRYPT', 'false').lower() == 'true':
        setup_letsencrypt(app)

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(
        host=os.getenv('FLASK_HOST', '0.0.0.0'),
        port=int(os.getenv('FLASK_PORT', 5000)),
        debug=os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    ) 
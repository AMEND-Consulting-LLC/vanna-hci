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

if __name__ == "__main__":
    # Verify Azure OpenAI configuration
    required_env_vars = [
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_DEPLOYMENT",
        "AZURE_CLIENT_ID",
        "AZURE_CLIENT_SECRET",
        "AZURE_TENANT_ID",
        "API_SIGNING_SECRET"
    ]
    
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        print("Error: Missing required environment variables:")
        for var in missing_vars:
            print(f"- {var}")
        exit(1)
    
    # Configure SSL context
    ssl_context = None
    
    # Try Let's Encrypt first if enabled
    if letsencrypt_config["enabled"]:
        if not all([letsencrypt_config["domains"], letsencrypt_config["email"]]):
            print("Error: LETSENCRYPT_DOMAINS and LETSENCRYPT_EMAIL are required when USE_LETSENCRYPT is true")
            exit(1)
            
        print("Setting up Let's Encrypt certificates...")
        ssl_config = setup_letsencrypt(
            app_domains=letsencrypt_config["domains"],
            contact_email=letsencrypt_config["email"],
            cert_dir="/certs",
            staging=letsencrypt_config["staging"]
        )
        
        if ssl_config:
            print("Successfully obtained Let's Encrypt certificates")
            ssl_context = configure_ssl_context(**ssl_config)
        else:
            print("Failed to obtain Let's Encrypt certificates")
            exit(1)
            
    # Fall back to manual certificates if Let's Encrypt is disabled
    elif all([security_config["ssl_cert"], security_config["ssl_key"]]):
        print("Using provided SSL certificates")
        ssl_context = configure_ssl_context(
            cert_path=security_config["ssl_cert"],
            key_path=security_config["ssl_key"],
            password=security_config["ssl_password"]
        )
    
    # Run the Flask app
    app.run(
        host="0.0.0.0",
        port=8000,
        ssl_context=ssl_context
    ) 
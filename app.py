from vanna.chromadb.chromadb_vector import ChromaDB_VectorStore
from vanna.openai.openai_chat import OpenAI_Chat
from vanna.flask import VannaFlaskApp
from vanna.flask.azure_auth import AzureAuth
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
app = VannaFlaskApp(
    vn=vector_store,
    auth=AzureAuth(azure_auth_config),
    debug=True,
    allow_llm_to_see_data=True,  # Since we're using local storage
    title="Vanna.AI with Azure SSO",
    subtitle="Your AI-powered SQL assistant with Azure Authentication"
)

# Configure Flask session
app.flask_app.config['SESSION_TYPE'] = 'filesystem'
Session(app.flask_app)

if __name__ == "__main__":
    # Verify Azure OpenAI configuration
    required_env_vars = [
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_DEPLOYMENT",
        "AZURE_CLIENT_ID",
        "AZURE_CLIENT_SECRET",
        "AZURE_TENANT_ID"
    ]
    
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        print("Error: Missing required environment variables:")
        for var in missing_vars:
            print(f"- {var}")
        exit(1)
    
    # Run the Flask app
    app.run(host="0.0.0.0", port=8000) 
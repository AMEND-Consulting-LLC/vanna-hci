#!/bin/bash

# Function to generate a random string
generate_random_string() {
    openssl rand -base64 32
}

# Check if .env exists, if not create it from template
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.template .env
    # Generate a random Flask secret key
    SECRET_KEY=$(generate_random_string)
    sed -i.bak "s/your-secret-key-here/$SECRET_KEY/" .env
    rm .env.bak
fi

# Check if .env.docker exists, if not create it from template
if [ ! -f .env.docker ]; then
    echo "Creating .env.docker file from template..."
    cp .env.docker.template .env.docker
    # Generate a random Flask secret key
    SECRET_KEY=$(generate_random_string)
    sed -i.bak "s/your-secret-key-here/$SECRET_KEY/" .env.docker
    rm .env.docker.bak
fi

# Create auth directory for ChromaDB if it doesn't exist
if [ ! -d auth ]; then
    mkdir auth
fi

# Create ChromaDB credentials file if it doesn't exist
if [ ! -f auth/credentials.json ]; then
    echo "Creating ChromaDB credentials file..."
    echo '{"username": "admin", "password": "'$(generate_random_string)'"}' > auth/credentials.json
fi

# Create necessary directories
mkdir -p data/chromadb
mkdir -p sessions

echo "Environment setup complete!"
echo "Please update the following in your .env or .env.docker file:"
echo "- AZURE_CLIENT_ID"
echo "- AZURE_CLIENT_SECRET"
echo "- AZURE_TENANT_ID"
echo "- AZURE_OPENAI_ENDPOINT"
echo "- AZURE_OPENAI_API_KEY" 
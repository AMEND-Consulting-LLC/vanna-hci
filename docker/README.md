# Docker Setup Guide

This guide explains how to set up and run the Vanna.AI application using Docker.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- Azure account with:
  - Azure Entra ID application registration
  - Azure OpenAI service
- Git

## Quick Start

1. Clone the repository and navigate to the project directory:
```bash
git clone <repository-url>
cd vanna-hci
```

2. Run the environment setup script:
```bash
chmod +x scripts/setup_env.sh
./scripts/setup_env.sh
```

3. Configure your environment:
   - Copy `.env.docker.template` to `.env.docker`
   - Update the following required variables:
     ```bash
     # Azure SSO Authentication
     AZURE_CLIENT_ID=your-client-id
     AZURE_CLIENT_SECRET=your-client-secret
     AZURE_TENANT_ID=your-tenant-id
     AZURE_REDIRECT_URI=your-callback-url

     # Azure OpenAI Configuration
     AZURE_OPENAI_ENDPOINT=your-azure-openai-endpoint
     AZURE_OPENAI_API_KEY=your-azure-openai-key

     # Database Configuration
     POSTGRES_PASSWORD=your-secure-password  # Use a strong password

     # Security
     FLASK_SECRET_KEY=your-secret-key
     API_SIGNING_SECRET=your-signing-secret
     ```

4. Start the services:
```bash
docker-compose --env-file .env.docker up -d
```

5. Check the initial admin API key:
```bash
docker exec vanna-hci-vanna-1 cat /app/data/admin_key.txt
```

## Architecture

The application consists of three main services:

1. **Vanna API Service**:
   - Flask application with Azure SSO integration
   - API security middleware
   - SSL/TLS support with Let's Encrypt

2. **Database Service (Supabase PostgreSQL)**:
   - Persistent data storage
   - API key management
   - Audit logging
   - Compatible with Supabase hosted service

3. **ChromaDB Service**:
   - Vector database for AI operations
   - Authenticated access
   - Persistent storage

## Database Configuration

### Local Development
```bash
# Default SQLite configuration
DATABASE_URL=sqlite:///data/api_keys.db
```

### Production (PostgreSQL)
```bash
# PostgreSQL configuration
POSTGRES_USER=vanna
POSTGRES_PASSWORD=your-secure-password
POSTGRES_DB=vanna
```

### Database Initialization
The database is automatically initialized when the container starts:
- Tables are created if they don't exist
- Initial admin API key is generated
- Basic schema is set up

### Data Persistence
Database data is stored in a Docker volume:
```yaml
volumes:
  postgres_data:
    driver: local
```

## API Security Features

### API Key Management

1. **Create a new API key**:
```bash
curl -X POST http://localhost:8000/api/keys \
  -H "X-API-Key: YOUR_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "role": "user",
    "description": "Development key",
    "expires_in_days": 30
  }'
```

2. **List API keys**:
```bash
curl http://localhost:8000/api/keys \
  -H "X-API-Key: YOUR_ADMIN_KEY"
```

3. **Revoke an API key**:
```bash
curl -X DELETE http://localhost:8000/api/keys/KEY_TO_REVOKE \
  -H "X-API-Key: YOUR_ADMIN_KEY"
```

### Request Signing

All API requests must be signed. Example Python code:
```python
import time
import hmac
import hashlib
import requests

def sign_request(method, path, body, secret):
    timestamp = str(int(time.time()))
    message = f"{timestamp}{method}{path}"
    if body:
        message += body
    
    signature = hmac.new(
        secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return {
        'X-Request-Timestamp': timestamp,
        'X-Request-Signature': signature
    }

# Example request
api_key = "your-api-key"
secret = "your-signing-secret"
data = {"query": "SELECT * FROM users"}

headers = sign_request('POST', '/api/query', json.dumps(data), secret)
headers['X-API-Key'] = api_key
headers['Content-Type'] = 'application/json'

response = requests.post(
    'http://localhost:8000/api/query',
    headers=headers,
    json=data
)
```

### Security Features

1. **API Key Security**:
   - Role-based access control
   - Key expiration
   - Rate limiting
   - Audit logging

2. **Request Security**:
   - Request signing
   - Timestamp validation
   - Replay attack prevention
   - Input validation

3. **Output Security**:
   - Response sanitization
   - Content security headers
   - CORS protection

## Environment Variables

### Required Variables
```bash
# Azure SSO Authentication
AZURE_CLIENT_ID          # Your Azure AD application client ID
AZURE_CLIENT_SECRET      # Your Azure AD application client secret
AZURE_TENANT_ID         # Your Azure AD tenant ID
AZURE_REDIRECT_URI      # OAuth callback URL

# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT   # Your Azure OpenAI service endpoint
AZURE_OPENAI_API_KEY    # Your Azure OpenAI API key

# Security
FLASK_SECRET_KEY        # Flask session secret key
API_SIGNING_SECRET      # API request signing secret

# Database
POSTGRES_PASSWORD       # PostgreSQL password
```

### Optional Variables with Defaults
```bash
# Docker Configuration
PORT=8000
FLASK_ENV=production

# Database Configuration
POSTGRES_USER=vanna
POSTGRES_DB=vanna

# Security Configuration
RATE_LIMIT=100
FORCE_HTTPS=true
TRUSTED_PROXIES=1
```

## Directory Structure

```
.
├── auth/                  # ChromaDB authentication
│   └── credentials.json
├── data/
│   ├── chromadb/         # ChromaDB persistent storage
│   └── admin_key.txt     # Initial admin API key
├── sessions/             # Flask session storage
├── certs/               # SSL certificates
├── .env.docker         # Docker environment configuration
└── docker-compose.yml  # Docker Compose configuration
```

## Security Considerations

1. **Environment Variables**:
   - Never commit `.env.docker` to version control
   - Use secrets management in production
   - Regularly rotate secrets and API keys

2. **Database Security**:
   - Use strong passwords
   - Limit database access to containers
   - Regular security updates
   - Monitor database logs

3. **API Security**:
   - Rotate API keys regularly
   - Monitor API usage
   - Review audit logs
   - Set appropriate rate limits

4. **Network Security**:
   - Use HTTPS in production
   - Configure CORS appropriately
   - Implement proper firewalls
   - Regular security audits

## Health Checks

The Docker Compose configuration includes health checks for all services:

1. **Vanna API**:
```bash
curl -f http://localhost:8000/health
```

2. **PostgreSQL**:
```bash
pg_isready -U vanna
```

3. **ChromaDB**:
```bash
curl -f http://localhost:8001/api/v1/heartbeat
```

## Troubleshooting

1. **Check service status**:
```bash
docker-compose ps
```

2. **View logs**:
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f vanna
docker-compose logs -f db
docker-compose logs -f chromadb
```

3. **Common Issues**:
   - Database connection errors: Check credentials and network
   - API key issues: Verify key exists and is active
   - SSL/TLS errors: Check certificate configuration
   - Permission errors: Check volume permissions

## Updates and Maintenance

1. **Update images**:
```bash
docker-compose pull
docker-compose up -d
```

2. **Backup database**:
```bash
docker exec -t vanna-hci-db-1 pg_dumpall -c -U vanna > dump.sql
```

3. **Restore database**:
```bash
cat dump.sql | docker exec -i vanna-hci-db-1 psql -U vanna
```

## Support

For issues and support:
- Create an issue in the repository
- Check the troubleshooting guide
- Review Azure SSO documentation
- Consult the API security documentation 
# Vanna AI Configuration Guide

This document provides detailed information about configuring the Vanna AI application in a containerized environment.

## Table of Contents
- [Overview](#overview)
- [Configuration Methods](#configuration-methods)
- [Environment Variables](#environment-variables)
- [Secrets Management](#secrets-management)
- [Configuration Validation](#configuration-validation)
- [Example Usage](#example-usage)

## Overview

The Vanna AI configuration system provides a flexible way to configure the application through:
- Environment variables
- `.env` files
- Docker secrets
- Runtime configuration

## Configuration Methods

### 1. Environment Variables

All configuration options can be set through environment variables. The application uses the `VANNA_` prefix for most settings.

### 2. .env File

Copy the template and modify for your environment:
```bash
cp docker/.env.template docker/.env
```

### 3. Docker Secrets

Sensitive values can be managed using Docker secrets. Place secret files in `/run/secrets/`:
```bash
echo "my-secret-value" > /run/secrets/vanna_api_key
```

## Environment Variables

### Core Settings

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `VANNA_DEBUG` | Enable debug mode | `false` | No |
| `VANNA_LOG_LEVEL` | Logging level | `INFO` | No |

### API Settings

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `VANNA_API_HOST` | API server host | `0.0.0.0` | Yes |
| `VANNA_API_PORT` | API server port | `8000` | Yes |
| `VANNA_API_KEY` | Authentication key | - | Yes |

### Database Settings

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `VANNA_DB_HOST` | PostgreSQL host | `localhost` | Yes |
| `VANNA_DB_PORT` | PostgreSQL port | `5432` | Yes |
| `VANNA_DB_NAME` | Database name | `vanna` | Yes |
| `VANNA_DB_USER` | Database user | - | Yes |
| `VANNA_DB_PASSWORD` | Database password | - | Yes |

### Vector Store Settings

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `VANNA_VECTOR_STORE_TYPE` | Vector store type | `chromadb` | Yes |
| `VANNA_VECTOR_STORE_URL` | Vector store URL | - | No |
| `VANNA_VECTOR_STORE_API_KEY` | Vector store API key | - | No |

### Resource Limits

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `VANNA_MAX_MEMORY` | Maximum memory (MB) | `4096` | No |
| `VANNA_MAX_CPU` | Maximum CPU cores | `2` | No |

### Security Settings

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `VANNA_ENABLE_SSL` | Enable SSL/TLS | `false` | No |
| `VANNA_SSL_CERT` | SSL certificate path | - | If SSL enabled |
| `VANNA_SSL_KEY` | SSL key path | - | If SSL enabled |

### Database Configuration Settings

Vanna supports configuration for multiple database types. Here are the configuration options for each supported database:

#### BigQuery Settings

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `VANNA_DB_TYPE` | Set to `bigquery` for BigQuery | - | Yes |
| `VANNA_BIGQUERY_PROJECT_ID` | Google Cloud Project ID | - | Yes |
| `VANNA_BIGQUERY_CRED_FILE` | Path to credentials JSON file | - | No |

Example .env configuration:
```bash
VANNA_DB_TYPE=bigquery
VANNA_BIGQUERY_PROJECT_ID=my-project-id
VANNA_BIGQUERY_CRED_FILE=/path/to/credentials.json
```

#### SQL Server Settings

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `VANNA_DB_TYPE` | Set to `sqlserver` for SQL Server | - | Yes |
| `VANNA_SQLSERVER_CONN_STR` | ODBC connection string | - | Yes |

Example .env configuration:
```bash
VANNA_DB_TYPE=sqlserver
VANNA_SQLSERVER_CONN_STR="Driver={ODBC Driver 17 for SQL Server};Server=my-server;Database=my-db;UID=my-user;PWD=my-password"
```

## Secrets Management

Sensitive configuration values are managed through the `SecretsManager` class, which:
1. Checks environment variables
2. Falls back to Docker secrets
3. Returns None if not found

### Docker Secrets Location
By default, secrets are read from `/run/secrets/`. This can be customized:

```python
from vanna.config import SecretsManager

secrets = SecretsManager(secrets_dir='/path/to/secrets')
```

### Supported Secret Types
- API keys
- Database credentials
- SSL/TLS certificates
- Vector store credentials

## Configuration Validation

The configuration system validates:

### Types
- String formats (URLs, hostnames)
- Integer ranges (ports)
- Boolean values

### Required Values
Ensures all required configuration is present:
- API settings
- Database credentials
- Vector store configuration

### Format Validation
- URL formats
- Hostname patterns
- Port ranges (1-65535)
- Allowed values for enums

## Example Usage

### Basic Configuration

```python
from vanna.config import ConfigManager

# Initialize with .env file
config = ConfigManager(env_file='docker/.env')

# Access configuration
debug_mode = config.get('DEBUG')
api_port = config.get('API_PORT')
```

### Working with Secrets

```python
from vanna.config import SecretsManager

secrets = SecretsManager()

# Get a secret
api_key = secrets.get_secret('VANNA_API_KEY')

# List available secrets
available_secrets = secrets.list_available_secrets()
```

### Custom Configuration

```python
from vanna.config import ConfigManager

config = ConfigManager()

# Set custom value
config.set('CUSTOM_SETTING', 'value')

# Get all configuration
all_config = config.config
```

### Using Environment Variables in Code

You can use environment variables in your code like this:

```python
import os
from vanna import VannaBase

config = {
    "database": {
        "db_type": os.getenv("VANNA_DB_TYPE"),
        # BigQuery settings
        "project_id": os.getenv("VANNA_BIGQUERY_PROJECT_ID"),
        "cred_file_path": os.getenv("VANNA_BIGQUERY_CRED_FILE"),
        # SQL Server settings
        "odbc_conn_str": os.getenv("VANNA_SQLSERVER_CONN_STR")
    }
}

vn = VannaBase(config=config)
```

## Error Handling

The configuration system raises `ValueError` for:
- Missing required values
- Invalid formats
- Type mismatches
- Range violations

Example error handling:
```python
try:
    config = ConfigManager()
except ValueError as e:
    print(f"Configuration error: {e}") 
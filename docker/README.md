# Docker Setup for Vanna AI

This directory contains the Docker configuration for running the Vanna AI text2sql platform.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- Git

## Quick Start

1. Copy the environment template:
   ```bash
   cp .env.template .env
   ```

2. Edit the `.env` file with your configuration:
   - Add your API keys
   - Configure database connection
   - Adjust other settings as needed

3. Build and start the containers:
   ```bash
   docker-compose up -d
   ```

4. Check the status:
   ```bash
   docker-compose ps
   ```

## Configuration

### Environment Variables

#### Core Configuration
- `VANNA_API_KEY`: Your LLM API key (e.g., OpenAI key)
- `VANNA_MODEL`: Model to use (default: gpt-4)
- `VANNA_VECTOR_STORE`: Vector store type (default: chromadb)
- `VANNA_PORT`: Port to expose the service (default: 8000)

#### Vector Store Configuration
- `VANNA_VECTOR_STORE_API_KEY`: API key for vector store (if required)
- `VANNA_VECTOR_STORE_URL`: Vector store endpoint URL
- `VANNA_VECTOR_STORE_NAMESPACE`: Namespace for vector store

#### Database Configuration
- `VANNA_DB_TYPE`: Database type (e.g., postgres, mysql)
- `VANNA_DB_HOST`: Database host
- `VANNA_DB_PORT`: Database port
- `VANNA_DB_NAME`: Database name
- `VANNA_DB_USER`: Database user
- `VANNA_DB_PASSWORD`: Database password

## Directory Structure

- `Dockerfile`: Multi-stage build configuration
- `docker-compose.yml`: Service orchestration
- `.env.template`: Environment variable template
- `README.md`: This documentation

## Volumes

The following volumes are created:
- `../data`: Application data
- `../logs`: Application logs
- `../vector_data`: Vector store data (when using ChromaDB)

## Networks

- `vanna-network`: Bridge network for container communication

## Health Checks

The application includes health checks that run every 30 seconds. You can monitor the health status using:
```bash
docker-compose ps
```

## Troubleshooting

1. If the containers fail to start:
   ```bash
   docker-compose logs
   ```

2. To restart services:
   ```bash
   docker-compose restart
   ```

3. To rebuild after changes:
   ```bash
   docker-compose build --no-cache
   docker-compose up -d
   ```

## Security Notes

1. Never commit the `.env` file
2. Regularly update base images
3. Use secure passwords
4. Keep API keys confidential

## Maintenance

1. Backup volumes regularly
2. Monitor container logs
3. Update dependencies as needed
4. Check container health status 
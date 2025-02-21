FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    TZ=UTC

# Create and set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -r vanna && \
    chown -R vanna:vanna /app

# Copy requirements files
COPY requirements*.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt && \
    if [ -f requirements-azure-auth.txt ]; then \
        pip install --no-cache-dir -r requirements-azure-auth.txt; \
    fi

# Copy application code
COPY . .

# Create necessary directories with appropriate permissions
RUN mkdir -p /data /certs /logs && \
    chown -R vanna:vanna /data /certs /logs && \
    chmod -R 755 /data /logs && \
    chmod -R 750 /certs

# Switch to non-root user
USER vanna

# Set default command
CMD ["python", "app.py"] 
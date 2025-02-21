# Build stage
FROM python:3.9-slim as builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy only the files needed for installation
COPY pyproject.toml .
COPY src/ src/

# Install build dependencies and build wheel
RUN pip install --no-cache-dir build && \
    python -m build

# Runtime stage
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Create non-root user
RUN useradd -m -u 1000 vanna && \
    chown -R vanna:vanna /app

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy wheel from builder stage
COPY --from=builder /app/dist/*.whl .

# Install the wheel and remove it
RUN pip install --no-cache-dir *.whl && \
    rm *.whl

# Create necessary directories with proper permissions
RUN mkdir -p /app/data /app/logs && \
    chown -R vanna:vanna /app/data /app/logs

# Switch to non-root user
USER vanna

# Environment variables
ENV VANNA_HOST=0.0.0.0
ENV VANNA_PORT=8000
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${VANNA_PORT}/health || exit 1

# Expose port
EXPOSE 8000

# Default command
CMD ["python", "-m", "vanna.flask.app"] 
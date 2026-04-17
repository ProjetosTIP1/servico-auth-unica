# Use the official Python image as a base
FROM ghcr.io/astral-sh/uv:latest AS uv
FROM python:3.12-slim-bullseye

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/root/.local/bin:${PATH}"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy uv from the official image
COPY --from=uv /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./

# Set the working directory
WORKDIR /app

# Copy dependency files first for better caching

# Install dependencies using uv
# --frozen ensures we use the exact versions in uv.lock
# --no-install-project skips installing the current package (only dependencies)
RUN uv sync --frozen --no-install-project --no-dev

# Copy the rest of the application code
COPY . .

RUN uv sync --frozen

# Create the images and backups directories and set permissions
RUN mkdir -p /app/images

# Create a non-root user for security
RUN groupadd -r appuser && useradd -m -r -g appuser appuser \
    && chown -R appuser:appuser /app

USER appuser

# Expose the application port
EXPOSE 8000

# Healthcheck to ensure the container is healthy
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Command to run the application using uv to ensure the virtual environment is used
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
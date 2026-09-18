# ---------------------------------------------------------
# UJA Editorial Pre-Filter Pipeline - Backend API Dockerfile
# ---------------------------------------------------------

# Uses Python 3.13 slim image for a lightweight footprint
FROM python:3.13-slim

# Set the working directory to the project root
WORKDIR /app

# Prevent Python from writing pyc files to disc
ENV PYTHONDONTWRITEBYTECODE=1
# Prevent Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED=1

# Install required native system packages
# - build-essential & gcc: required for compiling C-extensions (e.g. some scientific libraries) if wheels are missing
# - libpq-dev: required for compiling psycopg2 (PostgreSQL driver)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy only the requirements files first to leverage Docker build cache
COPY requirements.txt .
COPY apps/api/requirements.txt ./apps/api/

# Upgrade pip and install all Python dependencies
# Installs root requirements (data science packages) and API requirements (FastAPI, SQLAlchemy)
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r apps/api/requirements.txt

# Copy only the strictly necessary source code and configurations
# Explicit COPY prevents accidental inclusion of heavy/unnecessary folders like experiments/ or data/
COPY apps/api/ ./apps/api/
COPY packages/ ./packages/
COPY config.yaml .

# Create necessary runtime directories that might be required at runtime
RUN mkdir -p storage reports apps/api/temp_manuscripts

# Expose the API port
EXPOSE 8000

# Start the FastAPI server using Uvicorn
# Environment variables like DATABASE_HOST, JWT_SECRET, and OLLAMA_URL will be provided at runtime
CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

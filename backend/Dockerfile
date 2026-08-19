# Use official Python runtime as base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py field_defs.py mobility_program_generator.py program_pdf.py secrets_config.py .

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port 8080 (Cloud Run default)
EXPOSE 8080

# Use gunicorn for production
CMD exec gunicorn --bind :$PORT --workers 2 --threads 4 --timeout 60 main:app

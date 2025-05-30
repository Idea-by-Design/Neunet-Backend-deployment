# Use official Python image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y build-essential gcc && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy project
COPY . .

# Expose port
EXPOSE 8000

# Set environment variables for production (can be overridden at runtime)
ENV PORT=8000

# Start FastAPI with Gunicorn
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "services.api.main:app", "--bind", "0.0.0.0:8000", "--workers", "1", "--timeout", "120"]

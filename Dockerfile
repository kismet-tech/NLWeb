# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy the entire code directory
COPY code/ ./code/
COPY static/ ./static/

# Set working directory to code
WORKDIR /app/code

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Expose the port Cloud Run expects
EXPOSE 8080

# Run the application
CMD ["python", "app-file.py"] 
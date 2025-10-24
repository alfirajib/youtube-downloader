FROM python:3.10-slim

# Install FFmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create downloads folder
RUN mkdir -p downloads

# Expose port
EXPOSE 8080

# Start application
CMD gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
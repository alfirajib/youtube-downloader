FROM python:3.11-slim

# Install ffmpeg dan dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements dan install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy semua file aplikasi
COPY . .

# Buat folder downloads
RUN mkdir -p downloads

# Expose port
EXPOSE 8080

# Jalankan aplikasi
CMD gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 2 --timeout 0 app:app
FROM python:3.11-slim

WORKDIR /app

# Force cache invalidation - v4
RUN echo "Building fresh art service..."

# Install git for the samsung-tv-ws-api fork
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the script
COPY daily_art.py .

# Create volume for data (token persistence)
RUN mkdir -p /app/data

# Environment variables with defaults
ENV TV_IP=192.168.1.100
ENV DEPT_ID=11
ENV INTERVAL=86400

CMD ["python", "daily_art.py"]

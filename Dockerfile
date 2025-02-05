FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for OpenCV and other packages
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Instead of opencv-python, use opencv-python-headless for container environments
RUN pip uninstall -y opencv-python && pip install opencv-python-headless


# Copy the rest of the application
COPY . .

# Expose port
EXPOSE 8000

# Run the application
# Run with more verbose logging
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--log-level", "debug", "--error-logfile", "-", "--access-logfile", "-", "application:application"]
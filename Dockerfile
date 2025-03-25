# Use official Python image
FROM python:3.11-slim

# Create a non-root user
RUN useradd -m myuser

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file 
COPY --chown=myuser:myuser requirements.txt .

# Switch to non-root user
USER myuser

# Create a virtual environment
RUN python -m venv venv
ENV PATH="/app/venv/bin:$PATH"

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the entire application
COPY --chown=myuser:myuser . .

# Expose the port Flask runs on
EXPOSE 5000

# Set environment variables for Flask
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# Use gunicorn for production-ready server
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]

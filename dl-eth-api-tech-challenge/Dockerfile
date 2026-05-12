# Multi-stage build: Frontend
FROM node:20-slim AS frontend-builder
WORKDIR /frontend
COPY vue/package*.json ./
RUN npm install
COPY vue/ ./
RUN npm run build

# Final stage: Python backend with served frontend
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libffi-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY app/ .

# Copy built frontend from builder stage
COPY --from=frontend-builder /frontend/dist ./static/dist

# Expose port
EXPOSE 8080

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the application with gunicorn
CMD ["sh", "-c", "gunicorn app:app --bind 0.0.0.0:${PORT:-8080}"]
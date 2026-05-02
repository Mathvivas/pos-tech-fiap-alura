# Multi-stage build: Frontend
FROM node:20 as frontend-builder
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
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY app/ ./app/

# Copy built frontend from builder stage
COPY --from=frontend-builder /frontend/dist ./app/static/dist

# Expose port
EXPOSE 8080

# Set environment variables
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["python", "app/app.py"]


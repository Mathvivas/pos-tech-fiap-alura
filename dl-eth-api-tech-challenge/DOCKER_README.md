# Ethereum Price Prediction - Docker Setup

This project includes Docker support for running the entire application (Flask backend + Vue frontend) in containers.

## Quick Start with Docker Compose (Recommended for Development)

### Prerequisites
- Docker
- Docker Compose

### Run the Application

```bash
docker-compose up --build
```

This will:
- Build and start the Flask backend on `http://localhost:8080`
- Build and start the Vue development server on `http://localhost:5173`

### Access the Application
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8080/predict
- **API Docs**: http://localhost:8080/docs/

## Docker Build (Production - Single Dockerfile)

### Build the Docker Image

```bash
docker build -t ethereum-predictor .
```

### Run the Container

```bash
docker run -p 8080:8080 ethereum-predictor
```

This will serve both the backend API and the frontend (built static files) on port 8080.

### Access the Application
- **Application**: http://localhost:8080
- **API**: http://localhost:8080/predict
- **API Docs**: http://localhost:8080/docs/

## File Structure

```
.
├── Dockerfile              # Multi-stage build (production)
├── Dockerfile.backend      # Backend only (for docker-compose)
├── docker-compose.yml      # Local development setup
├── .dockerignore           # Files to exclude from Docker build
├── app/                    # Flask backend
│   ├── app.py
│   ├── routes/
│   ├── model/
│   └── predicao.py
├── vue/                    # Vue frontend
│   ├── src/
│   ├── Dockerfile         # Frontend for docker-compose
│   └── package.json
└── requirements.txt        # Python dependencies
```

## Environment Variables

For development with docker-compose, the frontend API URL is set to `http://localhost:8080`.

To customize:
- **Backend**: Update `docker-compose.yml` or set `FLASK_ENV`
- **Frontend**: Update `VITE_API_BASE_URL` in `docker-compose.yml`

## Troubleshooting

### Port Already in Use
If port 8080 (or 5173) is already in use:
- Change the port mapping in `docker-compose.yml` or Docker run command
- Example: `docker run -p 8000:8080 ethereum-predictor`

### Model Files Not Found
Ensure the model files exist:
- `app/model/model_weights.pth`
- `app/model/scaler.pkl`

### Frontend Not Loading
If using the production Dockerfile:
1. Ensure the Vue build completes successfully
2. The frontend is served from `app/static/dist`
3. Access the root path `/` for the SPA

## Development Workflow

1. **Start services**:
   ```bash
   docker-compose up
   ```

2. **Make code changes**:
   - Frontend: Changes in `vue/src` will auto-reload on port 5173
   - Backend: Restart the backend container with `docker-compose restart backend`

3. **Stop services**:
   ```bash
   docker-compose down
   ```

## Production Deployment

Use the single `Dockerfile` for production:

```bash
docker build -t ethereum-predictor:v1.0 .
docker run -p 8080:8080 ethereum-predictor:v1.0
```

This bundles both frontend and backend into a single container, suitable for deployment to services like AWS, GCP, or Docker Hub.

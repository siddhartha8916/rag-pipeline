@echo off
echo Starting RAG Pipeline Application...
echo.

echo Step 1: Starting Milvus with Docker Compose...
docker-compose up -d

echo.
echo Step 2: Waiting for services to be ready...
timeout /t 30 /nobreak > nul

echo.
echo Step 3: Checking service status...
docker-compose ps

echo.
echo Step 4: Starting FastAPI application...
echo You can now access the API at: http://localhost:8000
echo API Documentation: http://localhost:8000/docs
echo.

cd app
python main.py
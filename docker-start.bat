@echo off
echo ===================================
echo RAG Pipeline Docker Setup
echo ===================================
echo.

echo Step 1: Checking if .env.docker exists...
if not exist ".env.docker" (
    echo ERROR: .env.docker file not found!
    echo Please copy .env.docker.template to .env.docker and add your Perplexity API key
    echo.
    echo copy .env.docker .env.docker
    echo Then edit .env.docker and add your API key
    pause
    exit /b 1
)

echo Step 2: Building Docker images...
docker-compose build --no-cache

if %ERRORLEVEL% neq 0 (
    echo ERROR: Docker build failed!
    pause
    exit /b 1
)

echo.
echo Step 3: Starting all services...
docker-compose --env-file .env.docker up -d

if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to start services!
    pause
    exit /b 1
)

echo.
echo Step 4: Waiting for services to be ready...
echo This may take 1-2 minutes for first startup...
timeout /t 60 /nobreak > nul

echo.
echo Step 5: Checking service health...
docker-compose ps

echo.
echo ===================================
echo Setup Complete!
echo ===================================
echo.
echo Your RAG Pipeline is now running at:
echo - API: http://localhost:8000
echo - API Docs: http://localhost:8000/docs
echo - Health Check: http://localhost:8000/health
echo.
echo Milvus services:
echo - Milvus: localhost:19530
echo - MinIO Console: http://localhost:9001
echo.
echo To view logs: docker-compose logs -f rag-app
echo To stop: docker-compose down
echo.
pause
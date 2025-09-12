@echo off
echo Stopping RAG Pipeline services...
echo.

docker-compose down

echo.
echo Services stopped.
echo.
echo To remove all data volumes (WARNING: This will delete all uploaded documents):
echo docker-compose down -v
echo.
pause
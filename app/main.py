from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.routers import documents, health
from app.config import settings
import logging
import uvicorn
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="RAG Pipeline API",
    description="A FastAPI application implementing RAG (Retrieval-Augmented Generation) architecture using Milvus vector database and Perplexity LLM",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(documents.router, prefix="/documents", tags=["Documents"])

# Serve the main page
@app.get("/")
async def serve_frontend():
    """Serve the main frontend page."""
    static_index = os.path.join(static_dir, "index.html")
    if os.path.exists(static_index):
        return FileResponse(static_index)
    else:
        return {"message": "RAG Pipeline API", "frontend": "Not configured", "docs": "/docs"}

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception handler caught: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("Starting RAG Pipeline API...")
    logger.info(f"Milvus host: {settings.MILVUS_HOST}:{settings.MILVUS_PORT}")
    logger.info(f"Upload directory: {settings.UPLOAD_DIR}")
    logger.info(f"Embedding model: {settings.EMBEDDING_MODEL}")
    
    # Check if Perplexity API key is configured
    if not settings.PERPLEXITY_API_KEY:
        logger.warning("Perplexity API key not configured. Please set PERPLEXITY_API_KEY in .env file")
    else:
        logger.info("Perplexity API key is configured")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down RAG Pipeline API...")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
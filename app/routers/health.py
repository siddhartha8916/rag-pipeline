from fastapi import APIRouter, HTTPException
from app.services.rag_pipeline import RAGPipeline
from app.models.schemas import HealthResponse
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
rag_pipeline = RAGPipeline()

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint to verify all components are working.
    
    Checks:
    - Milvus connection
    - Perplexity API configuration
    - Upload directory accessibility
    """
    try:
        health_status = rag_pipeline.health_check()
        
        # Determine overall status
        overall_status = "healthy" if all(health_status.values()) else "unhealthy"
        
        return HealthResponse(
            status=overall_status,
            milvus_connected=health_status.get("milvus_connected", False),
            timestamp=datetime.now()
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return HealthResponse(
            status="unhealthy",
            milvus_connected=False,
            timestamp=datetime.now()
        )
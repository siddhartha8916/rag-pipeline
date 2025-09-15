from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from app.services.rag_pipeline import RAGPipeline
from app.models.schemas import ChatRequest, ChatResponse, DocumentUploadResponse
import logging
import json
import asyncio

logger = logging.getLogger(__name__)

router = APIRouter()
rag_pipeline = RAGPipeline()

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload and process a PDF document.
    
    The document will be:
    1. Validated (must be PDF, within size limits)
    2. Text extracted and chunked
    3. Converted to embeddings
    4. Stored in the vector database
    """
    try:
        result = await rag_pipeline.upload_and_process_document(file)
        return result
    except Exception as e:
        logger.error(f"Document upload failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with the RAG system.
    
    The system will:
    1. Convert your question to embeddings
    2. Find similar document chunks
    3. Use them as context for generating a response
    4. Return the response with source information
    """
    try:
        if not request.message or not request.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        result = await rag_pipeline.chat(request)
        return result
    except Exception as e:
        logger.error(f"Chat request failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat-stream")
async def chat_stream(request: ChatRequest):
    """
    Chat with the RAG system using streaming responses.
    
    Returns server-sent events with streaming response data.
    """
    try:
        if not request.message or not request.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        async def generate_stream():
            try:
                # Get the RAG response
                result = await rag_pipeline.chat(request)
                
                # Stream the response word by word
                words = result.response.split()
                
                for i, word in enumerate(words):
                    # Add space except for first word
                    content = f" {word}" if i > 0 else word
                    
                    data = {
                        "content": content,
                        "sources": result.sources if i == len(words) - 1 else None
                    }
                    
                    yield f"data: {json.dumps(data)}\n\n"
                    
                    # Small delay for typing effect
                    await asyncio.sleep(0.05)
                
                # Send completion signal
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                logger.error(f"Streaming chat failed: {str(e)}")
                error_data = {"error": str(e)}
                yield f"data: {json.dumps(error_data)}\n\n"
                yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
            }
        )
        
    except Exception as e:
        logger.error(f"Chat stream request failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_collection_stats():
    """Get statistics about the document collection."""
    try:
        stats = rag_pipeline.get_collection_stats()
        return stats
    except Exception as e:
        logger.error(f"Failed to get stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/clear")
async def clear_collection():
    """
    Clear all documents from the collection.
    Use with caution - this will delete all uploaded documents!
    """
    try:
        success = rag_pipeline.clear_collection()
        if success:
            return {"message": "Collection cleared successfully. You can now upload new documents."}
        else:
            raise HTTPException(status_code=500, detail="Failed to clear collection")
    except Exception as e:
        logger.error(f"Failed to clear collection: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reset")
async def reset_collection():
    """
    Reset the collection - recreate it if it doesn't exist.
    Useful after clearing the collection or if there are collection issues.
    """
    try:
        # Reset/recreate the collection
        success = rag_pipeline.reset_collection()
        if success:
            return {"message": "Collection reset successfully. Ready for new documents."}
        else:
            raise HTTPException(status_code=500, detail="Failed to reset collection")
    except Exception as e:
        logger.error(f"Failed to reset collection: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
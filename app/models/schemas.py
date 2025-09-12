from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    sources: List[str]
    session_id: str

class DocumentUploadResponse(BaseModel):
    filename: str
    document_id: str
    chunks_created: int
    message: str

class DocumentChunk(BaseModel):
    id: str
    text: str
    metadata: dict
    embedding: Optional[List[float]] = None

class HealthResponse(BaseModel):
    status: str
    milvus_connected: bool
    timestamp: datetime
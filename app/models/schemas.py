from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

# Existing RAG schemas
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

# Database Analytics schemas
class DatabaseType(str, Enum):
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    MSSQL = "mssql"

class DatabaseConnection(BaseModel):
    db_type: DatabaseType
    host: Optional[str] = None
    port: Optional[int] = None
    database: str
    username: Optional[str] = None
    password: Optional[str] = None
    file_path: Optional[str] = None  # For SQLite
    db_schema: Optional[str] = None  # For PostgreSQL schema (defaults to 'public')

class DatabaseConnectionTest(BaseModel):
    connection: DatabaseConnection
    
class DatabaseConnectionTestResponse(BaseModel):
    success: bool
    message: str
    tables: Optional[List[str]] = None
    error: Optional[str] = None

class AnalyticsQueryRequest(BaseModel):
    connection: DatabaseConnection
    user_query: str  # Natural language query like "List all farmers earning less than $40 per month"
    session_id: Optional[str] = None

class AnalyticsResponse(BaseModel):
    html_content: str
    session_id: str
    query_executed: str
    data_summary: Dict[str, Any]
    charts_generated: List[str]

class DatabaseSchema(BaseModel):
    tables: List[Dict[str, Any]]
    relationships: Optional[List[Dict[str, Any]]] = None

class QueryResult(BaseModel):
    columns: List[str]
    rows: List[List[Any]]
    row_count: int
    execution_time: float
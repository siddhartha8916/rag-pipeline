import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Perplexity API
    PERPLEXITY_API_KEY: str = os.getenv("PERPLEXITY_API_KEY", "")
    PERPLEXITY_API_URL: str = "https://api.perplexity.ai/chat/completions"
    
    # Milvus Configuration
    MILVUS_HOST: str = os.getenv("MILVUS_HOST", "localhost")
    MILVUS_PORT: int = int(os.getenv("MILVUS_PORT", "19530"))
    
    # Application Configuration
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "20485760"))  # 10MB
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "1000"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "200"))
    
    # Collection Configuration
    COLLECTION_NAME: str = os.getenv("COLLECTION_NAME", "document_embeddings")
    EMBEDDING_DIM: int = int(os.getenv("EMBEDDING_DIM", "384"))

settings = Settings()
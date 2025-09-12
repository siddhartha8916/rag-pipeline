import os
import uuid
from typing import List, Dict
import PyPDF2
from sentence_transformers import SentenceTransformer
from app.config import settings
from app.models.schemas import DocumentChunk
import logging

logger = logging.getLogger(__name__)

class PDFProcessor:
    def __init__(self):
        self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
        
    def extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file."""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            return text
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            raise Exception(f"Failed to extract text from PDF: {str(e)}")
    
    def chunk_text(self, text: str, chunk_size: int = None, overlap: int = None) -> List[str]:
        """Split text into chunks with overlap."""
        if chunk_size is None:
            chunk_size = settings.CHUNK_SIZE
        if overlap is None:
            overlap = settings.CHUNK_OVERLAP
            
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = start + chunk_size
            chunk = text[start:end]
            
            # Try to break at sentence boundaries
            if end < text_length:
                last_period = chunk.rfind('.')
                last_newline = chunk.rfind('\n')
                break_point = max(last_period, last_newline)
                
                if break_point > start + chunk_size // 2:  # Only break if we're not too close to start
                    chunk = text[start:start + break_point + 1]
                    end = start + break_point + 1
            
            chunks.append(chunk.strip())
            start = end - overlap
            
        return [chunk for chunk in chunks if chunk.strip()]
    
    def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Create embeddings for a list of texts."""
        try:
            embeddings = self.embedding_model.encode(texts, convert_to_tensor=False)
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Error creating embeddings: {str(e)}")
            raise Exception(f"Failed to create embeddings: {str(e)}")
    
    def process_pdf(self, file_path: str, filename: str) -> List[DocumentChunk]:
        """Process PDF file and return document chunks with embeddings."""
        try:
            # Extract text
            text = self.extract_text_from_pdf(file_path)
            
            if not text.strip():
                raise Exception("No text could be extracted from the PDF")
            
            # Split into chunks
            chunks = self.chunk_text(text)
            
            if not chunks:
                raise Exception("No chunks could be created from the text")
            
            # Create embeddings
            embeddings = self.create_embeddings(chunks)
            
            # Create document chunks
            document_chunks = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                doc_chunk = DocumentChunk(
                    id=str(uuid.uuid4()),
                    text=chunk,
                    embedding=embedding,
                    metadata={
                        "filename": filename,
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "file_path": file_path
                    }
                )
                document_chunks.append(doc_chunk)
            
            return document_chunks
            
        except Exception as e:
            logger.error(f"Error processing PDF {filename}: {str(e)}")
            raise Exception(f"Failed to process PDF: {str(e)}")
    
    def create_query_embedding(self, query: str) -> List[float]:
        """Create embedding for a query string."""
        try:
            embedding = self.embedding_model.encode([query], convert_to_tensor=False)
            return embedding[0].tolist()
        except Exception as e:
            logger.error(f"Error creating query embedding: {str(e)}")
            raise Exception(f"Failed to create query embedding: {str(e)}")
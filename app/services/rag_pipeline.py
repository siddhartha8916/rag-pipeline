import os
import uuid
from typing import List, Dict, Tuple
from fastapi import UploadFile
from app.services.pdf_processor import PDFProcessor
from app.services.vector_store import MilvusVectorStore
from app.services.llm_service import PerplexityLLM
from app.models.schemas import DocumentChunk, ChatRequest, ChatResponse, DocumentUploadResponse
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class RAGPipeline:
    def __init__(self):
        self.pdf_processor = PDFProcessor()
        self.vector_store = MilvusVectorStore()
        self.llm_service = PerplexityLLM()
        
        # Create upload directory if it doesn't exist
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    async def upload_and_process_document(self, file: UploadFile) -> DocumentUploadResponse:
        """Upload and process a PDF document into the vector store."""
        try:
            # Validate file
            if not file.filename.lower().endswith('.pdf'):
                raise Exception("Only PDF files are supported")
            
            if file.size and file.size > settings.MAX_FILE_SIZE:
                raise Exception(f"File size exceeds maximum allowed size of {settings.MAX_FILE_SIZE} bytes")
            
            # Generate unique filename to avoid conflicts
            document_id = str(uuid.uuid4())
            filename = f"{document_id}_{file.filename}"
            file_path = os.path.join(settings.UPLOAD_DIR, filename)
            
            # Save uploaded file
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            
            logger.info(f"Saved uploaded file: {filename}")
            
            # Process PDF and create chunks
            document_chunks = self.pdf_processor.process_pdf(file_path, file.filename)
            
            if not document_chunks:
                raise Exception("No content could be extracted from the PDF")
            
            # Store chunks in vector database
            success = self.vector_store.insert_documents(document_chunks)
            
            if not success:
                raise Exception("Failed to store document chunks in vector database")
            
            logger.info(f"Successfully processed and stored {len(document_chunks)} chunks from {file.filename}")
            
            return DocumentUploadResponse(
                filename=file.filename,
                document_id=document_id,
                chunks_created=len(document_chunks),
                message=f"Successfully processed {file.filename} and created {len(document_chunks)} chunks"
            )
            
        except Exception as e:
            logger.error(f"Error processing document {file.filename}: {str(e)}")
            # Clean up file if it was saved
            if 'file_path' in locals() and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass
            raise Exception(f"Document processing failed: {str(e)}")
    
    async def chat(self, request: ChatRequest) -> ChatResponse:
        """Process a chat request using RAG."""
        try:
            # Generate session ID if not provided
            session_id = request.session_id or str(uuid.uuid4())
            
            # Create query embedding
            query_embedding = self.pdf_processor.create_query_embedding(request.message)
            
            # Retrieve similar documents
            try:
                similar_docs = self.vector_store.search_similar_documents(
                    query_embedding, 
                    top_k=5
                )
            except Exception as search_error:
                logger.warning(f"Search failed, possibly empty collection: {str(search_error)}")
                similar_docs = []
            
            if not similar_docs:
                # If no documents found, provide a general response
                response_text = await self.llm_service.generate_simple_response(
                    f"I don't have any specific document context to answer your question about: {request.message}. "
                    "Please upload some PDF documents first so I can provide more accurate answers based on your content."
                )
                
                return ChatResponse(
                    response=response_text,
                    sources=[],
                    session_id=session_id
                )
            
            # Generate response using LLM with context
            response_text = await self.llm_service.generate_response(
                request.message,
                similar_docs
            )
            
            # Extract source information
            sources = []
            for doc in similar_docs:
                metadata = doc.get('metadata', {})
                filename = metadata.get('filename', 'Unknown')
                chunk_index = metadata.get('chunk_index', 0)
                source = f"{filename} (chunk {chunk_index + 1})"
                if source not in sources:
                    sources.append(source)
            
            logger.info(f"Generated response for query: {request.message[:50]}...")
            
            return ChatResponse(
                response=response_text,
                sources=sources,
                session_id=session_id
            )
            
        except Exception as e:
            logger.error(f"Error processing chat request: {str(e)}")
            raise Exception(f"Chat processing failed: {str(e)}")
    
    def get_collection_stats(self) -> Dict:
        """Get statistics about the document collection."""
        try:
            return self.vector_store.get_collection_stats()
        except Exception as e:
            logger.error(f"Error getting collection stats: {str(e)}")
            return {"total_documents": 0, "error": str(e)}
    
    def health_check(self) -> Dict:
        """Perform health check on all components."""
        return {
            "milvus_connected": self.vector_store.health_check(),
            "perplexity_configured": self.llm_service.is_configured(),
            "upload_dir_exists": os.path.exists(settings.UPLOAD_DIR)
        }
    
    def clear_collection(self) -> bool:
        """Clear all documents from the collection (keeps the collection structure)."""
        try:
            return self.vector_store.clear_collection_contents()
        except Exception as e:
            logger.error(f"Error clearing collection: {str(e)}")
            return False
    
    def reset_collection(self) -> bool:
        """Reset/recreate the collection if it doesn't exist."""
        try:
            self.vector_store._ensure_collection()
            return True
        except Exception as e:
            logger.error(f"Error resetting collection: {str(e)}")
            return False
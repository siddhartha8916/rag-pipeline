from typing import List, Dict, Tuple
from pymilvus import Collection, connections, FieldSchema, CollectionSchema, DataType, utility
from app.config import settings
from app.models.schemas import DocumentChunk
import logging
import json

logger = logging.getLogger(__name__)

class MilvusVectorStore:
    def __init__(self):
        self.collection_name = settings.COLLECTION_NAME
        self.embedding_dim = settings.EMBEDDING_DIM
        self.collection = None
        self._connect()
        self._ensure_collection()
    
    def _connect(self):
        """Connect to Milvus server."""
        try:
            connections.connect(
                alias="default",
                host=settings.MILVUS_HOST,
                port=settings.MILVUS_PORT
            )
            logger.info(f"Connected to Milvus at {settings.MILVUS_HOST}:{settings.MILVUS_PORT}")
        except Exception as e:
            logger.error(f"Failed to connect to Milvus: {str(e)}")
            raise Exception(f"Milvus connection failed: {str(e)}")
    
    def _create_collection_schema(self):
        """Create the collection schema for document embeddings."""
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=36, is_primary=True),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.embedding_dim),
            FieldSchema(name="metadata", dtype=DataType.VARCHAR, max_length=2048)
        ]
        
        schema = CollectionSchema(
            fields=fields,
            description="Document embeddings for RAG pipeline"
        )
        return schema
    
    def _ensure_collection(self):
        """Ensure the collection exists, create if it doesn't."""
        try:
            if utility.has_collection(self.collection_name):
                self.collection = Collection(self.collection_name)
                logger.info(f"Collection '{self.collection_name}' already exists")
            else:
                schema = self._create_collection_schema()
                self.collection = Collection(
                    name=self.collection_name,
                    schema=schema
                )
                logger.info(f"Created new collection '{self.collection_name}'")
            
            # Create index for vector field
            self._create_index()
            
        except Exception as e:
            logger.error(f"Error ensuring collection: {str(e)}")
            raise Exception(f"Collection setup failed: {str(e)}")
    
    def _create_index(self):
        """Create index for the embedding field."""
        try:
            index_params = {
                "metric_type": "L2",
                "index_type": "IVF_FLAT",
                "params": {"nlist": 128}
            }
            
            if not self.collection.has_index():
                self.collection.create_index(
                    field_name="embedding",
                    index_params=index_params
                )
                logger.info("Created index for embedding field")
            
            # Load collection into memory
            self.collection.load()
            
        except Exception as e:
            logger.error(f"Error creating index: {str(e)}")
            # Continue without index for now
            pass
    
    def insert_documents(self, documents: List[DocumentChunk]) -> bool:
        """Insert document chunks into the vector store."""
        try:
            if not documents:
                return True
            
            # Prepare data for insertion
            ids = [doc.id for doc in documents]
            texts = [doc.text for doc in documents]
            embeddings = [doc.embedding for doc in documents]
            metadata = [json.dumps(doc.metadata) for doc in documents]
            
            # Insert data
            entities = [ids, texts, embeddings, metadata]
            insert_result = self.collection.insert(entities)
            
            # Flush to ensure data is written
            self.collection.flush()
            
            logger.info(f"Inserted {len(documents)} documents into Milvus")
            return True
            
        except Exception as e:
            logger.error(f"Error inserting documents: {str(e)}")
            raise Exception(f"Failed to insert documents: {str(e)}")
    
    def search_similar_documents(self, query_embedding: List[float], top_k: int = 5) -> List[Dict]:
        """Search for similar documents using vector similarity."""
        try:
            # Check if collection exists, if not recreate it
            if not utility.has_collection(self.collection_name):
                logger.warning(f"Collection '{self.collection_name}' not found. Creating new collection.")
                self._ensure_collection()
                return []  # Return empty list since no documents exist yet
            
            # Ensure collection object exists
            if not self.collection:
                self.collection = Collection(self.collection_name)
            
            # Check if collection has any documents
            try:
                num_entities = self.collection.num_entities
                if num_entities == 0:
                    logger.info("Collection is empty, returning no results")
                    return []
            except Exception as entity_error:
                logger.warning(f"Could not get entity count: {str(entity_error)}")
                # Continue with search attempt
            
            # Ensure collection is loaded
            try:
                self.collection.load()
            except Exception as load_error:
                logger.warning(f"Collection load warning: {str(load_error)}")
                # Continue with search attempt
            
            search_params = {
                "metric_type": "L2",
                "params": {"nprobe": 10}
            }
            
            results = self.collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                output_fields=["text", "metadata"]
            )
            
            similar_docs = []
            for hits in results:
                for hit in hits:
                    similar_docs.append({
                        "id": hit.id,
                        "text": hit.entity.get("text"),
                        "metadata": json.loads(hit.entity.get("metadata", "{}")),
                        "score": hit.score
                    })
            
            logger.info(f"Found {len(similar_docs)} similar documents")
            return similar_docs
            
        except Exception as e:
            logger.error(f"Error searching documents: {str(e)}")
            # If search fails, try to ensure collection exists and return empty results
            try:
                self._ensure_collection()
                return []
            except:
                raise Exception(f"Search failed and collection recreation failed: {str(e)}")
    
    def get_collection_stats(self) -> Dict:
        """Get statistics about the collection."""
        try:
            # Check if collection exists, if not recreate it
            if not utility.has_collection(self.collection_name):
                logger.warning(f"Collection '{self.collection_name}' not found. Creating new collection.")
                self._ensure_collection()
                return {"total_documents": 0, "collection_name": self.collection_name}
            
            # Ensure collection object exists
            if not self.collection:
                self.collection = Collection(self.collection_name)
            
            stats = self.collection.num_entities
            return {
                "total_documents": stats,
                "collection_name": self.collection_name
            }
        except Exception as e:
            logger.error(f"Error getting collection stats: {str(e)}")
            # Try to recreate collection if there's an error
            try:
                self._ensure_collection()
                return {"total_documents": 0, "collection_name": self.collection_name}
            except:
                return {"total_documents": 0, "collection_name": self.collection_name}
    
    def clear_collection_contents(self):
        """Clear all contents from the collection without deleting the collection itself."""
        try:
            # Check if collection exists, if not recreate it
            if not utility.has_collection(self.collection_name):
                logger.warning(f"Collection '{self.collection_name}' not found. Creating new collection.")
                self._ensure_collection()
                return True
            
            # Ensure collection object exists
            if not self.collection:
                self.collection = Collection(self.collection_name)
            
            # Get all entities and delete them
            # Since we can't delete all at once easily in Milvus, we'll drop and recreate
            utility.drop_collection(self.collection_name)
            logger.info(f"Dropped collection '{self.collection_name}' to clear contents")
            
            # Recreate the collection
            self._ensure_collection()
            logger.info(f"Recreated empty collection '{self.collection_name}'")
            
            return True
        except Exception as e:
            logger.error(f"Error clearing collection contents: {str(e)}")
            # If clearing fails, try to ensure collection exists
            try:
                self._ensure_collection()
            except:
                pass
            raise Exception(f"Failed to clear collection contents: {str(e)}")
    
    def delete_collection(self):
        """Delete the entire collection (use with caution)."""
        try:
            if utility.has_collection(self.collection_name):
                utility.drop_collection(self.collection_name)
                self.collection = None
                logger.info(f"Deleted collection '{self.collection_name}'")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting collection: {str(e)}")
            raise Exception(f"Failed to delete collection: {str(e)}")
    
    def health_check(self) -> bool:
        """Check if Milvus connection is healthy."""
        try:
            # Check if we can list collections (basic connectivity test)
            utility.list_collections()
            
            # Ensure our collection exists
            if not utility.has_collection(self.collection_name):
                logger.info(f"Collection '{self.collection_name}' not found during health check. Creating it.")
                self._ensure_collection()
            
            return True
        except Exception as e:
            logger.error(f"Milvus health check failed: {str(e)}")
            return False
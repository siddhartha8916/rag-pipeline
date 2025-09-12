import httpx
from typing import List, Dict, Optional
from app.config import settings
import logging
import json

logger = logging.getLogger(__name__)

class PerplexityLLM:
    def __init__(self):
        self.api_key = settings.PERPLEXITY_API_KEY
        self.api_url = settings.PERPLEXITY_API_URL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        if not self.api_key:
            logger.warning("Perplexity API key not found in environment variables")
    
    def _create_rag_prompt(self, user_query: str, context_documents: List[Dict]) -> str:
        """Create a RAG prompt with context and user query."""
        
        # Build context from retrieved documents
        context_parts = []
        for i, doc in enumerate(context_documents, 1):
            context_parts.append(f"Document {i}:\n{doc['text']}\n")
        
        context = "\n".join(context_parts)
        
        prompt = f"""You are a helpful AI assistant that answers questions based on the provided context documents. 
Use the information from the context to provide accurate and relevant answers. If the context doesn't contain 
enough information to answer the question completely, please say so.

Context Documents:
{context}

User Question: {user_query}

Please provide a comprehensive answer based on the context above. If you reference specific information, 
try to indicate which document it came from."""

        return prompt
    
    async def generate_response(
        self, 
        user_query: str, 
        context_documents: List[Dict],
        model: str = "sonar",
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> str:
        """Generate a response using Perplexity API with RAG context."""
        
        try:
            if not self.api_key:
                raise Exception("Perplexity API key not configured")
            
            # Create the RAG prompt
            rag_prompt = self._create_rag_prompt(user_query, context_documents)
            
            # Prepare the request payload
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": rag_prompt
                    }
                ],
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": False
            }
            
            # Make the API request
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload
                )
                
                if response.status_code != 200:
                    logger.error(f"Perplexity API error: {response.status_code} - {response.text}")
                    raise Exception(f"Perplexity API error: {response.status_code}")
                
                result = response.json()
                
                # Extract the generated text
                if "choices" in result and len(result["choices"]) > 0:
                    generated_text = result["choices"][0]["message"]["content"]
                    logger.info("Successfully generated response from Perplexity")
                    return generated_text
                else:
                    logger.error(f"Unexpected response format: {result}")
                    raise Exception("Unexpected response format from Perplexity API")
                    
        except httpx.TimeoutException:
            logger.error("Timeout when calling Perplexity API")
            raise Exception("Request to Perplexity API timed out")
        except httpx.HTTPError as e:
            logger.error(f"HTTP error when calling Perplexity API: {str(e)}")
            raise Exception(f"HTTP error: {str(e)}")
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            raise Exception(f"Failed to generate response: {str(e)}")
    
    async def generate_simple_response(
        self, 
        message: str,
        model: str = "sonar",
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> str:
        """Generate a simple response without RAG context."""
        
        try:
            if not self.api_key:
                raise Exception("Perplexity API key not configured")
            
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": message
                    }
                ],
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": False
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload
                )
                
                if response.status_code != 200:
                    logger.error(f"Perplexity API error: {response.status_code} - {response.text}")
                    raise Exception(f"Perplexity API error: {response.status_code}")
                
                result = response.json()
                
                if "choices" in result and len(result["choices"]) > 0:
                    generated_text = result["choices"][0]["message"]["content"]
                    return generated_text
                else:
                    raise Exception("Unexpected response format from Perplexity API")
                    
        except Exception as e:
            logger.error(f"Error generating simple response: {str(e)}")
            raise Exception(f"Failed to generate response: {str(e)}")
    
    def is_configured(self) -> bool:
        """Check if the Perplexity API is properly configured."""
        return bool(self.api_key)
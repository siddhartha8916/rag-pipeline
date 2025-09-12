#!/usr/bin/env python3
"""
Utility script to inspect and verify PDF contents stored in Milvus.
This helps you understand what chunks were created from your PDF files.
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.services.vector_store import MilvusVectorStore
from app.services.pdf_processor import PDFProcessor
from app.config import settings
import json

def inspect_collection():
    """Inspect what's currently in the Milvus collection."""
    print("🔍 Inspecting Milvus Collection")
    print("=" * 50)
    
    try:
        vector_store = MilvusVectorStore()
        stats = vector_store.get_collection_stats()
        
        print(f"Collection Name: {stats.get('collection_name', 'N/A')}")
        print(f"Total Documents: {stats.get('total_documents', 0)}")
        
    except Exception as e:
        print(f"❌ Error inspecting collection: {e}")

def search_similar_content(query: str, top_k: int = 10):
    """Search for content similar to a query and show the results."""
    print(f"\n🔎 Searching for: '{query}'")
    print("=" * 50)
    
    try:
        vector_store = MilvusVectorStore()
        pdf_processor = PDFProcessor()
        
        # Create query embedding
        query_embedding = pdf_processor.create_query_embedding(query)
        
        # Search for similar documents
        results = vector_store.search_similar_documents(query_embedding, top_k=top_k)
        
        if not results:
            print("❌ No similar documents found.")
            return
        
        print(f"✅ Found {len(results)} similar chunks:")
        print()
        
        for i, doc in enumerate(results, 1):
            metadata = doc.get('metadata', {})
            text = doc.get('text', '')[:200] + "..." if len(doc.get('text', '')) > 200 else doc.get('text', '')
            score = doc.get('score', 'N/A')
            
            print(f"📄 Result {i}:")
            print(f"   File: {metadata.get('filename', 'Unknown')}")
            print(f"   Chunk: {metadata.get('chunk_index', 0) + 1} of {metadata.get('total_chunks', 'N/A')}")
            print(f"   Score: {score}")
            print(f"   Text: {text}")
            print()
            
    except Exception as e:
        print(f"❌ Error searching: {e}")

def analyze_pdf_file(file_path: str):
    """Analyze a PDF file to see what text would be extracted."""
    print(f"\n📖 Analyzing PDF: {file_path}")
    print("=" * 50)
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return
    
    try:
        pdf_processor = PDFProcessor()
        
        # Extract text
        print("Extracting text...")
        text = pdf_processor.extract_text_from_pdf(file_path)
        
        print(f"✅ Extracted {len(text)} characters")
        print(f"First 500 characters:")
        print("-" * 30)
        print(text[:500] + "..." if len(text) > 500 else text)
        print("-" * 30)
        
        # Create chunks
        print("\nCreating chunks...")
        chunks = pdf_processor.chunk_text(text)
        
        print(f"✅ Created {len(chunks)} chunks")
        print(f"Chunk size: {settings.CHUNK_SIZE}")
        print(f"Chunk overlap: {settings.CHUNK_OVERLAP}")
        
        # Show first few chunks
        print("\nFirst 3 chunks:")
        for i, chunk in enumerate(chunks[:3], 1):
            print(f"\n📄 Chunk {i}:")
            print(f"Length: {len(chunk)} characters")
            print(f"Content: {chunk[:200]}..." if len(chunk) > 200 else chunk)
        
    except Exception as e:
        print(f"❌ Error analyzing PDF: {e}")

def main():
    print("🔧 RAG Pipeline Content Inspector")
    print("=" * 50)
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python inspect_content.py collection              # Inspect collection stats")
        print("  python inspect_content.py search 'your query'     # Search for content")
        print("  python inspect_content.py analyze path/to/file.pdf # Analyze PDF file")
        return
    
    command = sys.argv[1].lower()
    
    if command == "collection":
        inspect_collection()
    
    elif command == "search":
        if len(sys.argv) < 3:
            print("❌ Please provide a search query")
            return
        query = " ".join(sys.argv[2:])
        search_similar_content(query)
    
    elif command == "analyze":
        if len(sys.argv) < 3:
            print("❌ Please provide a PDF file path")
            return
        file_path = sys.argv[2]
        analyze_pdf_file(file_path)
    
    else:
        print(f"❌ Unknown command: {command}")

if __name__ == "__main__":
    main()
# RAG Pipeline with FastAPI, Milvus, and Perplexity

A production-ready FastAPI application implementing RAG (Retrieval-Augmented Generation) architecture using Milvus as the vector database and Perplexity as the LLM service.

## Features

- **PDF Document Processing**: Upload and process PDF documents into vector embeddings
- **Vector Search**: Efficient similarity search using Milvus vector database
- **RAG Chat**: Chat interface that uses retrieved document context to generate responses
- **Perplexity Integration**: Uses Perplexity API for high-quality response generation
- **REST API**: Clean and documented REST API endpoints
- **Docker Support**: Complete Docker Compose setup for Milvus

## Architecture

1. **Document Upload**: PDF files are uploaded and processed
2. **Text Extraction**: Text is extracted from PDFs using PyPDF2
3. **Chunking**: Documents are split into manageable chunks with overlap
4. **Embedding Generation**: Text chunks are converted to embeddings using Sentence Transformers
5. **Vector Storage**: Embeddings are stored in Milvus vector database
6. **Query Processing**: User queries are converted to embeddings
7. **Similarity Search**: Similar document chunks are retrieved from Milvus
8. **Response Generation**: Retrieved context is used with Perplexity API to generate responses

## Prerequisites

- Python 3.8+
- Docker and Docker Compose
- Perplexity API key

## Setup

You can run this application in two ways: **Docker (Recommended)** or **Local Development**.

### Option 1: Docker Setup (Recommended)

This is the easiest way to get started. Everything runs in containers with proper networking.

#### 1. Prerequisites
- Docker and Docker Compose installed
- Perplexity API key

#### 2. Configure Environment
```bash
# Copy the Docker environment template
copy .env.docker .env.docker

# Edit .env.docker and add your Perplexity API key
# PERPLEXITY_API_KEY=your_actual_perplexity_api_key_here
```

#### 3. Start Everything with Docker
```bash
# Windows
docker-start.bat

# Linux/macOS
chmod +x docker-start.sh
./docker-start.sh
```

Or manually:
```bash
# Build and start all services
docker-compose --env-file .env.docker up -d --build

# Check status
docker-compose ps
```

#### 4. Access the Application
- **API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### Option 2: Local Development Setup

For development or if you prefer running locally:

#### 1. Clone and Navigate
```bash
cd d:\Learnings\rag-pipeline
```

#### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

#### 3. Configure Environment
```bash
copy .env.template .env
```

Edit `.env` and add your Perplexity API key:
```env
PERPLEXITY_API_KEY=your_actual_perplexity_api_key_here
```

#### 4. Start Milvus with Docker Compose
```bash
docker-compose up -d etcd minio milvus
```

Wait for all services to be healthy (usually 1-2 minutes):
```bash
docker-compose ps
```

#### 5. Start the FastAPI Application
```bash
cd app
python main.py
```

Or using uvicorn directly:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## API Usage

The API will be available at `http://localhost:8000`

### API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Endpoints

#### 1. Health Check
```bash
GET /health
```

#### 2. Upload PDF Document
```bash
POST /documents/upload
Content-Type: multipart/form-data

# Upload a PDF file
curl -X POST "http://localhost:8000/documents/upload" -H "accept: application/json" -H "Content-Type: multipart/form-data" -F "file=@your_document.pdf"
```

#### 3. Chat with RAG
```bash
POST /documents/chat
Content-Type: application/json

{
  "message": "What is the main topic of the uploaded document?",
  "session_id": "optional-session-id"
}
```

#### 4. Get Collection Statistics
```bash
GET /documents/stats
```

#### 5. Clear All Documents
```bash
DELETE /documents/clear
```

## Example Usage

### 1. Upload a Document

```python
import requests

files = {'file': open('example.pdf', 'rb')}
response = requests.post('http://localhost:8000/documents/upload', files=files)
print(response.json())
```

### 2. Chat with the System

```python
import requests

chat_request = {
    "message": "What are the key findings in the document?",
    "session_id": "my-session"
}

response = requests.post('http://localhost:8000/documents/chat', json=chat_request)
print(response.json())
```

## Docker Commands

### Essential Docker Commands

```bash
# Start all services
docker-compose --env-file .env.docker up -d

# View logs
docker-compose logs -f rag-app
docker-compose logs -f milvus

# Check service status
docker-compose ps

# Stop all services
docker-compose down

# Stop and remove all data (WARNING: Deletes uploaded documents)
docker-compose down -v

# Rebuild application container
docker-compose build --no-cache rag-app

# Access container shell
docker-compose exec rag-app bash
```

### Docker Architecture

The Docker setup includes:
- **rag-app**: FastAPI application container (Linux-based)
- **milvus**: Vector database
- **etcd**: Milvus metadata storage
- **minio**: Milvus object storage
- **Custom network**: `rag-network` for inter-container communication
- **Persistent volumes**: For data persistence

## Configuration

### For Docker Setup (`.env.docker`):
- `PERPLEXITY_API_KEY`: Your Perplexity API key (required)
- `MILVUS_HOST`: Milvus container name (set to `milvus`)
- `MILVUS_PORT`: Milvus port (default: 19530)

### For Local Setup (`.env`):
- `PERPLEXITY_API_KEY`: Your Perplexity API key (required)
- `MILVUS_HOST`: Milvus server host (default: localhost)
- `MILVUS_PORT`: Milvus server port (default: 19530)

### Common Settings:
- `EMBEDDING_MODEL`: Sentence transformer model (default: all-MiniLM-L6-v2)
- `CHUNK_SIZE`: Text chunk size (default: 1000)
- `CHUNK_OVERLAP`: Overlap between chunks (default: 200)
- `MAX_FILE_SIZE`: Maximum PDF file size in bytes (default: 10MB)

## Project Structure

```
rag-pipeline/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── config.py              # Configuration settings
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py         # Pydantic models
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── documents.py       # Document endpoints
│   │   └── health.py          # Health endpoints
│   └── services/
│       ├── __init__.py
│       ├── pdf_processor.py   # PDF processing and embeddings
│       ├── vector_store.py    # Milvus vector database
│       ├── llm_service.py     # Perplexity LLM integration
│       └── rag_pipeline.py    # Main RAG logic
├── uploads/                   # Directory for uploaded files
├── docker-compose.yml         # Milvus stack
├── requirements.txt           # Python dependencies
├── .env                      # Environment variables
├── .env.template             # Environment template
└── README.md                 # This file
```

## Troubleshooting

### Docker Issues

1. **Services not starting**:
   ```bash
   # Check Docker daemon is running
   docker --version
   
   # Check logs for specific service
   docker-compose logs rag-app
   docker-compose logs milvus
   
   # Restart all services
   docker-compose down
   docker-compose --env-file .env.docker up -d
   ```

2. **Port conflicts**:
   ```bash
   # Check what's using the ports
   netstat -an | findstr "8000\|19530\|9000"
   
   # Stop conflicting services or change ports in docker-compose.yml
   ```

3. **Build failures**:
   ```bash
   # Clean build
   docker-compose build --no-cache
   
   # Remove old images
   docker system prune -a
   ```

### Milvus Connection Issues

1. Check if Docker containers are running:
   ```bash
   docker-compose ps
   ```

2. View container logs:
   ```bash
   docker-compose logs milvus
   ```

3. Restart Milvus stack:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

### API Key Issues

Ensure your Perplexity API key is correctly set:
- For Docker: In `.env.docker` file
- For Local: In `.env` file

### Memory Issues

If you encounter memory issues with embeddings:
- Reduce `CHUNK_SIZE` in the configuration
- Process smaller PDF files
- Consider using a smaller embedding model
- Increase Docker memory limits if needed

### Container Access

To debug inside containers:
```bash
# Access FastAPI app container
docker-compose exec rag-app bash

# Check app logs
docker-compose logs -f rag-app

# Check Python packages
docker-compose exec rag-app pip list
```

## Development

### Running in Development Mode

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Adding New Features

1. Add new endpoints in `app/routers/`
2. Implement business logic in `app/services/`
3. Define data models in `app/models/schemas.py`
4. Update configuration in `app/config.py` if needed

## Production Deployment

For production deployment:

1. Set proper CORS origins in `main.py`
2. Use environment variables for all sensitive configuration
3. Set up proper logging and monitoring
4. Use a production WSGI server like Gunicorn
5. Set up SSL/TLS certificates
6. Configure Milvus for production use

## License

This project is licensed under the MIT License.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the API documentation at `/docs`
3. Check Milvus and Perplexity documentation
4. Open an issue in the repository
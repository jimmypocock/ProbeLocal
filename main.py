#!/usr/bin/env python3
"""
Main API server for PDF Q&A application optimized for M3 MacBook Air
"""

import os
import shutil
import logging
import json
import signal
import sys
import asyncio
from pathlib import Path
from typing import Dict, Any
from contextlib import asynccontextmanager

# Set offline mode for HuggingFace to prevent HTTP 429 errors
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"

from fastapi import FastAPI, HTTPException, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from src.config import Config
from src.document_processor import DocumentProcessor
from src.qa_chain_unified import UnifiedQAChain
from src.performance.request_queue import request_queue, get_request_result
from src.model_warmup import start_background_warmup
from src.error_messages import ErrorMessages
from src.security import (
    sanitize_filename, create_safe_file_path, sanitize_query_string,
    validate_model_name, validate_parameter_bounds, sanitize_error_message,
    is_safe_url
)
from src.async_io import write_file_async, delete_file_async, load_json_async, save_json_async, file_exists_async, delete_directory_async
from src.vector_store_manager import VectorStoreManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize configuration
config = Config()
config.create_directories()

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Global instances
doc_processor = None
unified_qa_chain = None
vector_store_manager = None

class QuestionRequest(BaseModel):
    model_config = {"protected_namespaces": ()}
    
    question: str
    document_id: str
    max_results: int = 5
    model_name: str = None  # Optional model override
    temperature: float = 0.7  # Optional temperature override
    use_web_search: bool = False  # Enable web search
    stream: bool = False  # Enable streaming response

class URLProcessRequest(BaseModel):
    model_config = {"protected_namespaces": ()}
    
    url: str
    model: str = "mistral"
    chunk_size: int = 800
    temperature: float = 0.7

class UploadResponse(BaseModel):
    model_config = {"protected_namespaces": ()}
    
    document_id: str
    pages: int
    chunks: int
    processing_time: float
    message: str

class AnswerResponse(BaseModel):
    model_config = {"protected_namespaces": ()}
    
    answer: str
    sources: list
    document_id: str
    processing_time: float
    llm_model: str  # Changed to llm_model to avoid Pydantic namespace conflict

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global doc_processor, unified_qa_chain, vector_store_manager
    logger.info("Initializing PDF Q&A system...")
    
    try:
        # Initialize vector store manager
        vector_store_manager = VectorStoreManager(
            config.VECTOR_STORE_DIR,
            config.UPLOAD_DIR
        )
        
        # Delay initialization to avoid startup issues
        logger.info("System ready - components will be initialized on first use")
        
        # Start warming up models in the background
        logger.info("Starting background model warmup...")
        start_background_warmup()
        
        # Run initial cleanup
        logger.info("Running initial vector store cleanup...")
        cleanup_stats = vector_store_manager.cleanup_old_stores(force=True)
        if "removed_by_age" in cleanup_stats:
            total_removed = len(cleanup_stats["removed_by_age"]) + len(cleanup_stats["removed_by_count"])
            if total_removed > 0:
                logger.info(f"Initial cleanup removed {total_removed} old vector stores")
        
    except Exception as e:
        logger.error(f"Failed to initialize system: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down PDF Q&A system...")
    
    # Clean up global instances
    global doc_processor, unified_qa_chain
    
    # Clean up document processor
    if doc_processor is not None:
        try:
            logger.info("Cleaning up document processor...")
            # Clear embeddings cache if any
            if hasattr(doc_processor, 'embeddings'):
                del doc_processor.embeddings
            del doc_processor
            doc_processor = None
        except Exception as e:
            logger.error(f"Error cleaning up document processor: {e}")
    
    # Clean up direct QA chain
    if unified_qa_chain is not None:
        try:
            logger.info("Cleaning up direct QA chain...")
            # Clear any cached data
            if hasattr(unified_qa_chain, 'llm'):
                del unified_qa_chain.llm
            if hasattr(unified_qa_chain, 'embeddings'):
                del unified_qa_chain.embeddings
            if hasattr(unified_qa_chain, 'vector_store'):
                del unified_qa_chain.vector_store
            del unified_qa_chain
        except Exception as e:
            logger.error(f"Error cleaning up direct QA chain: {e}")
    
    unified_qa_chain = None
    
    # Force garbage collection
    import gc
    gc.collect()
    
    logger.info("Cleanup completed")

# Create FastAPI app
app = FastAPI(
    title="Greg API - AI Playground",
    description="100% Free, Local, and Private Document Question Answering. Supports PDF, TXT, CSV, Markdown, Word, Excel, and Image files.",
    version="1.1.0",
    lifespan=lifespan
)

# Add CORS middleware - Allow common Streamlit ports
streamlit_origins = [
    "http://localhost:2402",  # Greg's preferred port
    "http://localhost:8501",  # Streamlit default
    "http://localhost:8502",  # Common alternative
    "http://localhost:8503",  # Common alternative
] + [f"http://localhost:{port}" for port in range(2402, 2500)]  # Range for port search

app.add_middleware(
    CORSMiddleware,
    allow_origins=streamlit_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiter to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/")
async def root():
    return {
        "message": "Greg API - Your AI Playground",
        "status": "running",
        "supported_files": ["pdf", "txt", "csv", "md", "docx", "xlsx", "png", "jpg"],
        "endpoints": {
            "upload": "/upload",
            "ask": "/ask",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """Check system health and available memory"""
    try:
        import psutil
        memory = psutil.virtual_memory()
        
        return {
            "status": "healthy",
            "memory": {
                "available_gb": round(memory.available / (1024**3), 2),
                "percent_used": memory.percent,
                "total_gb": round(memory.total / (1024**3), 2)
            },
            "model": config.LOCAL_LLM_MODEL,
            "optimal_settings": config.get_optimal_settings()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}

def get_doc_processor():
    """Lazy initialization of document processor"""
    global doc_processor
    if doc_processor is None:
        logger.info("Initializing document processor...")
        doc_processor = DocumentProcessor()
    return doc_processor


def get_unified_qa_chain():
    """Lazy initialization of direct QA chain"""
    global unified_qa_chain
    if unified_qa_chain is None:
        logger.info("Initializing direct QA chain...")
        unified_qa_chain = UnifiedQAChain()
    return unified_qa_chain


@app.post("/process-url", response_model=UploadResponse)
@limiter.limit("10/minute")  # 10 URL fetches per minute per IP
async def process_url(request: Request, url_request: URLProcessRequest):
    """Process a URL by fetching and converting its content to a document"""
    
    # Validate URL
    if not is_safe_url(url_request.url):
        raise HTTPException(
            status_code=400,
            detail="Invalid URL. Please provide a valid HTTP or HTTPS URL."
        )
    
    try:
        logger.info(f"Processing URL: {url_request.url}")
        
        # Fetch and process URL content
        from src.web_search import WebSearcher
        searcher = WebSearcher()
        
        # Extract content from URL
        content = searcher.extract_content(url_request.url)
        if not content:
            raise HTTPException(status_code=400, detail="Could not extract content from URL")
        
        # Parse title from content or URL
        from urllib.parse import urlparse
        parsed_url = urlparse(url_request.url)
        title = f"Web: {parsed_url.netloc}"
        
        # Create a temporary file from the content with secure name
        import tempfile
        import uuid
        safe_filename = f"web_{uuid.uuid4().hex[:8]}.txt"
        safe_path = create_safe_file_path(safe_filename, config.UPLOAD_DIR)
        
        if not safe_path:
            raise HTTPException(status_code=500, detail="Could not create temporary file")
        
        try:
            # Write web content asynchronously
            web_content = f"# {title}\n\nSource: {url_request.url}\n\n{content}"
            await write_file_async(safe_path, web_content)
            
            # Process as a text document
            processor = get_doc_processor()
            doc_id, pages, chunks, processing_time = processor.process_file(
                str(safe_path),
                safe_filename,  # Use the actual filename with .txt extension
                chunk_size=url_request.chunk_size
            )
            
            # Clean up asynchronously
            await delete_file_async(safe_path)
            
            return UploadResponse(
                document_id=doc_id,
                pages=1,  # Web content is treated as single page
                chunks=chunks,
                processing_time=processing_time,
                message=f"Successfully processed web content from {parsed_url.netloc}"
            )
            
        except Exception as e:
            if safe_path and safe_path.exists():
                safe_path.unlink()
            raise e
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing URL: {e}")
        error_msg = ErrorMessages.get_specific_error(e, {'context': 'url_processing'})
        raise HTTPException(status_code=500, detail=error_msg)

@app.post("/web-search")
@limiter.limit("30/minute")  # 30 web searches per minute per IP
async def web_search(request: Request, question_request: QuestionRequest):
    """Search the web for information without requiring a document"""
    # Sanitize query string
    question = sanitize_query_string(question_request.question)
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    
    # Validate model name if provided
    if question_request.model_name and not validate_model_name(question_request.model_name):
        raise HTTPException(status_code=400, detail="Invalid model name")
    
    try:
        logger.info(f"Web search: {question}")
        
        # Use direct chain with simple streaming
        chain = get_unified_qa_chain()
        result = chain.answer_question(
            question=question,
            document_id="web_only",
            use_web=True,
            max_results=question_request.max_results or 5,
            model_name=question_request.model_name,
            temperature=question_request.temperature,
            streaming=True
        )
        
        return StreamingResponse(
            result['stream'],
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            }
        )
        
    except Exception as e:
        logger.error(f"Error in web search: {e}")
        error_msg = ErrorMessages.get_specific_error(e, {'context': 'web_search'})
        raise HTTPException(status_code=500, detail=error_msg)

@app.post("/ask", response_model=AnswerResponse)
@limiter.limit("60/minute")  # 60 questions per minute per IP
async def ask_question(request: Request, question_request: QuestionRequest):
    """Ask a question about a processed document"""
    
    # Sanitize query string
    question = sanitize_query_string(question_request.question)
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    
    # Validate model name if provided
    if question_request.model_name and not validate_model_name(question_request.model_name):
        raise HTTPException(status_code=400, detail="Invalid model name")
    
    # Validate and sanitize other parameters
    params = validate_parameter_bounds({
        'temperature': question_request.temperature,
        'max_results': question_request.max_results
    })
    temperature = params.get('temperature', question_request.temperature)
    max_results = params.get('max_results', question_request.max_results)
    
    try:
        logger.info(f"Question: {question} for document: {question_request.document_id}")
        
        # Call directly without asyncio timeout (causes issues in threads)
        return await _ask_question_impl(question, question_request, temperature, max_results)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing question: {e}", exc_info=True)
        context = {'model_name': question_request.model_name}
        error_msg = ErrorMessages.get_specific_error(e, context)
        raise HTTPException(status_code=500, detail=error_msg)

async def _ask_question_impl(question: str, question_request: QuestionRequest, temperature: float, max_results: int):
    """Implementation of ask question with timeout protection"""
    try:
        # Use direct chain with simple streaming
        chain = get_unified_qa_chain()
        
        # Create streaming generator
        result = chain.answer_question(
            question=question,
            document_id=question_request.document_id,
            use_web=question_request.use_web_search,
            max_results=max_results,
            model_name=question_request.model_name,
            temperature=temperature,
            streaming=True
        )
        
        # Return streaming response
        return StreamingResponse(
            result['stream'],
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",  # Disable proxy buffering
            }
        )
        
    except ValueError as e:
        error_msg = ErrorMessages.DOCUMENT_NOT_FOUND
        raise HTTPException(status_code=404, detail=error_msg)

@app.get("/documents")
async def list_documents():
    """List all processed documents"""
    try:
        # Call directly without asyncio timeout (causes issues in threads)
        return await _list_documents_impl()
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        error_msg = sanitize_error_message(e, show_details=False)
        raise HTTPException(status_code=500, detail=error_msg)

async def _list_documents_impl():
    """Implementation of list documents with timeout protection"""
    # Check for unified store first
    unified_metadata_path = config.VECTOR_STORE_DIR / "unified_store.metadata"
    if unified_metadata_path.exists():
        # Load unified store metadata
        unified_metadata = await load_json_async(unified_metadata_path)
        
        # Convert unified store format to document list format
        documents = []
        for doc in unified_metadata.get('documents', []):
            documents.append({
                "document_id": "unified",
                "filename": doc['filename'],
                "pages": doc['pages'],
                "chunks": doc['chunks'],
                "upload_date": unified_metadata['creation_date'],
                "model_used": unified_metadata['model_used']
            })
        
        return {"documents": documents}
    
    # Fallback to individual document stores
    documents = []
    
    # Get all metadata files and process them concurrently
    from src.async_io import process_files_batch_async
    
    async def load_metadata(metadata_file):
        # Skip unified store metadata
        if metadata_file.name == "unified_store.metadata":
            return None
            
        try:
            # Try JSON first (new format)
            metadata = await load_json_async(metadata_file)
            return {
                "document_id": metadata['document_id'],
                "filename": metadata['filename'],
                "pages": metadata['pages'],
                "chunks": metadata.get('chunks', 'N/A'),
                "upload_date": metadata['upload_date'],  # Already ISO format
                "model_used": metadata['model_used']
            }
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Fallback to pickle for old files
            import pickle
            from src.async_io import read_file_async
            content = await read_file_async(metadata_file, mode='rb')
            metadata = pickle.loads(content)
            return {
                "document_id": metadata['document_id'],
                "filename": metadata['filename'],
                "pages": metadata['pages'],
                "chunks": metadata.get('chunks', 'N/A'),
                "upload_date": metadata['upload_date'].isoformat(),
                "model_used": metadata['model_used']
            }
    
    # Process all metadata files concurrently
    metadata_files = list(config.VECTOR_STORE_DIR.glob("*.metadata"))
    results = await process_files_batch_async(metadata_files, load_metadata, max_concurrent=10)
    documents = [doc for doc in results if doc is not None]
    
    return {"documents": documents}

@app.post("/ask-streaming")
@limiter.limit("30/minute")  # Lower limit for streaming
async def ask_question_streaming(request: Request, question_request: QuestionRequest):
    """Ask a question and get a streaming response (better for long answers)"""
    
    # Validate and sanitize inputs
    question = sanitize_query_string(question_request.question)
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    
    if question_request.model_name and not validate_model_name(question_request.model_name):
        raise HTTPException(status_code=400, detail="Invalid model name")
    
    # Validate parameters
    params = validate_parameter_bounds({
        'max_results': question_request.max_results or 3,
        'temperature': question_request.temperature or 0.7
    })
    max_results = params.get('max_results', 3)
    
    try:
        # Use direct chain with simple streaming
        chain = get_unified_qa_chain()
        result = chain.answer_question(
            question=question,
            document_id=question_request.document_id,
            use_web=question_request.use_web_search or False,
            max_results=max_results,
            model_name=question_request.model_name,
            temperature=question_request.temperature or 0.7,
            streaming=True
        )
        
        return StreamingResponse(
            result['stream'],
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive"
            }
        )
        
    except Exception as e:
        logger.error(f"Error in streaming Q&A: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/storage-stats")
async def get_storage_stats():
    """Get storage statistics for vector stores"""
    try:
        if not vector_store_manager:
            raise HTTPException(status_code=503, detail="Vector store manager not initialized")
        
        stats = vector_store_manager.get_storage_stats()
        
        # Add storage path
        stats["storage_path"] = str(config.VECTOR_STORE_DIR.absolute())
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting storage stats: {e}")
        error_msg = sanitize_error_message(e, show_details=False)
        raise HTTPException(status_code=500, detail=error_msg)

@app.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """Delete a specific document"""
    try:
        deleted_something = False
        
        # Delete vector store (it's a directory)
        vector_store_path = config.VECTOR_STORE_DIR / f"{document_id}.faiss"
        if await file_exists_async(vector_store_path) and vector_store_path.is_dir():
            await delete_directory_async(vector_store_path)
            deleted_something = True
            logger.info(f"Deleted vector store for document: {document_id}")
        
        # Delete metadata
        metadata_path = config.VECTOR_STORE_DIR / f"{document_id}.metadata"
        if await file_exists_async(metadata_path):
            await delete_file_async(metadata_path)
            deleted_something = True
            logger.info(f"Deleted metadata for document: {document_id}")
        
        if not deleted_something:
            raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
        
        logger.info(f"Successfully deleted document: {document_id}")
        return {"message": f"Document {document_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {e}", exc_info=True)
        error_msg = sanitize_error_message(e, show_details=False)
        raise HTTPException(status_code=500, detail=error_msg)

@app.post("/clear-all")
async def clear_all_documents():
    """Clear all documents and reset the system"""
    try:
        # Clear all files in vector store directory
        for file in config.VECTOR_STORE_DIR.glob("*"):
            if file.is_file():
                os.remove(file)
            elif file.is_dir():
                shutil.rmtree(file)
        
        # Clear uploads directory
        for file in config.UPLOAD_DIR.glob("*"):
            if file.is_file():
                os.remove(file)
        
        logger.info("Cleared all documents")
        return {"message": "All documents cleared successfully"}
        
    except Exception as e:
        logger.error(f"Error clearing documents: {e}")
        error_msg = sanitize_error_message(e, show_details=False)
        raise HTTPException(status_code=500, detail=error_msg)

@app.post("/cleanup-stores")
async def cleanup_vector_stores():
    """Manually trigger vector store cleanup"""
    try:
        if not vector_store_manager:
            raise HTTPException(status_code=503, detail="Vector store manager not initialized")
        
        # Force cleanup
        cleanup_stats = vector_store_manager.cleanup_old_stores(force=True)
        
        # Clean orphaned upload files too
        orphaned_cleaned = vector_store_manager.cleanup_orphaned_files()
        cleanup_stats["orphaned_files_cleaned"] = orphaned_cleaned
        
        return cleanup_stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        error_msg = sanitize_error_message(e, show_details=False)
        raise HTTPException(status_code=500, detail=error_msg)

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    sys.exit(0)

def start_server():
    """Start the FastAPI server"""
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Get port from environment variable or default to 8080
    port = int(os.environ.get('GREG_API_PORT', 8080))
    logger.info(f"Starting server on port {port}")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
        # Disable multiprocessing reload to avoid semaphore leaks
        reload=False,
        workers=1,
        # Let uvicorn handle signals properly
        loop="asyncio",
        access_log=False  # Reduce log noise
    )

if __name__ == "__main__":
    # Set multiprocessing start method to avoid semaphore leaks on macOS
    import multiprocessing
    try:
        multiprocessing.set_start_method('spawn', force=True)
    except RuntimeError:
        pass  # Already set
    
    start_server()
#!/usr/bin/env python3
"""
Main API server for PDF Q&A application optimized for M3 MacBook Air
"""

import os
import shutil
import logging
from pathlib import Path
from typing import Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from src.config import Config
from src.document_processor import DocumentProcessor
from src.qa_chain import QAChain

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize configuration
config = Config()
config.create_directories()

# Global instances
doc_processor = None
qa_chain = None

class QuestionRequest(BaseModel):
    question: str
    document_id: str
    max_results: int = 5
    model_name: str = None  # Optional model override

class UploadResponse(BaseModel):
    document_id: str
    pages: int
    chunks: int
    processing_time: float
    message: str

class AnswerResponse(BaseModel):
    answer: str
    sources: list
    document_id: str
    processing_time: float
    llm_model: str  # Changed to llm_model to avoid Pydantic namespace conflict

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global doc_processor, qa_chain
    logger.info("Initializing PDF Q&A system...")
    
    try:
        # Delay initialization to avoid startup issues
        logger.info("System ready - components will be initialized on first use")
    except Exception as e:
        logger.error(f"Failed to initialize system: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down PDF Q&A system...")

# Create FastAPI app
app = FastAPI(
    title="PDF Q&A API - M3 Optimized",
    description="100% Free, Local, and Private PDF Question Answering",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],  # Streamlit default
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "PDF Q&A API - M3 MacBook Air Optimized",
        "status": "running",
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

def get_qa_chain():
    """Lazy initialization of QA chain"""
    global qa_chain
    if qa_chain is None:
        logger.info("Initializing QA chain...")
        qa_chain = QAChain()
    return qa_chain

@app.post("/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """Upload and process a PDF file"""
    
    # Validate file
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Check file size
    contents = await file.read()
    file_size = len(contents)
    
    if file_size > config.MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {config.MAX_FILE_SIZE_MB}MB"
        )
    
    # Save file temporarily
    temp_path = config.UPLOAD_DIR / file.filename
    
    try:
        with open(temp_path, 'wb') as f:
            f.write(contents)
        
        logger.info(f"Processing PDF: {file.filename}")
        
        # Process the PDF with lazy initialization
        processor = get_doc_processor()
        doc_id, pages, chunks, processing_time = processor.process_pdf(
            str(temp_path),
            file.filename
        )
        
        # Clean up temporary file
        os.remove(temp_path)
        
        return UploadResponse(
            document_id=doc_id,
            pages=pages,
            chunks=chunks,
            processing_time=processing_time,
            message=f"Successfully processed {pages} pages into {chunks} chunks"
        )
        
    except Exception as e:
        # Clean up on error
        if temp_path.exists():
            os.remove(temp_path)
        
        logger.error(f"Error processing PDF: {e}", exc_info=True)
        # Return more detailed error information
        error_msg = str(e)
        if "Ollama" in error_msg:
            error_msg = "Ollama service error. Please ensure 'ollama serve' is running and you have pulled a model with 'ollama pull mistral'"
        raise HTTPException(status_code=500, detail=error_msg)

@app.post("/ask", response_model=AnswerResponse)
async def ask_question(request: QuestionRequest):
    """Ask a question about a processed document"""
    
    try:
        logger.info(f"Question: {request.question} for document: {request.document_id}")
        
        # Get answer with lazy initialization
        chain = get_qa_chain()
        result = chain.answer_question(
            question=request.question,
            document_id=request.document_id,
            max_results=request.max_results,
            model_name=request.model_name
        )
        
        return AnswerResponse(**result)
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error answering question: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documents")
async def list_documents():
    """List all processed documents"""
    try:
        documents = []
        
        # Get all metadata files
        for metadata_file in config.VECTOR_STORE_DIR.glob("*.metadata"):
            import pickle
            with open(metadata_file, 'rb') as f:
                metadata = pickle.load(f)
                documents.append({
                    "document_id": metadata['document_id'],
                    "filename": metadata['filename'],
                    "pages": metadata['pages'],
                    "upload_date": metadata['upload_date'].isoformat(),
                    "model_used": metadata['model_used']
                })
        
        return {"documents": documents}
        
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """Delete a specific document"""
    try:
        deleted_something = False
        
        # Delete vector store (it's a directory)
        vector_store_path = config.VECTOR_STORE_DIR / f"{document_id}.faiss"
        if vector_store_path.exists() and vector_store_path.is_dir():
            shutil.rmtree(vector_store_path)
            deleted_something = True
            logger.info(f"Deleted vector store for document: {document_id}")
        
        # Delete metadata
        metadata_path = config.VECTOR_STORE_DIR / f"{document_id}.metadata"
        if metadata_path.exists():
            os.remove(metadata_path)
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
        raise HTTPException(status_code=500, detail=str(e))

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
        raise HTTPException(status_code=500, detail=str(e))

def start_server():
    """Start the FastAPI server"""
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,  # Changed to 8080 to avoid conflicts
        log_level="info"
    )

if __name__ == "__main__":
    start_server()